import sys, os
sys.path.insert(0, '.')
print('=' * 55)
print('  FACULTY RAG - HEALTH CHECK')
print('=' * 55)

# 1. Config
from core.config import settings
model_short = settings.GROQ_MODEL.split("/")[-1]
print(f'[1] Config       : OK  (model={model_short})')

# 2. ChromaDB
try:
    import chromadb
    mode = os.getenv("CHROMA_MODE", "remote").strip().lower()
    if mode == "remote":
        client = chromadb.CloudClient(
            api_key=settings.CHROMA_API_KEY,
            tenant=settings.CHROMA_TENANT,
            database=settings.CHROMA_DATABASE
        )
    else:
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
    col = client.get_or_create_collection(settings.CHROMA_COLLECTION_NAME)
    count = col.count()
    print(f'[2] ChromaDB     : OK  ({count} chunks in collection)')
except Exception as e:
    print(f'[2] ChromaDB     : FAIL ({e})')

# 3. Groq LLM
try:
    from services.groq_service import GroqService
    svc = GroqService()
    r = svc.generate('Say OK', max_tokens=5)
    print(f'[3] Groq LLM     : OK  (response={r.strip()})')
except Exception as e:
    print(f'[3] Groq LLM     : FAIL ({e})')

# 4. RAG pipeline
try:
    from rag.pipeline import RagPipeline
    pipe = RagPipeline()
    result = pipe.run('Who worked on plant disease detection?')
    preview = result.get('answer', '')[:80].replace('\n', ' ')
    print(f'[4] RAG Pipeline : OK  (answer preview: {preview}...)')
except Exception as e:
    print(f'[4] RAG Pipeline : FAIL ({e})')


# 5. Database
try:
    import sqlalchemy
    from db.database import get_db
    db = next(get_db())
    db.execute(sqlalchemy.text('SELECT 1'))
    print(f'[5] Database     : OK')
except Exception as e:
    print(f'[5] Database     : FAIL ({e})')

print('=' * 55)
print('  All checks done.')
print('=' * 55)
