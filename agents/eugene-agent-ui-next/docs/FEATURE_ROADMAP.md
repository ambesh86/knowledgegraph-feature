# CSL Atlas — Feature Roadmap (funding build)

Research-backed plan for turning Atlas from a graph-grounded chat into a full
**research workspace**: upload → parse → analyze → generate → publish, with
durable memory. Written 2026-07. Each feature includes a build spec ("prompt")
so it can be implemented independently.

## Hard constraint that shapes everything
The production EC2 sits in a **VPC with no internet egress** (verified: PubMed,
Google, OpenAI all unreachable from the box). Therefore:
- **No runtime calls to cloud APIs** (LandingAI cloud parse, hosted LLMs) unless
  a NAT gateway / VPC endpoint is added. Track that as an infra dependency.
- Features are architected **offline-first**: local libraries for
  generation/parsing; the **Eugene backend agent** supplies intelligence.
- Where a feature is dramatically better with cloud (agentic PDF extraction),
  we ship the offline path now and gate the cloud path behind
  `EUGENE_INTERNET_EGRESS=1`.

## Competitive framing (why this wins funding)
- **LandingAI ADE** (Agentic Document Extraction) — treats a document as a
  visual object, agentic parse/extract/section/split, hierarchical JSON +
  markdown, 99.16% DocVQA, 1000+ page PDFs. This is the bar for "PDF parsing."
  Sources: https://landing.ai/ , https://github.com/landing-ai/ade-python
- **Claude Artifacts / Publish** — significant self-contained output rendered in
  a side panel; downloadable `.docx/.pptx/.xlsx/.pdf`, HTML, Markdown, Mermaid,
  React; **Publish** = public link, **Share** = org-only, recipients need no
  account, others can remix. Source:
  https://support.claude.com/en/articles/9547008-publish-and-share-artifacts
- **Agent memory (2026)** — move off flat RAG to a **three-layer** design:
  in-context (short-term) + vector store (semantic long-term) + structured store
  (exact long-term); Graph-RAG and Agentic-RAG are the trend. Sources:
  https://mem0.ai/blog/state-of-ai-agent-memory-2026 ,
  https://sparkco.ai/blog/ai-agent-memory-in-2026-comparing-rag-vector-stores-and-graph-based-approaches

Atlas already owns a **biomedical knowledge graph** (Neo4j/PrimeKG, 484k nodes /
21.4m rels) — the differentiator is **Graph-grounded** document intelligence:
uploads and memory resolved against the graph, not a generic vector blob.

---

## Feature 1 — Export & Publish (SHIPPING FIRST)
"Generate PDF / Word / HTML on demand + publish like Claude."

**Spec**
- Any assistant answer gets a toolbar: **Copy · Export ▾ · Publish**.
- Export formats (all offline): **Markdown** (trivial), **HTML** (styled,
  self-contained), **Word `.docx`** (pure-JS `docx` lib — no binary), **PDF**
  (via the published artifact page's browser-native Print / Save-as-PDF, so no
  Puppeteer/Chromium on the t3.medium).
- **Publish** persists the answer as an `artifacts` row and returns a shareable
  URL `/nextgen/a/<id>` (viewable by anyone who can reach the app — VPN scope
  today; public when a public ALB is added). Publisher-owned; revocable.
- DB: `artifacts(id, user_id, conversation_id, title, body_md, source, format,
  created_at, revoked)`. Access page is read-only and unauthenticated-within-app.

**Files**: `lib/atlas/artifacts.ts`, `app/api/atlas/artifacts/route.ts`,
`app/api/atlas/artifacts/[id]/route.ts`,
`app/api/atlas/artifacts/[id]/export/route.ts`, `app/a/[id]/page.tsx`,
toolbar in `components/atlas/views/AskView.tsx`. Dependency: `docx`.

---

## Feature 2 — Document & Image Upload (attach to chat)
**Spec**
- Drag-drop / paste / file-picker in the composer. Accept PDF, DOCX, TXT, MD,
  PNG/JPG. Cap ~25 MB.
- Store bytes in Postgres `uploads(id, user_id, conversation_id, filename, mime,
  bytes BYTEA, extracted_text, page_count, created_at)` (or on-disk volume +
  path if we outgrow BYTEA).
- Show an attachment chip in the message; images render inline.
- Extracted text (Feature 3) is prepended to the agent prompt as context so the
  answer is grounded in the uploaded doc.
- Route: `POST /api/atlas/uploads` (multipart), `GET /api/atlas/uploads/[id]`
  (download / inline), size + mime allowlist, per-user ownership.

---

## Feature 3 — PDF / Document Parsing (LandingAI-style)
**Spec — two tiers**
- **Offline tier (ships now-ish):** `pdfjs-dist` / `unpdf` for text + layout;
  `mammoth` for `.docx`→html/text. Produces markdown + page map. Good for
  born-digital PDFs. No OCR for scanned pages without a model.
- **Agentic tier (behind `EUGENE_INTERNET_EGRESS=1` or a Eugene backend
  endpoint):** call LandingAI ADE `parse`/`extract` (hierarchical JSON + grounded
  boxes) OR route the extracted text through the Eugene agent to pull structured
  fields (drugs, targets, trials) and **resolve them against the knowledge
  graph** — this is the graph-grounded differentiator LandingAI can't do.
- Output stored on the `uploads` row (`extracted_text`, `structured JSONB`).
- Route: `POST /api/atlas/uploads/[id]/parse`.

---

## Feature 4 — Concrete Memory (three-layer)
**Spec** (mirrors the working `~/.claude` memory model, graph-aware)
- **Exact/structured layer:** `memories(id, user_id, kind, title, body,
  entities JSONB, source_conversation, created_at, updated_at)` — kinds:
  `preference | fact | project | entity`. Editable in a **Memory** panel
  (view/add/delete), like the file-based memory that already serves this repo.
- **Semantic layer (when embeddings are reachable):** embed each memory via the
  Eugene backend embeddings endpoint; store vectors in `pgvector`; retrieve
  top-k per new question and inject into the agent prompt.
- **Graph layer:** memories reference graph node ids; recall pulls the node's
  current facts so memory stays live, not stale.
- Auto-capture: after a turn, a lightweight extractor proposes memories
  (confirm-before-save) so it grows without manual work.
- Routes: `GET/POST/DELETE /api/atlas/memory`, injection hook in the send path.

---

## Sequencing
1. **Export & Publish** (this PR) — visible, self-contained, offline. ✅
2. **Upload + offline parse** — the "LandingAI" demo moment (drag a paper in).
3. **Concrete memory** (structured first, semantic when embeddings wired).
4. **Agentic parse + graph resolution** — needs egress or a backend endpoint.

## Infra dependencies to raise with the funding/infra ask
- **NAT gateway or VPC endpoints** to unlock cloud parse + hosted models.
- **pgvector** extension on the Atlas Postgres for the semantic memory layer.
- **Public ALB + TLS** to make Publish truly public (today it's VPN-scoped).
- Object storage (S3) if uploads outgrow Postgres BYTEA.
