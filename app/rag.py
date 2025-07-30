from app.embeddings import embed_text
from app.vector_store import query_embedding
from app.session_memory import add_to_history, get_history
from openai import OpenAI
import re
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(query: str, session_id: str):
    query_emb = embed_text(query)
    matches = query_embedding(query_emb, top_k=5)

    # Compose context text from matched docs
    docs_context = "\n\n".join(
        f"{m['metadata']['source']}:\n{m['metadata'].get('text', '')[:500]}" for m in matches
    )

    # Extract all related_links from matched docs metadata
    related_links = []
    for m in matches:
        links = m['metadata'].get("related_links", [])
        for link in links:
            if link not in related_links:
                related_links.append(link)

    # Prepare clickable links markdown block if any related_links exist
    links_md = ""
    if related_links:
        top_links = related_links[:5]
        links_md = "\n\nUseful Links:\n" + "\n".join(f"- [{link}]({link})" for link in top_links)

    # Get recent chat history
    chat_history = get_history(session_id)
    history_context = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:])

    prompt = f"""
You are a helpful assistant for Pune Municipal Corporation users.
Answer concisely based on the provided documents and the current conversation.
Include clickable links from source metadata wherever appropriate.

Chat History:
{history_context}

Context:
{docs_context}

User: {query}
Answer:
{links_md}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    answer = response.choices[0].message.content.strip()

    # Fix broken markdown links caused by punctuation right after the URL
    answer = re.sub(r'\]\((https?://[^\s)]+)([).,])\)', r'](\1)\2)', answer)

    add_to_history(session_id, "user", query)
    add_to_history(session_id, "assistant", answer)

    return answer, [m["metadata"]["source"] for m in matches]
