"""
MedPak AI — RAG Vector Store
Builds and manages the ChromaDB collection of drug embeddings.
Run this file once to index the database:  python rag/vectorstore.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import Optional
from config import settings
from database.db import get_all_drugs


# ── Singleton handles ─────────────────────────────────────────────────────────

_client: Optional[chromadb.PersistentClient] = None
_collection = None
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[RAG] Loading embedding model: {settings.EMBED_MODEL}")
        _model = SentenceTransformer(settings.EMBED_MODEL)
    return _model


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(settings.CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    return _client


def get_collection():
    """Return the ChromaDB collection (creates if not exists)."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Indexing ──────────────────────────────────────────────────────────────────

def build_index(force: bool = False) -> int:
    """
    Embed all DRUG records and store in ChromaDB.
    Skips if already indexed (unless force=True).
    Returns number of documents indexed.
    """
    collection = get_collection()
    existing = collection.count()

    if existing > 0 and not force:
        print(f"[RAG] Index already built: {existing} documents. Use force=True to rebuild.")
        return existing

    print("[RAG] Fetching all drugs from database...")
    drugs = get_all_drugs()
    print(f"[RAG] Indexing {len(drugs)} drugs into ChromaDB...")

    model = _get_model()

    # Build text chunks for each drug
    documents, metadatas, ids = [], [], []
    for drug in drugs:
        # Combine the most semantically rich fields into one text chunk
        text_parts = [
            f"Drug: {drug['NAME']}",
            f"Indications: {drug['INDICATIONS'] or ''}",
            f"Overview: {drug['OVERVIEW'] or ''}",
            f"Side effects: {drug['EFFECTS'] or ''}",
            f"Contraindications: {drug['CONTRAINDICATIONS'] or ''}",
            f"Warnings: {drug['warnings'] or ''}",
        ]
        # Truncate to 2000 chars to keep embeddings manageable
        full_text = "\n".join(text_parts)[:2000]

        documents.append(full_text)
        metadatas.append({
            "drug_id":   drug["CODE"],
            "drug_name": drug["NAME"],
        })
        ids.append(str(drug["CODE"]))

    # Batch embed + upsert (ChromaDB handles batching internally)
    BATCH = 100
    for i in range(0, len(documents), BATCH):
        batch_docs  = documents[i:i+BATCH]
        batch_meta  = metadatas[i:i+BATCH]
        batch_ids   = ids[i:i+BATCH]
        embeddings  = model.encode(batch_docs, show_progress_bar=False).tolist()

        collection.upsert(
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        print(f"[RAG]  Indexed {min(i+BATCH, len(documents))}/{len(documents)}", end="\r")

    print(f"\n[RAG] [OK] Index built: {len(drugs)} drugs stored in ChromaDB.")
    return len(drugs)


# ── Query ─────────────────────────────────────────────────────────────────────

def query_index(query_text: str, n_results: int = 3) -> list[dict]:
    """
    Semantic search: embed query → find top-N most similar drug documents.
    Returns list of {drug_id, drug_name, document, score}.
    """
    collection = get_collection()
    if collection.count() == 0:
        print("[RAG] Warning: index is empty. Run build_index() first.")
        return []

    model = _get_model()
    query_embedding = model.encode([query_text])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "drug_id":   results["metadatas"][0][i]["drug_id"],
            "drug_name": results["metadatas"][0][i]["drug_name"],
            "document":  results["documents"][0][i],
            "score":     1 - results["distances"][0][i],  # cosine similarity
        })
    return output


# ── Self-test / build trigger ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Building ChromaDB Index ===")
    n = build_index(force=False)
    print(f"Total indexed: {n}")

    print("\n=== Test Query: 'fever and headache' ===")
    results = query_index("fever and headache medicine", n_results=3)
    for r in results:
        print(f"  [{r['score']:.3f}]  {r['drug_name']} (id={r['drug_id']})")

    print("\n=== Test Query: 'bukhaar aur sir dard' (Roman Urdu) ===")
    results = query_index("bukhaar aur sir dard ki dawa", n_results=3)
    for r in results:
        print(f"  [{r['score']:.3f}]  {r['drug_name']} (id={r['drug_id']})")

    print("\n=== Index built and tested successfully! ===")
