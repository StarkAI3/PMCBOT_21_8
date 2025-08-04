from app.embeddings import embed_text
from app.vector_store import query_embedding
from app.session_memory import add_to_history, get_history
from app.url_mapper import url_mapper
from openai import OpenAI
import re
import os
from typing import List

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(query: str, session_id: str):
    query_emb = embed_text(query)
    matches = query_embedding(query_emb, top_k=5)

    # Compose context text from matched docs
    docs_context = "\n\n".join(
        f"{m['metadata']['source']}:\n{m['metadata'].get('text', '')[:500]}" for m in matches
    )

    # Extract all related_links from matched docs metadata and convert to frontend URLs
    related_links = []
    for m in matches:
        links = m['metadata'].get("related_links", [])
        for link in links:
            # Convert backend URLs to frontend URLs
            frontend_url = url_mapper.get_frontend_url(link)
            if frontend_url:
                if frontend_url not in related_links:
                    related_links.append(frontend_url)
            else:
                # If no mapping found, keep the original URL if it's not a backend API URL
                if not link.startswith("https://webadmin.pmc.gov.in/api/"):
                    if link not in related_links:
                        related_links.append(link)

    # Search for additional relevant URLs based on query keywords
    query_keywords = extract_keywords(query)
    additional_links = []
    for keyword in query_keywords:
        keyword_mappings = url_mapper.search_mappings_by_keyword(keyword)
        for mapping in keyword_mappings[:2]:  # Limit to 2 results per keyword
            frontend_url = mapping['frontend_url']
            if frontend_url not in related_links and frontend_url not in additional_links:
                additional_links.append(frontend_url)
    
    # Combine all links, prioritizing related_links
    all_links = related_links + additional_links[:3]  # Limit additional links to 3

    # Prepare clickable links markdown block if any links exist
    links_md = ""
    if all_links:
        top_links = all_links[:5]
        links_md = "\n\nUseful Links:\n" + "\n".join(f"- [{link}]({link})" for link in top_links)

    # Get recent chat history
    chat_history = get_history(session_id)
    history_context = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:])

    prompt = f"""
You are a helpful assistant for Pune Municipal Corporation users.
Answer concisely based on the provided documents and the current conversation.
Include clickable links from source metadata wherever appropriate.
Always prefer frontend URLs over backend API URLs when providing links to users.

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

    # Convert any remaining backend URLs in the answer to frontend URLs
    answer = url_mapper.convert_urls_in_text(answer)

    # Fix broken markdown links caused by punctuation right after the URL
    answer = re.sub(r'\]\((https?://[^\s)]+)([).,])\)', r'](\1)\2)', answer)

    add_to_history(session_id, "user", query)
    add_to_history(session_id, "assistant", answer)

    return answer, [m["metadata"]["source"] for m in matches]

def extract_keywords(query: str) -> List[str]:
    """Extract relevant keywords from the query for URL matching."""
    # Remove common stop words and extract meaningful keywords
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'what', 'when', 'where', 'why', 'how', 'who', 'which', 'whose', 'whom'
    }
    
    # Simple keyword extraction - split by spaces and filter out stop words
    words = re.findall(r'\b\w+\b', query.lower())
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Add some domain-specific keywords that might be useful for PMC
    pmc_keywords = ['property', 'tax', 'tree', 'cutting', 'permission', 'circular', 'aadhaar', 'pan', 'card', 'linking']
    for keyword in pmc_keywords:
        if keyword in query.lower():
            keywords.append(keyword)
    
    return keywords[:5]  # Limit to 5 keywords
