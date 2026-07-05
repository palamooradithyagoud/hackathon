import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pypdf
import chromadb

# Load environment variables
load_dotenv()


def get_chroma_client():
    """
    Initializes and returns a Chroma client using credentials from .env.
    """
    mode = os.getenv("CHROMA_MODE", "remote").strip().lower()
    if mode == "remote":
        api_key = os.getenv("CHROMA_API_KEY", "").strip()
        tenant = os.getenv("CHROMA_TENANT", "").strip()
        database = os.getenv("CHROMA_DATABASE", "").strip()

        if not api_key or not tenant or not database:
            print("ERROR: Missing CHROMA_API_KEY, CHROMA_TENANT, or CHROMA_DATABASE in .env")
            sys.exit(1)

        print(f"Connecting to Chroma Cloud (tenant: {tenant}, database: {database})...")
        client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database,
        )
    else:
        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chromadb_data").strip()
        print(f"Connecting to local Chroma DB (persist: {persist_dir})...")
        client = chromadb.PersistentClient(path=persist_dir)

    # Verify connection
    try:
        heartbeat = client.heartbeat()
        print(f"Connection successful! Heartbeat: {heartbeat}")
    except Exception as e:
        print(f"Error connecting to Chroma DB: {e}")
        sys.exit(1)

    return client


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text into chunks of roughly chunk_size characters with chunk_overlap overlap,
    attempting to respect word boundaries.
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Try to break at a space or newline
            last_space = text.rfind(' ', end - 50, end)
            last_newline = text.rfind('\n', end - 50, end)
            best_break = max(last_space, last_newline)
            if best_break != -1:
                end = best_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        # Move start forward
        start = end - chunk_overlap
        if start >= end:
            start = end

    return chunks


def extract_pdf_chunks(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    Reads a PDF file and extracts text chunks page-by-page.
    Returns lists of: documents, metadatas, and ids.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    print(f"Reading PDF: {path.name}...")
    reader = pypdf.PdfReader(path)

    documents = []
    metadatas = []
    ids = []

    pdf_name = path.name

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        text = page.extract_text()
        if not text or not text.strip():
            continue

        page_chunks = split_text(text, chunk_size, chunk_overlap)
        print(f"  Page {page_num}: {len(page_chunks)} chunks")

        for chunk_idx, chunk in enumerate(page_chunks):
            chunk_id = f"{pdf_name}_p{page_num}_c{chunk_idx}"
            documents.append(chunk)
            metadatas.append({
                "source": pdf_name,
                "page": page_num,
                "chunk": chunk_idx
            })
            ids.append(chunk_id)

    return documents, metadatas, ids


def main():
    print("=" * 50)
    print("  Chroma DB - PDF Uploader")
    print("=" * 50)

    # Ask user to paste the PDF file path
    pdf_path = input("\nPaste the full path to your PDF file: ").strip()

    # Remove surrounding quotes if the user pasted a quoted path
    if (pdf_path.startswith('"') and pdf_path.endswith('"')) or \
       (pdf_path.startswith("'") and pdf_path.endswith("'")):
        pdf_path = pdf_path[1:-1]

    if not pdf_path:
        print("ERROR: No path provided.")
        sys.exit(1)

    # Extract content from PDF
    try:
        documents, metadatas, ids = extract_pdf_chunks(pdf_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)

    if not documents:
        print("No text content found/extracted from the PDF.")
        sys.exit(1)

    print(f"\nTotal chunks extracted: {len(documents)}")

    # Connect to Chroma DB
    client = get_chroma_client()

    # Get or create collection
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "pdf_documents").strip()
    print(f"Getting or creating collection '{collection_name}'...")
    collection = client.get_or_create_collection(name=collection_name)

    # Add documents to Chroma DB in batches
    print(f"Ingesting {len(documents)} chunks into Chroma DB...")

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]

        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
        print(f"  Batch {i // batch_size + 1}: chunks {i + 1}-{min(i + batch_size, len(documents))} uploaded")

    print("\n" + "=" * 50)
    print("  Upload complete!")
    print(f"  Collection: {collection_name}")
    print(f"  Total chunks: {len(documents)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
