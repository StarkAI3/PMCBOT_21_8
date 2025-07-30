import requests
from app.embeddings import embed_text

PMC_MENU_API = "https://webadmin.pmc.gov.in/api/menu-data/pmc-services-citizen?lang=en"

def flatten_menu(menu):
    flat_items = []

    for submenu in menu.get("field_sub_menu", []):
        for item in submenu.get("super_sub_menus", []):
            title = item.get("field_super_sub_menu_title", "").strip()
            link = item.get("field_super_sub_menu_link", "").strip()

            # Fix relative links
            if link and not link.startswith("http"):
                link = f"https://www.pmc.gov.in{link}"

            if title and link:
                flat_items.append({
                    "title": title,
                    "link": link
                })

    return flat_items

def load_menu_docs():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115.0.0.0 Safari/537.36"
        }

        res = requests.get(PMC_MENU_API, headers=headers, verify=False, timeout=10)
        res.raise_for_status()
        menu_json = res.json()

        items = flatten_menu(menu_json)
        docs = []

        for item in items:
            title = item["title"]
            url = item["link"]
            docs.append({
                "id": url,
                "text": f"{title}\n{url}",
                "metadata": {
                    "source": url
                }
            })

        print(f"✅ Extracted {len(docs)} menu items.")
        return docs
    except Exception as e:
        print(f"❌ Failed to load menu JSON: {e}")
        return []
