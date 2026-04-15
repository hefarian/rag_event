# Puls-Events — RAG POC

[![Tests CI](https://github.com/USERNAME/PROJET09/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/PROJET09/actions/workflows/ci.yml)

RAG (Retrieval-Augmented Generation) system using OpenAgenda events, FAISS vector search, LangChain orchestration, and Mistral LLM.

> **FastAPI + Swagger + Streamlit Interface + Docker** 🚀

## 🏗️ Architecture

- **Backend API**: FastAPI with Swagger UI (`/docs`)
- **Frontend UI**: Streamlit interactive dashboard
- **Vector Store**: FAISS for similarity search
- **LLM**: Mistral for embeddings and text generation
- **Deployment**: Docker Compose

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Setup environment
cp .env.example .env
# Edit .env with MISTRAL_API_KEY and OPENAGENDA_API_KEY

# Start services
docker-compose up -d

# Access
# - API Swagger: http://localhost:8000/docs
# - Streamlit UI: http://localhost:8501
```

### Local Development

```powershell
# Setup Python environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Build index
python scripts/build_index.py

# Terminal 1: Start API
uvicorn api.app:app --reload --port 8000

# Terminal 2: Start UI
streamlit run streamlit_app.py --server.port 8501
```

## 📚 Core Commands

### Building & Indexing

```bash
# Build FAISS index from OpenAgenda data
python scripts/build_index.py

# Clean old events (remove past dates, faster than full rebuild)
.\clean_old_events.ps1              # PowerShell
clean_old_events.bat                # Batch
python scripts/clean_old_events.py  # Python direct
```

### Verification

```bash
# API health
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Quels concerts cette semaine?"}'
```

## 🧹 Index Maintenance

### Clean Old Events

Remove outdated events **without** full index rebuild (~3 seconds vs ~30 minutes):

```powershell
# Simulate (see what would be removed)
.\clean_old_events.ps1 -DryRun

# Execute (creates automatic backups)
.\clean_old_events.ps1

# Without backup
.\clean_old_events.ps1 -NoBackup
```

### Diagnostic & Troubleshooting

Check index consistency and past events:

```bash
# Diagnose index state
python scripts/diagnostic_index.py

# Outputs: vector count, metadata sync, past events found, recommendations
```

**For issues**: See [doc/TROUBLESHOOTING.md](doc/TROUBLESHOOTING.md)

**Full details**: See [doc/CLEAN_OLD_EVENTS_GUIDE.md](doc/CLEAN_OLD_EVENTS_GUIDE.md)

## 📋 API Reference

All endpoints documented in **Swagger UI** at `/docs`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Status |
| `/health` | GET | Health check |
| `/ask` | POST | RAG query with generation |
| `/search` | POST | Similarity search only |
| `/rebuild` | POST | Rebuild index from source |

### Example Request

```json
POST /ask
{
  "question": "Quels événements à Paris cette weekend?",
  "top_k": 3
}
```

## 🎨 UI Features

**Streamlit** at `http://localhost:8501`:
- 💬 **RAG Chat**: Ask questions, get answers with sources
- 🔍 **Search**: Find similar documents
- ⚙️ **Admin**: Manage index and settings
- 📚 **Docs**: API reference

## 🐳 Docker Commands

```bash
# View logs
docker-compose logs -f api
docker-compose logs -f streamlit

# Rebuild images
docker-compose up -d --build

# Stop/cleanup
docker-compose down
docker-compose down -v  # Remove volumes
```

## 📁 Project Structure

```
PROJET09/
├── api/
│   └── app.py                    FastAPI application
├── scripts/
│   ├── build_index.py           Full index build
│   └── clean_old_events.py      Incremental cleanup
├── tests/
│   └── test_clean_old_events.py Test suite
├── streamlit_app.py              UI/Dashboard
├── docker-compose.yml            Container orchestration
├── requirements.txt              Python dependencies
└── README.md                     This file
```

## 🔧 Configuration

### Environment (.env)

```env
MISTRAL_API_KEY=your_key
LOG_LEVEL=INFO
DEBUG=false
```

### API Settings (api/app.py)

- **Port**: 8000 (configurable in docker-compose.yml)
- **Host**: 0.0.0.0 (accessible from outside)
- **CORS**: Enabled for all origins

## ✅ Testing

```bash
# Unit tests
pytest tests/

# Test specific module
pytest tests/test_clean_old_events.py -v

# In Docker
docker-compose exec api pytest tests/

# With coverage report
pytest tests/ --cov=scripts --cov-report=html
```

## 🔄 CI/CD Pipeline

### GitHub Actions

Automated tests run on every push and pull request:

```yaml
# Triggers on: push to main/develop, PR to main/develop
# Runs:
#   - Tests on Python 3.8, 3.9, 3.10, 3.11
#   - Linting with flake8
#   - Coverage report to Codecov
```

**Workflow file**: [.github/workflows/ci.yml](.github/workflows/ci.yml)

View build status: [![Tests CI Badge](https://github.com/USERNAME/PROJET09/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/PROJET09/actions)

## 📈 Workflow

1. **Ingest**: OpenAgenda events → JSON
2. **Index**: Chunk text → Mistral embeddings → FAISS
3. **Search**: Query in FAISS → retrieve top-k
4. **Generate**: Pass to Mistral LLM → answer with sources
5. **Serve**: FastAPI + Streamlit + Docker

## 🚀 Deployment

### Production Checklist

- [ ] Use `faiss-gpu` instead of `faiss-cpu` (if hardware available)
- [ ] Enable authentication on API endpoints
- [ ] Add rate limiting
- [ ] Configure persistent volume for vectors/
- [ ] Setup logging aggregation
- [ ] Use secrets manager for API keys

## 📚 Purge des évènements passé

Quick reference and detailed guides available in `doc/`:

docker exec -it puls-events-api python scripts/clean_index_robust.py

## 📝 Notes

- FAISS-CPU is used for portability (use GPU version for production)
- Streamlit requires API to be healthy at startup
- Volumes are mounted for persistent storage
- Both services auto-restart on failure (docker-compose)
- Data from DATAIN/ is processed into vectors/ directory

## 🎯 Next Steps

1. Build your first index: `python scripts/build_index.py`
2. Start services: `docker-compose up -d`
3. Try the API: `curl http://localhost:8000/docs`
4. Use the UI: Open `http://localhost:8501`
5. Clean old events: `.\clean_old_events.ps1 -DryRun`

