# eugene-ade — agentic document extraction with evidence provenance

Fetches research PDFs, stores them in S3, extracts Markdown + grounded JSON chunks,
and renders the exact page region an answer came from. A local reimplementation of
LandingAI's ADE architecture — no vendor API key.

**Runs on `http://localhost:18100`** · Swagger at `/docs`

## Pipeline

```
fetch → store → parse → layout → artifacts → index
```

1. **fetch** — resolve PMID/PMCID/DOI via Europe PMC, download the PDF.
   Europe PMC rather than PubMed on purpose: PubMed indexes abstracts and most
   records have no free PDF. Measured on a real query: 8/8 Europe PMC results
   carried PDF links, 6/8 open access.
2. **store** — original bytes to `s3://$ADE_S3_BUCKET/documents/{doc_id}/source.pdf`,
   unmodified. This is the evidence of record.
3. **parse** — PyMuPDF reads the PDF's own content stream: exact text, exact
   geometry, tables via `find_tables()`, reading order, marginalia detection.
4. **layout** — DocLayout-YOLO labels each region (title / text / table / figure /
   caption / footnote / formula). Merged onto the parsed chunks by IoU.
5. **artifacts** — `parse.md`, `chunks.json`, `grounding.json`, `document.json`.
6. **index** — write the paper and its passages into Neo4j so fused retrieval can
   surface them. Without this the extraction is a dead end: the agent could cite a
   paper but not retrieve what it says.

### Graph shape

```
(:paper {doc_id, title, doi, pmid, pmcid, year, journal, url})
  -[:has_chunk]-> (:paper_chunk {chunk_id, doc_id, page, bbox_*, text, chunk_type})
(:paper) -[:mentions]-> (:drug | :disease)
```

Each `paper_chunk` carries `doc_id` + `chunk_id` — exactly the pair the evidence
renderer needs, so a retrieved passage knows how to prove itself. Milvus embedding
happens separately in `eugene_ws` (`corpus_ingest_service --labels paper_chunk`),
because milvus-lite is single-process and only that service may open it.

### Why both PyMuPDF and a DL model

Neither is sufficient alone. PyMuPDF gives exact text and coordinates but cannot
tell an *abstract* from a *paragraph*. DocLayout-YOLO gives semantic labels but no
text. Merging them yields exact text + exact coordinates + a real type.

Measured on a 13-page paper:

| | chunk types |
|---|---|
| PyMuPDF only | `text: 190, marginalia: 28` |
| + DocLayout-YOLO | `text: 167, title: 5, table: 8, caption: 7, footnote: 3, marginalia: 28` |

If the model or its weights can't load, the service logs a warning and returns
structural labels only. A missing optional model never takes extraction offline.

## S3 layout

```
documents/{doc_id}/source.pdf                    original PDF
documents/{doc_id}/document.json                 manifest: metadata, counts, timings
documents/{doc_id}/parse.md                      full Markdown
documents/{doc_id}/chunks.json                   chunks w/ bbox, type, ids, source
documents/{doc_id}/grounding.json                chunk_id → {page, box, type}
documents/{doc_id}/renders/{chunk_id}@{dpi}.png  cached evidence renders
```

`doc_id` is a deterministic slug, so re-ingesting is idempotent and evidence links
stay stable.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/ade/ingest` | run pipeline for one document (idempotent) |
| POST | `/ade/ingest/batch` | queue many for background extraction |
| POST | `/ade/reindex` | re-run graph indexing from S3 artifacts (no re-extraction); `?doc_id=` for one |
| GET | `/ade/documents/{doc_id}` | manifest |
| GET | `/ade/documents/{doc_id}/chunks` | chunks (filter by `chunk_type`, `page`) |
| GET | `/ade/documents/{doc_id}/markdown` | Markdown |
| GET | `/ade/documents/{doc_id}/pdf` | original PDF |
| GET | `/ade/evidence/{doc_id}/{chunk_id}.png` | **highlighted page render** |
| GET | `/ade/page/{doc_id}/{page_no}.png` | plain page render |
| GET | `/health` | liveness + S3 + model status |

```bash
curl -X POST localhost:18100/ade/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source":"europepmc","id":"PMC13202553"}'

curl "localhost:18100/ade/evidence/pmc13202553/<chunk_id>.png?dpi=150" -o evidence.png
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ADE_S3_BUCKET` | — | **required**; artifact bucket |
| `AWS_REGION` | `us-east-1` | |
| `ADE_LAYOUT_ENABLED` | `true` | `false` skips the DL model entirely |
| `ADE_LAYOUT_CONF` | `0.25` | YOLO confidence threshold |
| `ADE_LAYOUT_MIN_IOU` | `0.15` | below this, a detected region doesn't relabel a chunk |

## Performance

Cold ingest of a 13-page paper: **~70s** — fetch 18s, parse 11s, **YOLO 39s** (CPU),
artifacts 0.4s. A 10-page paper ran in 36s. YOLO dominates, which is why batch
ingestion is backgrounded and the pipeline is idempotent.

Evidence renders are cached in S3, so the second view of a chunk is one object GET.

## Known limits

- **Paywalled papers** return `status: "unavailable"` with the publisher link. This
  is a normal outcome, not an error.
- **Scanned PDFs** have no text layer; they are flagged `text_layer: false`. OCR is
  not implemented.
- **Cold start** downloads 40.7 MB of YOLO weights. Cached on the
  `eugene_ade_models` volume; the model is warmed at boot.
- **The same paper ingested under two identifiers becomes two documents.** A PMID
  and its PMCID slug to different `doc_id`s, so both extract and both index —
  observed with `42206210` / `pmc13202553`. Deduplicating on DOI at ingest time is
  the fix; not implemented.
- **Entity linking is name-match only** (~4.5 mentions/paper), scoped to title and
  opening passages so a long review can't emit hundreds of weak edges. It will miss
  entities named only by synonym.
