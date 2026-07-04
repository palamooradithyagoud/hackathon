"""
Download all PDFs from a Google Drive folder and ingest them into Chroma DB.
Usage: python ingest_drive.py
"""

import os
import sys
import glob
import time
from pathlib import Path
from dotenv import load_dotenv
import gdown
import pypdf
import chromadb

# Load environment variables
load_dotenv()

# Google Drive folder ID — all files are sourced from here
GDRIVE_FOLDER_ID = "1IjFWghs6FKGPhVTCHksc_pk_8nrmWjHm"

# Google Drive file IDs and names (full folder listing, updated 2026-07-05)
GDRIVE_FILES = [
    # --- Original 5 ---
    ("1Oq7kFuaCq3fA4RLgAz8QU7YKFHYBBgJA", "Agri-Ai-Intelligent-Plant-Disease-Surveillance-and-Predictive-Forecasting_PADMAJA.pdf"),
    ("1CktTi4qJb42k1dUOqrzvkaGwGZpjhP_b", "Comprehensive Models Towards for Feature_venkateshwara.pdf"),
    ("15etGUU4Zu2WX15r8jWrwRJbf2aV18K9h", "Integrating Named Data Networking with IoT-Based Internet _MADHURYA.pdf"),
    ("1_k4HgIK9iK10_CZlEhrlWZo0H5ggxRwm", "IOT based health monitoring_gagandeep.pdf"),
    ("1nWR7O3aq1iOeu4Zo4IdBAR7TLNuH0VSs", "Measuring Internet Energy Consumption at The Edge and Core_vasantha.pdf"),
    # --- New 8 (added 2026-07-05) ---
    ("1Uc-dlzXX416zXELIsykXlkbJEpQAQs4H", "Accident Detection and Alert System Using Big Data Analytics_SRININVAS_GONGULA.pdf"),
    ("1v7uAFa0kFtaOW8Sxhw7ha8tHgDYEZYfa", "Characterizing Ipv6 Adoption Trends Through Longitudinal _RAVIKUMAR.pdf"),
    ("13jUTybvLdBTZzRL9yHulOfzfjDFIX0Ke", "economics.pdf"),
    ("1AvYpc8Eiqzga8ejCqR99Bihy6SNgJ1ZA", "From CNNs to diffusion models_MANZOOR.pdf"),
    ("1ZM0Usj9a6kGbew13obOIPu4dJTPRRiyn", "frontiers.pdf"),
    ("1XYMi8YueZ6WjXjgglqjmS63wA_fZu0X-", "heart_disease.pdf"),
    ("1mK-gNIeLcgJP1ngfTYQ0VFua8DSgt-LX", "procedia.pdf"),
    ("1npz0m0gHZwCkUlo2A59HUOyOMH6WqtLB", "science_direct.pdf"),
]


def get_chroma_client():
    """Connect to Chroma Cloud using credentials from .env."""
    api_key = os.getenv("CHROMA_API_KEY", "").strip()
    tenant = os.getenv("CHROMA_TENANT", "").strip()
    database = os.getenv("CHROMA_DATABASE", "").strip()

    if not api_key or not tenant or not database:
        print("ERROR: Missing CHROMA_API_KEY, CHROMA_TENANT, or CHROMA_DATABASE in .env")
        sys.exit(1)

    client = chromadb.CloudClient(
        api_key=api_key,
        tenant=tenant,
        database=database,
    )
    return client


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks respecting word boundaries."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
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

        start = end - chunk_overlap
        if start >= end:
            start = end

    return chunks


def extract_pdf_chunks(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Read a PDF file and extract text chunks page-by-page."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

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


def download_file(file_id: str, output_path: str, retries: int = 3):
    """Download a single file from Google Drive by its file ID."""
    url = f"https://drive.google.com/uc?id={file_id}"
    for attempt in range(retries):
        try:
            gdown.download(url, output_path, quiet=False)
            if os.path.exists(output_path):
                return True
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    return False


def main():
    print("=" * 55)
    print("  Google Drive -> Chroma DB Bulk PDF Uploader")
    print("=" * 55)

    # 1. Download PDFs from Google Drive
    download_dir = os.path.join(os.getcwd(), "downloaded_pdfs")
    os.makedirs(download_dir, exist_ok=True)

    print(f"\nDownloading {len(GDRIVE_FILES)} PDFs from Google Drive...")
    downloaded_files = []

    for file_id, file_name in GDRIVE_FILES:
        output_path = os.path.join(download_dir, file_name)

        if os.path.exists(output_path):
            print(f"  Already exists: {file_name}")
            downloaded_files.append(output_path)
            continue

        print(f"\n  Downloading: {file_name}")
        if download_file(file_id, output_path):
            downloaded_files.append(output_path)
            print(f"  Done: {file_name}")
        else:
            print(f"  FAILED: {file_name}")

    if not downloaded_files:
        print("\nERROR: No PDF files downloaded.")
        sys.exit(1)

    print(f"\n{len(downloaded_files)} PDF(s) ready for ingestion.")

    # 2. Connect to Chroma DB
    print("\nConnecting to Chroma Cloud...")
    client = get_chroma_client()
    heartbeat = client.heartbeat()
    print(f"Connected! Heartbeat: {heartbeat}")

    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "pdf_documents").strip()
    collection = client.get_or_create_collection(name=collection_name)
    print(f"Collection '{collection_name}' ready.\n")

    # 3. Process and ingest each PDF
    total_chunks = 0
    for pdf_path in downloaded_files:
        pdf_name = Path(pdf_path).name
        print(f"Processing: {pdf_name}")

        try:
            documents, metadatas, ids = extract_pdf_chunks(pdf_path)
        except Exception as e:
            print(f"  ERROR reading {pdf_name}: {e}")
            continue

        if not documents:
            print(f"  No text extracted from {pdf_name}, skipping.")
            continue

        print(f"  Extracted {len(documents)} chunks")

        # Upload in batches using upsert to avoid duplicate errors
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            collection.upsert(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )

        print(f"  Uploaded {len(documents)} chunks")
        total_chunks += len(documents)

    # 4. Summary
    print("\n" + "=" * 55)
    print(f"  Upload complete!")
    print(f"  PDFs processed: {len(downloaded_files)}")
    print(f"  Total chunks uploaded: {total_chunks}")
    print(f"  Collection: {collection_name}")
    print(f"  Total in collection: {collection.count()}")
    print("=" * 55)


if __name__ == "__main__":
    main()
