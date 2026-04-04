# Instructions for AI agents (Puls-Events — RAG POC)

Goal: give AI agents the minimal, actionable knowledge to be productive on this RAG POC repository (OpenAgenda → FAISS → LangChain → Mistral).

1) Big picture
- Architecture: fetch OpenAgenda → clean & chunk (scripts/) → embed (Mistral embeddings) → index FAISS (vectors/) → retrieval via LangChain → generate with Mistral API (api/).
- Data flow: raw events → `data/events.json` or `data/events.parquet` → chunks + metadata → embeddings + `vectors/index.faiss` + `vectors/metadata.jsonl`.

2) Key paths and files (expect these)
- `README.md` : how to reproduce and run.
- `requirements.txt` : pinned deps to install.
- `scripts/fetch_openagenda.py` : pulls events (city, 1y window).
- `scripts/build_index.py` : creates FAISS index and metadata jsonl.
- `api/app.py` : FastAPI wrapper exposing `/ask` and `/rebuild`.
- `vectors/` : `index.faiss` and `metadata.jsonl` (not committed, produced by build script).
- `tests/` : unit tests for indexing and API.
- `Dockerfile` : build + run api image.

3) Environment checks
- Use Python >=3.8 and a venv. Prefer `faiss-cpu` for portability.
- Quick import test:
```
python -c "import faiss, langchain, pandas; print('imports ok')"
```

4) Secrets / env
- Use `MISTRAL_API_KEY` and `OPENAGENDA_API_KEY` environment variables. See `.env.example`.

5) Project-specific conventions
- Chunk size: aim for ~200–500 tokens per chunk and keep `event_id`, `date`, `location` in metadata.
- Metadata stored as JSONL in `vectors/metadata.jsonl` aligned by index id.
- LangChain usage pattern: use FAISS as VectorStore, call `similarity_search` top-k (3–5), build prompt by concatenating fragments, then call Mistral for generation.

6) Small prompt examples (copy-paste ready)
- Retrieval + prompt assembly (pseudo):
```
passages = vectorstore.similarity_search(q, k=4)
context = "\n\n".join([p.page_content for p in passages])
prompt = f"Using only the information below, answer the question concisely:\n\nCONTEXT:\n{context}\n\nQUESTION: {q}\n\nAnswer:"
```
- Mistral call (HTTP / client pseudocode):
```
response = MistralClient.generate(prompt=prompt, max_tokens=256, temperature=0.0)
```

7) Testing & evaluation
- Keep `tests/annotated_questions.jsonl` with {question, reference_answer} for automated eval.
- `evaluate_rag.py` should compute similarity/EM metrics (or call Ragas if present).

8) Docker & demo
- Docker image must mount or copy `vectors/index.faiss` at start.
- Local run example:
```
docker build -t puls-events-poc .
docker run -p 8000:8000 --env-file .env puls-events-poc
curl -X POST http://localhost:8000/ask -d '{"question":"Quels concerts jazz à Paris cette semaine ?"}'
```

9) What to avoid
- Don't rebuild FAISS index on every `/ask` call.
- Don't commit API keys or large vector files.

10) When in doubt
- Inspect `README.md`, `requirements.txt`, `scripts/`, `api/`, `tests/` first. If a file is missing, produce a minimal working stub and request review.

If you want, I can now generate small, runnable stubs: `scripts/build_index.py`, `api/app.py`, `tests/`, `requirements.txt` and a small `README.md` — say "yes" to proceed.
