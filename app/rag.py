from app.embeddings import embed_text
from app.vector_store import query_embedding
from app.session_memory import add_to_history, get_history
from app.url_mapper import url_mapper
from openai import OpenAI
import re
import os
from typing import List
from datetime import datetime


def _ensure_logs_dir_exists() -> None:
    logs_dir = os.path.join("logs")
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        # Best-effort logging directory creation; ignore failures
        pass


def _append_log_entry(text: str) -> None:
    try:
        _ensure_logs_dir_exists()
        log_path = os.path.join("logs", "logs.txt")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(text)
            if not text.endswith("\n"):
                log_file.write("\n")
            log_file.write("\n")
    except Exception:
        # Avoid breaking the request on logging errors
        pass

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_language(query: str) -> str:
    """
    Detect if the query is in English or Marathi using LLM for better accuracy.
    Returns 'english' or 'marathi'
    """
    # Simple heuristic-based language detection for Devanagari
    # Count Devanagari characters vs Latin characters
    
    # Devanagari Unicode range: 0x0900-0x097F
    devanagari_chars = sum(1 for char in query if '\u0900' <= char <= '\u097F')
    
    # Latin characters (basic English)
    latin_chars = sum(1 for char in query if char.isalpha() and ord(char) < 128)
    
    # If more Devanagari characters, it's definitely Marathi
    if devanagari_chars > latin_chars:
        return 'marathi'
    
    # For Latin script text, run lightweight rule checks before any LLM call
    query_lower = query.lower()

    marathi_indicators = {
        'kasa', 'kase', 'kay', 'kaay', 'kuthe', 'kadhi', 'kiti', 'konala', 'kona',
        'milwaycha', 'milwayche', 'milwaychi', 'karaycha', 'karayche', 'karaychi',
        'ghaycha', 'ghayche', 'ghaychi', 'deyacha', 'deyache', 'deyachi',
        'bharaycha', 'bharayche', 'bharaychi', 'mahnaycha', 'mahnayche', 'mahnaychi',
        'sangaycha', 'sangayche', 'sangaychi', 'hotay', 'hoti', 'hota', 'hotat',
        'aadhaar', 'mahapalika', 'nagar', 'palika',
    }

    words_in_query = query_lower.split()
    marathi_indicator_count = 0
    for word in words_in_query:
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word in marathi_indicators:
            marathi_indicator_count += 1

    marathi_patterns = [
        r'\b(kasa|kase|kay|kaay|kuthe|kadhi|kiti|konala|kona)\s+\w+',
        r'\w+\s+(cha|che|chi|ne|la|na|ta|te|ti|sa|se|si)\b',
        r'\b(milwaycha|milwayche|milwaychi|karaycha|karayche|karaychi)\b',
        r'\b(ghaycha|ghayche|ghaychi|deyacha|deyache|deyachi)\b',
        r'\b(bharaycha|bharayche|bharaychi|mahnaycha|mahnayche|mahnaychi)\b',
        r'\w+\s+(kasa|kase|kay|kaay|kuthe|kadhi|kiti|konala|kona)\s+\w+',
    ]
    pattern_matches = 0
    for pattern in marathi_patterns:
        if re.search(pattern, query_lower):
            pattern_matches += 1

    # If there are no Marathi indicators or patterns at all, treat as English
    if marathi_indicator_count == 0 and pattern_matches == 0:
        return 'english'

    # Strong Marathi signals: classify as Marathi without LLM
    if marathi_indicator_count >= 2 or pattern_matches > 0:
        return 'marathi'

    # Ambiguous case (e.g., exactly one indicator): use LLM as a tie-breaker
    try:
        language_detection_prompt = f"""
You are a language detection expert. Analyze the following text and determine if it's written in English or Romanized Marathi (Marathi words written using English/Latin script).

Text to analyze: "{query}"

Respond with only one word: "english" or "marathi"
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": language_detection_prompt}],
            temperature=0.1,
            max_tokens=10,
        )

        detected_lang = response.choices[0].message.content.strip().lower()

        # Strict normalization of response
        if detected_lang in {"marathi", "romanized marathi"}:
            return 'marathi'
        if detected_lang == 'english':
            return 'english'
        # Default to English if unclear in ambiguous scenarios
        return 'english'

    except Exception as e:
        # If LLM fails, use fallback
        print(f"LLM language detection failed: {e}")
        return fallback_language_detection(query)

def fallback_language_detection(query: str) -> str:
    """
    Fallback rule-based language detection when LLM is unavailable.
    """
    query_lower = query.lower()
    
    # Marathi-specific words that are strong indicators
    marathi_indicators = {
        'kasa', 'kase', 'kay', 'kaay', 'kuthe', 'kadhi', 'kiti', 'konala', 'kona',
        'milwaycha', 'milwayche', 'milwaychi', 'karaycha', 'karayche', 'karaychi',
        'ghaycha', 'ghayche', 'ghaychi', 'deyacha', 'deyache', 'deyachi',
        'bharaycha', 'bharayche', 'bharaychi', 'mahnaycha', 'mahnayche', 'mahnaychi',
        'sangaycha', 'sangayche', 'sangaychi', 'hotay', 'hoti', 'hota', 'hotat',
        'aadhaar', 'mahapalika', 'nagar', 'palika',
    }
    
    # Count strong Marathi indicators in the query
    marathi_indicator_count = 0
    words_in_query = query_lower.split()
    
    for word in words_in_query:
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word in marathi_indicators:
            marathi_indicator_count += 1
    
    # If we find strong Marathi indicators, treat as Marathi
    if marathi_indicator_count > 0:
        return 'marathi'
    
    # Check for common Marathi sentence patterns
    marathi_patterns = [
        r'\b(kasa|kase|kay|kaay|kuthe|kadhi|kiti|konala|kona)\s+\w+',
        r'\w+\s+(cha|che|chi|ne|la|na|ta|te|ti|sa|se|si)\b',
        r'\b(milwaycha|milwayche|milwaychi|karaycha|karayche|karaychi)\b',
        r'\b(ghaycha|ghayche|ghaychi|deyacha|deyache|deyachi)\b',
        r'\b(bharaycha|bharayche|bharaychi|mahnaycha|mahnayche|mahnaychi)\b',
        r'\w+\s+(kasa|kase|kay|kaay|kuthe|kadhi|kiti|konala|kona)\s+\w+',
    ]
    
    import re
    pattern_matches = 0
    for pattern in marathi_patterns:
        if re.search(pattern, query_lower):
            pattern_matches += 1
    
    # If we find Marathi patterns, treat as Marathi
    if pattern_matches > 0:
        return 'marathi'
    
    # Default to English if no clear Marathi indicators
    return 'english'

def generate_answer(query: str, session_id: str):
    # Detect language of the query
    detected_language = detect_language(query)
    
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
        if detected_language == 'marathi':
            links_md = "\n\nउपयुक्त लिंक्स:\n" + "\n".join(f"- [{link}]({link})" for link in top_links)
        else:
            links_md = "\n\nUseful Links:\n" + "\n".join(f"- [{link}]({link})" for link in top_links)

    # Get recent chat history
    chat_history = get_history(session_id)
    history_context = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:])

    # Language-specific prompts
    if detected_language == 'marathi':
        prompt = f"""
