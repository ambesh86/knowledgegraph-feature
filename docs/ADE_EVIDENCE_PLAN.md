# Agentic Document Extraction + 100% evidence provenance

**Goal:** a user clicks a literature result in Ask → the paper's PDF is fetched, stored in S3,
parsed by a deep-learning document-extraction pipeline into Markdown + JSON (chunks with
bounding boxes, type, ids, source) → the user is shown the *exact* page region the answer
came from, rendered on the fly with PyMuPDF.

Modelled on LandingAI's ADE architecture, but with **no API key** — the extraction is ours.

---

## 1. Feasibility — verified before any code was written

| Question | Finding |
|---|---|
| Can we get PDFs for literature results? | **Yes, via Europe PMC**, not raw PubMed. `europepmc.org/articles/{PMCID}?pdf=render` returned `application/pdf`, `%PDF-` magic, 3.2 MB. On a real query, **8/8 results carried PDF links, 6/8 open access**. Raw PubMed mostly has no free PDF — Europe PMC / PMC-OA is the correct fetch path. |
| Does the reference parser work on a real paper? | Yes — 13 pages → **218 chunks**, normalized 0–1 bboxes. |
| Does highlight rendering match the target UI? | Yes — rendered the abstract of a June 2026 *Kidney Medicine* paper with the same green highlight as the reference screenshot. |
| S3 writable? | Yes — created `s3://eugene-research-pdfs-087084717211` and confirmed put/list. |
| DocLayout-YOLO usable? | Yes — `doclayout-yolo==0.0.4` on PyPI, weights `juliozhao/DocLayout-YOLO-DocStructBench` are only **40.7 MB**. |

## 2. Architecture

```
 Ask (literature result)
        │  click / auto-ingest
        ▼
 ┌──────────────────────── eugene-ade  (NEW service, :18100) ────────────────────────┐
 │  1 FETCH     Europe PMC → resolve PMID/PMCID → download PDF                        │
 │  2 STORE     S3: documents/{doc_id}/source.pdf                                     │
 │  3 PARSE     PyMuPDF: text blocks, tables, figures, reading order  ── structure    │
 │  4 LAYOUT    DocLayout-YOLO: title/abstract/table/figure/caption   ── semantics    │
 │              → merged: DL region labels assigned to PyMuPDF text chunks            │
 │  5 ARTIFACTS S3: parse.md · chunks.json · grounding.json · document.json           │
 │  6 RENDER    on-the-fly PNG of page N with the chunk's bbox highlighted            │
 └───────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
 Evidence page — highlighted page image + chunk text + source link
```

**Why a separate service, not an addition to `eugene_ws`:** `eugene_ws` is already 2.04 GB and
owns the graph/vector API. Document extraction has a different dependency set (YOLO, OpenCV),
a different failure profile (long-running, network-bound), and should be able to fail or
restart without taking graph search down. Clean seam, own lifecycle.

### Why both PyMuPDF *and* DocLayout-YOLO

They solve different halves and neither is sufficient alone:

- **PyMuPDF** gives exact text and exact geometry, straight from the PDF's own content
  stream. It cannot tell you a block is an *abstract* rather than a *paragraph*.
- **DocLayout-YOLO** gives semantic region labels (title, plain text, abstract, table,
  figure, caption, formula) but returns pixel boxes with no text.

The pipeline runs both and does an **IoU-based merge**: each PyMuPDF text chunk is assigned
the DL label of the region it overlaps most. Result: exact text + exact coordinates + a real
semantic type. Falls back to PyMuPDF-only heuristics when the model is unavailable, so the
service degrades instead of failing.

### S3 layout

```
s3://eugene-research-pdfs-087084717211/
  documents/{doc_id}/source.pdf        original PDF, byte-identical
  documents/{doc_id}/document.json     manifest: source, title, pages, checksums, timings
  documents/{doc_id}/parse.md          full Markdown rendering
  documents/{doc_id}/chunks.json       [{chunk_id, chunk_type, page, bbox, text, source, order}]
  documents/{doc_id}/grounding.json    chunk_id → grounding (page, box, type)
```

`doc_id` is a deterministic slug (`pmc13202553`) so re-ingesting is idempotent and cheap.

### API (`:18100`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/ade/ingest` | `{source, id}` → run pipeline (idempotent; returns cached manifest) |
| POST | `/ade/ingest/batch` | auto-ingest all results of a search, in background |
| GET | `/ade/documents/{doc_id}` | manifest |
| GET | `/ade/documents/{doc_id}/chunks` | chunk list (filterable by type/page) |
| GET | `/ade/documents/{doc_id}/markdown` | Markdown |
| GET | `/ade/evidence/{doc_id}/{chunk_id}.png` | **on-the-fly highlighted page render** |
| GET | `/ade/documents/{doc_id}/pdf` | original PDF (presigned redirect) |
| GET | `/health` | liveness + S3 + model status |

