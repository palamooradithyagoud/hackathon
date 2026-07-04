import os
import sys
from dotenv import load_dotenv
import chromadb
from groq import Groq

# Load environment variables
load_dotenv()


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


def query_documents(collection, question: str, n_results: int = 8):
    """Query Chroma DB for relevant document chunks."""
    results = collection.query(
        query_texts=[question],
        n_results=n_results,
    )
    return results


def ask_groq(question: str, context: str) -> str:
    """Send the question + retrieved context to Groq LLM and return the answer."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct").strip()

    if not groq_key:
        print("ERROR: Missing GROQ_API_KEY in .env")
        sys.exit(1)

    client = Groq(api_key=groq_key)

    system_prompt = (
        "You are a helpful research assistant. Answer the user's question based ONLY on the "
        "provided context from research papers.\n\n"
        "IMPORTANT RULES:\n"
        "- Distinguish between the ACTUAL AUTHORS of the paper (usually listed on Page 1 under "
        "the title) and authors mentioned in the REFERENCES/CITATIONS section.\n"
        "- When asked about authors, return ONLY the paper's own authors, NOT the cited/referenced authors.\n"
        "- The paper's authors are typically found on page 1, right below the title.\n"
        "- Referenced authors appear in numbered citations like [1], [2], etc.\n"
        "- If the context doesn't contain enough information to answer, say so clearly.\n"
        "- Cite the source page numbers when possible."
    )

    user_prompt = f"""Context from research papers:
---
{context}
---

Question: {question}

Answer:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as e:
        error_str = str(e).lower()
        if "rate_limit" in error_str or "429" in error_str or "rate limit" in error_str:
            fallback_model = "llama-3.1-8b-instant"
            print(f"\n[WARNING] Groq rate limit hit for {model}. Retrying with fallback: {fallback_model}...")
            response = client.chat.completions.create(
                model=fallback_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
        else:
            raise e

    return response.choices[0].message.content


def main():
    print("=" * 50)
    print("  Chroma DB - Research Paper Q&A")
    print("=" * 50)

    # Connect to Chroma DB
    print("\nConnecting to Chroma Cloud...")
    client = get_chroma_client()
    heartbeat = client.heartbeat()
    print(f"Connected! Heartbeat: {heartbeat}")

    # Get the collection
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "pdf_documents").strip()
    try:
        collection = client.get_collection(name=collection_name)
        doc_count = collection.count()
        print(f"Collection '{collection_name}' loaded ({doc_count} chunks)\n")
    except Exception as e:
        print(f"ERROR: Could not find collection '{collection_name}': {e}")
        print("Make sure you have uploaded a PDF first using ingest.py")
        sys.exit(1)

    # Interactive Q&A loop
    print("Ask questions about your uploaded documents.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Retrieve relevant chunks from Chroma DB
        results = query_documents(collection, question)

        if not results["documents"] or not results["documents"][0]:
            print("\nAssistant: No relevant documents found for your question.\n")
            continue

        # Build context from retrieved chunks
        context_parts = []
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            source = meta.get("source", "unknown")
            page = meta.get("page", "?")
            context_parts.append(f"[Source: {source}, Page {page}]\n{doc}")

        context = "\n\n".join(context_parts)

        # Get answer from Groq LLM
        try:
            answer = ask_groq(question, context)
            print(f"\nAssistant: {answer}\n")
        except Exception as e:
            print(f"\nERROR generating answer: {e}\n")


if __name__ == "__main__":
    main()
