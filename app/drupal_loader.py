import requests
import hashlib

from bs4 import BeautifulSoup

def get_public_url(api_url: str) -> str:
    """
    Convert a PMC Drupal API URL to the corresponding public-facing URL.
    E.g., https://webadmin.pmc.gov.in/api/basic-page/fire-brigade?lang=en
       → https://www.pmc.gov.in/en/fire-brigade
    """
    if "api/basic-page/" in api_url:
        slug = api_url.split("api/basic-page/")[-1].split("?")[0]
        return f"https://www.pmc.gov.in/en/{slug}"
    return api_url  # fallback: if it's not an API page, return as-is


def extract_text_and_links(data):
    texts = []
    links = set()

    def clean_html(html_content):
        return BeautifulSoup(html_content, "html.parser").get_text(separator=" ", strip=True)

    def recurse(obj):
        if isinstance(obj, dict):
            for key in ['title', 'detail_summary', 'sub_summary']:
                if key in obj and obj[key]:
                    texts.append(str(obj[key]))

            if 'summary' in obj and isinstance(obj['summary'], list):
                for html_block in obj['summary']:
                    texts.append(clean_html(html_block))

            if 'descriptions' in obj and obj['descriptions']:
                for desc in obj['descriptions']:
                    texts.append(str(desc))

            # extract links
            for link_key in ['internal_link', 'external_link', 'file_url', 'paragraph_file_url', 'node_file_url']:
                url = obj.get(link_key)
                if url:
                    links.add(url)

            if 'pdf_files' in obj:
                for pdf in obj['pdf_files']:
                    if 'file_url' in pdf:
                        links.add(pdf['file_url'])
                    if 'pdf_title' in pdf:
                        texts.append(pdf['pdf_title'])

            for v in obj.values():
                recurse(v)

        elif isinstance(obj, list):
            for item in obj:
                recurse(item)

    recurse(data)
    return " ".join(texts), list(links)


def fetch_json_and_extract_text(url):
    try:
        res = requests.get(url, timeout=10, verify=False)
        res.raise_for_status()
        data = res.json()
        text, found_links = extract_text_and_links(data)
        return text[:2000], url, found_links
    except Exception as e:
        print(f"❌ Failed to fetch or parse JSON from {url}: {e}")
        return None, None, []

def load_all_links():
    with open("data/urls.txt") as f:
        urls = [line.strip() for line in f.readlines()]

    docs = []
    total_links_found = 0

    for url in urls:
        content, link, found_links = fetch_json_and_extract_text(url)
        if content:
            uid = hashlib.md5(link.encode()).hexdigest()
            total_links_found += len(found_links)
            docs.append({
                "id": uid,
                "text": content,
                "metadata": {
                    "source": get_public_url(link),
                    "related_links": found_links
                }
            })

    print(f"✅ Loaded {len(docs)} JSON documents from {len(urls)} URLs.")
    print(f"🔗 Extracted a total of {total_links_found} related links from all docs.")
    return docs
