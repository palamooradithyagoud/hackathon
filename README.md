# 🎓 Faculty Research Assistant RAG + Collaboration Platform

This is a production-grade academic search, collaboration matchmaking, and trend gap identification system powered by a **FastAPI backend** (Vercel serverless compatible) and an **interactive CLI client**.

## ⚙️ Core Architecture

- **Vector Database**: `ChromaDB` storing faculty biographies and research summaries.
- **Relational Storage & Memory**: `SQLite` (default) or `PostgreSQL` for transactional logging, decisions, and user feedback.
- **RAG & Reasoning Engine**: `Groq LLM` with intent classifier routing.
- **External Intelligence**: `arXiv API` + `Tavily Search API` to compare global trends against local competencies when vector matches are weak.

---

## 🚀 Setup & Execution

### 1. Configure Settings

Create a `.env` file in the root directory (based on `.env.example`):
```ini
CHROMA_MODE=remote
CHROMA_HOST=api.trychroma.com
CHROMA_PORT=443
CHROMA_SSL=true
CHROMA_API_KEY=your_chromadb_cloud_key
CHROMA_TENANT=your_tenant_id
CHROMA_DATABASE=your_database_id
CHROMA_COLLECTION_NAME=Researchpapers

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Optional: Add Tavily API Key for web searches
TAVILY_API_KEY=your_tavily_key
```

### 2. Install Dependencies

Install the requirements inside your virtual environment:
```bash
pip install -r requirements.txt
```

### 3. Ingest Data (Optional)

If you need to re-ingest PDFs from Google Drive:
```bash
python ingest_drive.py
```

---

## 💻 CLI Mode (Primary Demo)

To run the terminal-based conversation assistant directly:
```bash
python main.py
```

### Example Usage:
```
You: Who works on Federated Learning?

Assistant:
Dr. Padmaja and Dr. Venkateshwara are the closest matches...
[Detailed reasoning, citing documents and page numbers]

Shall I proceed and log this recommendation? (yes/no): yes
Recommendation successfully logged.
Would you like to rate this response? (1-5, or press Enter to skip): 5
Any comments? (Optional): Very relevant matches!
Thank you for your feedback!
```

---

## 🌐 Server Mode (APIs)

To run the FastAPI server locally:
```bash
python server.py
```
Or:
```bash
uvicorn server:app --port 8000 --reload
```

### Main Endpoints:

1. **`POST /api/chat`** — Routes queries dynamically using intent classifier.
   - Body: `{"query": "Who works on IoT?"}`
2. **`POST /api/upload_pdf`** — Ingest and clean custom faculty profile PDFs.
3. **`POST /api/recommend`** — General RAG search for faculty profiles.
4. **`POST /api/collaborate`** — Propose collaborations and joint projects between professors.
   - Body: `{"faculty_a": "Padmaja", "faculty_b": "Madhurya"}`
5. **`POST /api/professor-mode`** — Gap analysis comparing local expertise against arXiv/web trends.
   - Body: `{"topic": "quantum computing"}`
6. **`GET /api/logs`** — Retrieve database audit logs.
7. **`POST /api/feedback`** — Submit ratings and comments.

---

## ⚡ Deployment

Deploy to Vercel instantly using the preconfigured [vercel.json](vercel.json):
```bash
vercel deploy
```
Ensure environment variables match those in `.env`.