## 3. The code-generation prompt

> Build a production FastAPI service called **eugene-ade** that reproduces LandingAI's
> Agentic Document Extraction locally, with no vendor API key.
>
> **Modules — one responsibility each, no cross-imports except through `pipeline.py`:**
>
> `storage.py` — S3 adapter. `put_bytes(key, data, content_type)`, `get_bytes(key)`,
> `exists(key)`, `put_json`, `get_json`, `presign(key, ttl)`. Bucket and region from env
> (`ADE_S3_BUCKET`, `AWS_REGION`). Every method raises a typed `StorageError`; never let a
> raw botocore exception escape.
>
> `fetch.py` — resolve a literature id to a downloadable PDF. Input `{source, id}` where
> source ∈ {pubmed, europepmc, pmc, url}. For pubmed/europepmc, query the Europe PMC REST
> search API with `resultType=core`, read `fullTextUrlList.fullTextUrl[]` and select entries
> with `documentStyle == "pdf"`, preferring open access. Download with a descriptive
> User-Agent, verify the first bytes are `%PDF-`, cap at 60 MB. Return
> `(pdf_bytes, metadata)` where metadata carries title, authors, year, doi, pmid, pmcid,
> is_open_access, pdf_url. Raise `PdfUnavailable` with a human-readable reason when there is
> no open PDF — this is common and must be a clean, explainable outcome, never a crash.
>
> `parser.py` — PyMuPDF structural parse. For each page emit chunks with: `chunk_id` (uuid),
> `chunk_type`, `page` (0-based), `bbox` normalized to 0..1 with (0,0) top-left, `text`,
> `order`. Tables first via `page.find_tables()` → Markdown, then text/image blocks in
> reading order, skipping blocks that overlap a table by >50%. Classify blocks in the top or
> bottom 8% of the page as `marginalia`. Return `(markdown, chunks, pages, grounding_index)`.
>
> `layout.py` — DocLayout-YOLO semantic labelling. Lazy-load the model
> (`juliozhao/DocLayout-YOLO-DocStructBench`, imgsz 1024, conf 0.25) on first use; cache the
> instance. `detect_page(page) -> [{label, bbox_norm, confidence}]`. `merge(chunks, regions)`
> assigns each chunk the label of the region with the highest IoU above 0.15, writing
> `chunk_type` and `layout_confidence`. **If the model or its weights are unavailable, log a
> warning and return the chunks unchanged** — the service must still work.
>
> `pipeline.py` — orchestration, the only module that composes the others.
> `ingest(source, id, force=False) -> Manifest`. Idempotent: if `document.json` exists in S3
> and `force` is false, return it. Otherwise fetch → store PDF → parse → layout-merge →
> write `parse.md`, `chunks.json`, `grounding.json`, `document.json` → return the manifest
> with per-stage timings.
>
> `render.py` — evidence rendering. `render_evidence(doc_id, chunk_id, dpi) -> png_bytes`.
> Load `grounding.json` and the PDF from S3, map the normalized bbox onto the page rect, add
> a rect annotation (stroke `(0.38,0.67,0.02)`, fill `(0.66,0.85,0.29)`, opacity 0.38),
> rasterize at a clamped 96–300 dpi. Cache rendered PNGs in S3 under
> `documents/{doc_id}/renders/{chunk_id}@{dpi}.png`.
>
> `api.py` — the routes in the table above. Background batch ingest via FastAPI
> `BackgroundTasks`. Return typed Pydantic models. Long PDF work must never block the event
> loop — run blocking calls in a threadpool.
>
> **Non-negotiables:** every module has a docstring explaining *why* it exists, not just
> what it does. No bare `except:`. No secrets in code. Every network call has a timeout.
> Every S3 key is built by one function so the layout can never drift.

## 4. Risks / limits, stated up front

- **Not every paper has an open PDF.** Paywalled records are a normal outcome, surfaced as
  "no open-access PDF available" with the publisher link — not an error.
- **DocLayout-YOLO adds cold-start latency** (first request loads 40.7 MB of weights). Model
  is warmed at startup and cached on a volume.
- **Scanned PDFs have no text layer.** PyMuPDF returns nothing; DL gives regions but no text.
  OCR is out of scope for this iteration and such documents are flagged `text_layer: false`.
