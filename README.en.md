# PaperMind — Scientific Intelligence Platform

> **Ask in your language, find research in English.**

Multilingual semantic search and source-grounded answers over four academic sources — **arXiv, Crossref, DOAJ and OpenAlex**. A Russian query finds English papers, and the answer comes back in the language you asked in.

Self-hosted, open source, one `docker compose up`. Retrieval quality is **measured and reproducible**, not asserted.

*(Full documentation in Azerbaijani: [README.md](README.md) · Deployment guide: [DEPLOY.md](DEPLOY.md))*

---

## Why this exists

Most research is published in English. Most students outside the English-speaking world do not think in English. That gap is not a translation problem — it is a **retrieval** problem: if you cannot pick the right English keywords, keyword search returns nothing, and you never learn that the paper you needed was three results away.

PaperMind removes the keyword step. You ask in Azerbaijani or Russian; a multilingual embedding model maps your question into the same vector space as the English abstracts; the answer is written back in your language with citations.

## What it does

- **Semantic search** over 19 scientific fields — meaning, not keywords
- **Source-grounded Q&A (RAG)** — every claim carries a citation; when the context has no answer, the model says so
- **Genuinely multilingual retrieval** — measured RU↔EN similarity of 0.79, not a translation shim
- **Cross-source deduplication** — the same work indexed by arXiv, Crossref and DOAJ appears once, with all three recorded as provenance
- **Trend analytics** across five discipline groups, cached in Redis
- **Trilingual UI** (AZ / RU / EN), 128 keys each
- **Automated ingestion** — three daily n8n workflows with retries and a dedicated error-handler workflow
- **Paper intelligence** — problem, methodology, dataset, findings and limitations extracted per paper, each tagged with its *evidence type*: stated in the paper / synthesized / AI inference. Only abstracts are indexed, so that distinction is never hidden
- **Comparison and conflicting evidence** — 2–5 papers compared across seven axes; conflicts classified from *conditions*, not from opposite wording (a different population or metric means conditional, not direct, conflict). The system never declares which paper is right
- **Research landscape, trends and gaps** — clusters, active authors and cross-field links counted from the indexed corpus; trends classified as emerging/growing/stable/declining *with the reason*; gaps labelled explicitly as AI-generated opportunities, never as "no research exists"

## Architecture

```
Browser ──▶ FastAPI ──▶ PostgreSQL 16 + pgvector   (HNSW, cosine)
              │    └──▶ Redis 7                    (analytics, LLM answers, translations)
              └───────▶ Groq  llama-3.3-70b-versatile

n8n ──(3 daily crons)──▶ /api/ingest/pull ──▶ arXiv · Crossref · DOAJ · OpenAlex
                              ↓
                     dedup (DOI / arXiv ID / title)
                              ↓
                  chunking + multilingual embedding ──▶ DB
```

| Layer | Choice |
|---|---|
| API | FastAPI + Pydantic v2 |
| Storage | PostgreSQL 16 + pgvector, SQLAlchemy 2.0 |
| Cache | Redis 7 |
| Embeddings | fastembed — `paraphrase-multilingual-MiniLM-L12-v2` (384d, local, free) |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Automation | n8n — 5 workflows |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |

## Four decisions worth explaining

### 1. Retrieval strategy was measured, not assumed

I assumed Russian search worked. A benchmark proved it did not: Russian queries were **not returning Russian papers at all**, because the translated query was being embedded instead of the original. The fix was dual-vector retrieval — `LEAST()` over the distance to both the original and the translated query.

Then the benchmark itself turned out to be irreproducible: without an `ORDER BY`, the same configuration scored 0.885 and 0.773 on consecutive runs. Both bugs were invisible to the eye.

The resulting policy lives in one function that both the API and the benchmark call, so the measured behaviour and the shipped behaviour cannot drift apart:

