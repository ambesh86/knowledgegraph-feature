# Eugene — Presentation Talking Points

### Agentic Biomedical Competitive-Intelligence Platform

---

**1. Agentic intelligence, not just search**
Eugene is a conversational AI agent that *reasons* over a biomedical knowledge graph. It plans multi-step tool calls (ReAct: Reason → Act → Observe) instead of returning flat search results.

**2. Curated knowledge graph at its core**
A Neo4j graph with **44 node types and 31 relationship types** — drugs, diseases, genes/proteins, pathways, clinical trials, patents, and organizations — capturing how biomedical entities connect.

**3. Live reasoning-graph visualization**
Every answer materializes the agent's reasoning path as an interactive graph in real time. Users *see* which nodes and relationships the agent traversed — not just the text answer.

**4. Real-time data, not a stale snapshot**  *(headline new capability)*
Beyond the static graph, Eugene pulls **live data** from ClinicalTrials.gov (recruiting trials, sponsors, phases), Europe PMC (latest literature + patents), and PubMed — fetched at query time.

**5. Static + live data fusion**
A single question blends curated graph facts with real-time web sources in one answer — e.g. *"What does Eugene know about Hemophilia A, and what are the most recent trials?"* — with citations distinguishing the two.

**6. Full explainability & provenance**
Every asserted fact carries a citation `[node_id, tool]`, and the UI traces evidence and lineage — critical for regulated pharma / competitive-intelligence contexts where answers must be auditable.

**7. Multi-step relationship reasoning**
Eugene chains tools intelligently — resolving an organization name → its ID → its assets, or walking gene-protein neighbors → their clinical trials — answering multi-hop questions a keyword search cannot.

**8. Enterprise-grade, model-agnostic architecture**
Pluggable LLM backends (OpenAI / Anthropic / AWS Bedrock), JWT auth with user allowlisting, and a clean separation: UI ↔ Agent ↔ MCP tool server ↔ Neo4j — each independently scalable.

**9. Extensible via MCP (Model Context Protocol)**
New capabilities are added as tools, not rewrites. Drop in a new graph tool or live-data tool and the agent discovers it automatically — future-proof for new data sources and skills.

**10. Deployed and demo-ready, anywhere**
Runs as a containerized stack — locally via Docker or on AWS (EC2 / Terraform) — with streaming responses, multi-turn conversations, and a polished Next.js UI featuring a live context graph.

---

### 30-second pitch

> **Eugene is an agentic biomedical competitive-intelligence platform.** It combines a curated 44-type knowledge graph with real-time clinical-trial, patent, and literature search — and shows its reasoning as a live, explainable graph with full source citations. Ask it a question in plain English, and watch it plan, query, and connect the evidence in front of you.

---

### Demo questions (in order)

| # | Question | Capability shown |
|---|---|---|
| 1 | "What assets does CSL Behring have?" | Graph traversal + reasoning-graph viz |
| 2 | "Find the gene-protein neighbors of Factor VIII and which clinical trials reference them." | Multi-hop relationship reasoning |
| 3 | "Find the latest recruiting clinical trials for emicizumab." | Real-time clinical trials *(enable Web chip)* |
| 4 | "Search the latest literature and patents on emicizumab." | Real-time literature + patents *(enable Web + PubMed)* |
| 5 | "What does Eugene know about Hemophilia A, and what are the most recent trials for its treatments?" | Static graph + live data fusion *(enable all chips)* |

---

### Tech stack at a glance

**Knowledge Graph** Neo4j 5.26 · **Agent** Strands + FastAPI · **LLM** OpenAI GPT-4.1 (also Anthropic / Bedrock) · **Tools** MCP (Model Context Protocol) · **UI** Next.js 14 + Cytoscape · **Live sources** ClinicalTrials.gov · Europe PMC · PubMed · **Deploy** Docker / AWS EC2 / Terraform