तुम्ही पुणे महानगरपालिकेच्या वापरकर्त्यांसाठी एक सहाय्यक आहात.
दिलेल्या दस्तऐवजांवर आणि वर्तमान संवादावर आधारित संक्षिप्त उत्तर द्या.
योग्य ठिकाणी स्रोत मेटाडेटामधून क्लिक करण्यायोग्य लिंक्स समाविष्ट करा.
वापरकर्त्यांना लिंक्स देताना नेहमी बॅकएंड API URL ऐवजी फ्रंटएंड URL प्राधान्य द्या.

संवाद इतिहास:
{history_context}

संदर्भ:
{docs_context}

वापरकर्ता: {query}
उत्तर:
{links_md}
"""
    else:
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

    # Build detailed log before calling the LLM
    try:
        matches_log_lines = []
        for idx, m in enumerate(matches, start=1):
            meta = m.get("metadata", {}) or {}
            source = meta.get("source", "")
            text_snippet = (meta.get("text", "") or "")[:500]
            score = m.get("score", None)
            matches_log_lines.append(
                f"  {idx}. score={score} source={source}\n     snippet={text_snippet}"
            )

        matches_section = "\n".join(matches_log_lines) if matches_log_lines else "  (none)"

        detailed_log = (
            f"==== Chat Request Log ====\n"
            f"Time: {datetime.utcnow().isoformat()}Z\n"
            f"Session ID: {session_id}\n"
            f"Detected Language: {detected_language}\n"
            f"User Query: {query}\n"
            f"\nRecent History Used (last 5):\n{history_context}\n"
            f"\nRetrieved Matches ({len(matches)}):\n{matches_section}\n"
            f"\nRelated Links ({len(related_links)}): {related_links}\n"
            f"Additional Links from Keywords ({len(additional_links)}): {additional_links}\n"
            f"All Links Used in Prompt ({len(all_links)}): {all_links}\n"
            f"\nPrompt sent to OpenAI (model=gpt-4o-mini):\n{prompt}"
        )
    except Exception:
        detailed_log = None

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

    # Append answer to the detailed log and write to file
    try:
        if detailed_log is not None:
            full_log = detailed_log + f"\n\nLLM Answer:\n{answer}\n============================="
            _append_log_entry(full_log)
    except Exception:
        pass

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
