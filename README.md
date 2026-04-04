Puls-Events — RAG POC

This repository contains a small proof-of-concept for a Retrieval-Augmented Generation system
that uses OpenAgenda event data, FAISS for vector search, LangChain orchestration and Mistral for
embeddings/generation.

> **Now with FastAPI + Swagger + Streamlit Interface + Docker!** 🚀

---

## 📁 Project Structure

### Root Level (Clean, Only Essentials)
```
init_index.py          ← Initialiser l'index FAISS 2026+ (utilité)
streamlit_app.py       ← Interface utilisateur  (utilité)
README.md              ← Ce fichier
docker-compose.yml     ← Docker orchestration
requirements.txt       ← Dependencies
.gitignore             ← Git rules (archive/ ignoré)
```

---

## 📋 Architecture

- **Backend API**: FastAPI with Swagger documentation (`/docs`)
- **Frontend UI**: Streamlit interactive interface for users
- **Vector Store**: FAISS for efficient similarity search
- **Containerization**: Docker + Docker Compose for easy deployment

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

**Prerequisites**: Docker and Docker Compose installed

```bash
# Clone the repository
git clone <repo-url>
cd PROJET09

# Copy environment variables template
cp .env.example .env
# Edit .env with your API keys
# MISTRAL_API_KEY=your_key_here
# OPENAGENDA_API_KEY=your_key_here

# Start the services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Access the application
# - Streamlit UI: http://localhost:8501
# - FastAPI Swagger: http://localhost:8000/docs
# - API Health: http://localhost:8000/health
```

### Option 2: Local Development

**Prerequisites**: Python 3.8+, pip

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Build FAISS index (optional, if you have data)
python scripts/build_index.py

# Start API in one terminal
uvicorn api.app:app --reload --port 8000

# Start Streamlit in another terminal
streamlit run streamlit_app.py --server.port 8501
```

## 📚 API Endpoints

All endpoints are documented in **Swagger UI**: `http://localhost:8000/docs`

### Health & Status
- `GET /` - API status
- `GET /health` - Health check (for Docker)

### RAG Operations
- `POST /ask` - Ask a question to the RAG system
  ```json
  {
    "question": "Quels concerts jazz à Paris cette semaine ?",
    "top_k": 3
  }
  ```
- `POST /search` - Similarity search without generation
  ```json
  {
    "question": "Jazz concerts",
    "top_k": 5
  }
  ```

### Administration
- `POST /rebuild` - Rebuild FAISS index from source data

## 🎨 Streamlit Interface

Access at `http://localhost:8501`

Features:
- **💬 Chat RAG**: Ask questions and get answers with sources
- **🔍 Search**: Find similar documents
- **⚙️ Administration**: Manage index and configuration
- **📚 Documentation**: API reference and links

## 🐳 Docker Deployment

### Build Images Individually (if needed)

```bash
# Build API image
docker build -f Dockerfile.api -t puls-events-api:latest .

# Build Streamlit image
docker build -f Dockerfile.streamlit -t puls-events-ui:latest .

# Run API container
docker run -p 8000:8000 \
  -e MISTRAL_API_KEY=your_key \
  -v ./vectors:/app/vectors \
  puls-events-api:latest

# Run Streamlit container
docker run -p 8501:8501 \
  --network host \
  puls-events-ui:latest
```

### Docker Compose Useful Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f streamlit

# Stop services
docker-compose down

# Rebuild images
docker-compose up -d --build

# Remove volumes (clean everything)
docker-compose down -v
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
MISTRAL_API_KEY=your_api_key
OPENAGENDA_API_KEY=your_api_key
LOG_LEVEL=INFO
DEBUG=false
```

### API Configuration

API settings in `api/app.py`:
- Port: `8000` (configurable in docker-compose.yml)
- Host: `0.0.0.0` (accessible from outside container)
- CORS: Enabled for all origins

### Streamlit Configuration

Streamlit settings in `Dockerfile.streamlit`:
- Port: `8501`
- Server mode: Headless (for Docker)

## ✅ Monitoring

### Health Checks

Both services include Docker health checks:

```bash
# Check API health
curl http://localhost:8000/health

# Check Streamlit (returns HTML if healthy)
curl http://localhost:8501/healthz
```

### Logs

```bash
# API logs
docker logs puls-events-api -f

# Streamlit logs
docker logs puls-events-ui -f
```

## 📦 Project Structure

```
PROJET09/
├── api/
│   └── app.py              # FastAPI application
├── scripts/
│   └── build_index.py      # Index building script
├── streamlit_app.py        # Streamlit interface
├── Dockerfile.api          # API container
├── Dockerfile.streamlit    # Streamlit container
├── docker-compose.yml      # Orchestration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🧪 Testing

```bash
# Run tests locally
pytest tests/

# Run tests in Docker
docker-compose exec api pytest tests/
```

## 🔄 Workflow

1. **Data Ingestion**: OpenAgenda events → JSON/Parquet
2. **Indexing**: Text chunking → Mistral embeddings → FAISS index
3. **API**: FastAPI with Swagger documentation
4. **UI**: Streamlit for user interaction
5. **Deployment**: Docker + Docker Compose

## 📝 Notes

- The system uses FAISS-CPU for portability (use `faiss-gpu` in production if needed)
- Streamlit depends on API being healthy before startup (configured in docker-compose)
- Volumes are mounted for persistent storage of vectors and data
- Both services have automatic restart policies

## 📞 Support

For issues or questions, check:
- `.github/copilot-instructions.md` for AI agent guidance
- `api/app.py` for endpoint documentation
- `streamlit_app.py` for UI logic
- Docker logs: `docker-compose logs`

## 🚀 Next Steps

1. **Implement RAG Logic**: Connect to actual Mistral API
2. **Add Real Data**: Ingest OpenAgenda events
3. **Scale**: Use faiss-gpu, add caching, optimize prompts
4. **Monitor**: Add Prometheus metrics, logging aggregation