| Query language | Primary vector | Secondary | Measured reason |
|---|---|---|---|
| `en` | original | — | translation does not apply |
| `ru` | original | translation | original lifts field precision 63%→72%; translation lifts MRR 0.70→0.80 |
| `az` | translation | — | the Azerbaijani vector adds noise: 60% alone vs 52% when combined |

Current baseline (n=60, corpus 1,596):

| | English | Russian | Azerbaijani |
|---|---|---|---|
| known-item MRR@10 | 0.876 | 0.802 | — |
| NDCG@10 | 0.898 | 0.830 | — |
| Recall@10 | 97% | 92% | — |
| Field precision P@10 | 59% | 75% | 60% |

```bash
docker compose exec backend python scripts/benchmark.py --compare
```

### 2. Language is detected from the alphabet, not from metadata

Russian journals routinely publish English abstracts, and OpenAlex sometimes labels English work as `ru`. Trusting the source's language tag produced a "Russian corpus" that was mostly English. Detection now reads the Cyrillic-to-Latin character ratio of the text itself.

### 3. Deduplication runs on three keys, strongest first

DOI → arXiv ID (version stripped) → a diacritic- and punctuation-insensitive SHA-1 of the title. On a match no new row is created: the existing paper gains another provenance record and any missing fields (DOI, PDF link, field keys) are enriched from the other source. Dedup runs both **within** an incoming batch and **against** the database.

Verified against live data, not fixtures: of 15 DOAJ DOIs re-fetched directly from Crossref, the 7 that Crossref actually holds exist as a single row with two provenance records; the 8 it does not hold show DOAJ only. No duplicates were created.

### 4. Public exposure was secured before the port was opened

`PUBLIC_MODE=true` gates every write endpoint behind `X-API-Key` and enables rate limits (20 LLM questions/hour/IP, a 500/day global ceiling, 120 searches/hour/IP). A `preflight.sh` script runs 13 checks before deployment; n8n is reachable only over an SSH tunnel in production. A `429` surfaces in the UI as its own message in all three languages, not as a generic error.

## Quickstart

```bash
cp .env.example .env          # add your GROQ_API_KEY
docker compose up -d --build
docker compose exec backend python scripts/backfill_multi.py --days 14 --limit 80
```

Then open http://localhost:8000 — dashboard, search, Q&A, trends. API docs at `/docs`.

Low-RAM machine? The repo ships a [devcontainer](.devcontainer/devcontainer.json) — GitHub Codespaces runs the whole stack in the browser.

## Testing

```bash
docker compose exec backend python -m pytest tests/ -q
```

156 tests covering the functions that fail *silently* rather than loudly: dedup key normalisation and equivalence, alphabet-based language detection on mixed text, JATS abstract cleaning, chunk boundaries and overlap, plus an end-to-end check that one work arriving from three sources produces one row and three provenance records.

## Known limitations

Stated plainly, because they shape what this is useful for:

- **The corpus is small — roughly 1,600 papers.** This is a self-hosted index built from daily ingestion, not a mirror of the literature. Scale here is a hosting question, not an engineering one.
- **Hybrid search is built but off by default.** A lexical `tsvector` index and RRF fusion exist; `RETRIEVAL_MODE=vector` stays until benchmarking proves a gain (§5: complexity only when measured).
- **No reranking.** The top 10 is raw cosine ordering.
- **Abstracts only**, not full text.
- **Endpoint coverage is thin.** It now exists (validation, auth, response models) but retrieval quality itself is proven by benchmark, not tests.
- **Azerbaijani goes through translation**, since the model supports it less strongly than Russian or English.
- **Medicine and psychology** are not on arXiv and arrive only via Crossref/DOAJ text queries, so those fields are thin.

Planned next, in order: reranking (only if measured) → knowledge relationships between papers → provider abstraction for LLM/embedding backends.

## License

Not yet chosen — see the note at the top of [docs/POSITIONING.md](docs/POSITIONING.md). MIT is the intended default.
