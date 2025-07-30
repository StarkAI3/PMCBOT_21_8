import os
from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=os.getenv("PINECONE_ENV"))
    )

index = pc.Index(index_name)

def upsert_embeddings(docs):
    to_upsert = [(doc["id"], doc["embedding"], doc["metadata"]) for doc in docs]
    index.upsert(vectors=to_upsert)

def query_embedding(embedding, top_k=5):
    result = index.query(vector=embedding, top_k=top_k, include_metadata=True)
    return result["matches"]
