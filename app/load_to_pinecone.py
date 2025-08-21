import os
import sys
from dotenv import load_dotenv
load_dotenv()

from app.menu_loader import load_menu_docs
from app.drupal_loader import load_all_links
from app.embeddings import embed_text
from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")

# Reset index if needed
if "--reset" in sys.argv:
    if index_name in pc.list_indexes().names():
        print(f"🧹 Deleting existing index '{index_name}'...")
        pc.delete_index(index_name)
    else:
        print(f"⚠️ Index '{index_name}' not found, nothing to reset.")

# Create index if it doesn't exist
if index_name not in pc.list_indexes().names():
    print(f"📦 Creating index '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=384,  # Adjust if your embed_text uses different embedding size
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=os.getenv("PINECONE_ENV"))
    )

index = pc.Index(index_name)

# Load documents from Drupal API and menu JSON
print("🔍 Loading documents from Drupal API and menu JSON...")
drupal_docs = load_all_links()
menu_docs = load_menu_docs()
docs = drupal_docs + menu_docs
print(f"📄 Loaded {len(docs)} total documents.")

# Count total related links extracted in metadata (optional check)
total_related_links = sum(len(doc["metadata"].get("related_links", [])) for doc in drupal_docs)
print(f"🔗 Found {total_related_links} related links across Drupal docs.")

print("🧠 Embedding and upserting documents...")

upsert_payload = []
fail_count = 0

for doc in docs:
    try:
        embedding = embed_text(doc["text"])
        # Add the text content to metadata so it can be retrieved during RAG
        metadata_with_text = doc["metadata"].copy()
        metadata_with_text["text"] = doc["text"]
        upsert_payload.append((doc["id"], embedding, metadata_with_text))
    except Exception as e:
        print(f"⚠️ Failed to embed {doc['id']}: {e}")
        fail_count += 1

if upsert_payload:
    try:
        index.upsert(vectors=upsert_payload)
        print(f"✅ Successfully upserted {len(upsert_payload)} / {len(docs)} documents.")
        if fail_count > 0:
            print(f"⚠️ Skipped {fail_count} documents due to embedding failures.")
    except Exception as e:
        print(f"❌ Failed to upsert to Pinecone index: {e}")
else:
    print("❌ No documents were upserted.")

print("🛠️ To reset the index, run: python load_to_pinecone.py --reset")
