#!/usr/bin/env python3
"""
Waża Kotlina — Auto SEO Blog Post Generator
- Catering i eventy na Ziemi Kłodzkiej
- Claude generuje artykuły pod usługi
- Unsplash zdjecia z atrybucją
- Rank Math SEO
"""

import os
import re
import json
import random
import base64
import requests
from datetime import datetime

WP_URL      = os.environ["WAZA_WP_URL"].rstrip("/")
WP_USER     = os.environ["WAZA_WP_USER"]
WP_PASSWORD = os.environ["WAZA_WP_PASSWORD"]
CLAUDE_KEY  = os.environ["CLAUDE_KEY"]
UNSPLASH_KEY = os.environ.get("UNSPLASH_KEY", "")
POST_STATUS = os.environ.get("POST_STATUS", "publish")
DW_TOKEN    = "directwebs2026"

SERVICES = [
    {"name": "catering firmowy", "url": "https://wazakotlina.pl/catering-firmowy/", "desc": "profesjonalny catering dla firm i konferencji"},
    {"name": "catering ślubny", "url": "https://wazakotlina.pl/catering-slubny/", "desc": "catering na wesela i uroczystości"},
    {"name": "eventy firmowe", "url": "https://wazakotlina.pl/eventy/", "desc": "organizacja eventów i imprez firmowych"},
    {"name": "grille plenerowe", "url": "https://wazakotlina.pl/grille/", "desc": "grille i pikniki plenerowe"},
    {"name": "warsztaty kulinarne", "url": "https://wazakotlina.pl/warsztaty/", "desc": "warsztaty kulinarne i atrakcje"},
    {"name": "wynajem sali", "url": "https://wazakotlina.pl/sala/", "desc": "wynajem sali konferencyjnej"},
]

KEYWORDS = [
    {"focus": "catering Kotlina Kłodzka", "related": ["catering Kłodzko", "catering na event Ziemia Kłodzka", "firma cateringowa Kłodzko"], "type": "lokalne", "length": 1600},
    {"focus": "catering firmowy Kłodzko", "related": ["lunch firmowy Kłodzko", "catering konferencyjny Ziemia Kłodzka", "bufet firmowy Kłodzko"], "type": "poradnik", "length": 1600},
    {"focus": "organizacja eventów Ziemia Kłodzka", "related": ["eventy firmowe Kłodzko", "imprezy firmowe Kotlina Kłodzka", "event Kłodzko"], "type": "poradnik", "length": 1800},
    {"focus": "catering ślubny Kotlina Kłodzka", "related": ["catering wesele Kłodzko", "catering na ślub Ziemia Kłodzka", "wesele catering Kłodzko"], "type": "poradnik", "length": 1800},
    {"focus": "grille plenerowe Kłodzko", "related": ["grill plenerowy catering", "piknik firmowy Kotlina Kłodzka", "catering grill Kłodzko"], "type": "lista", "length": 1500},
    {"focus": "warsztaty kulinarne Kotlina Kłodzka", "related": ["warsztaty gotowania Kłodzko", "atrakcje integracyjne Ziemia Kłodzka", "team building Kłodzko"], "type": "poradnik", "length": 1600},
    {"focus": "sala konferencyjna Kłodzko", "related": ["wynajem sali Kotlina Kłodzka", "sala na event Kłodzko", "konferencja Ziemia Kłodzka"], "type": "lokalne", "length": 1500},
    {"focus": "imprezy integracyjne Kotlina Kłodzka", "related": ["integracja firmowa Kłodzko", "team building Ziemia Kłodzka", "wyjazd integracyjny Kłodzko"], "type": "lista", "length": 1800},
]

EXTERNAL_LINKS = [
    {"url": "https://pl.wikipedia.org/wiki/Kotlina_K%C5%82odzka", "name": "Wikipedia — Kotlina Kłodzka"},
    {"url": "https://www.ziemiaklodzka.pl", "name": "Ziemia Kłodzka"},
    {"url": "https://pl.wikipedia.org/wiki/Catering", "name": "Wikipedia — Catering"},
]

def now():
    return datetime.now().strftime("%H:%M:%S")

def claude_request(prompt, max_tokens=1000):
    headers = {"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": "claude-sonnet-4-6", "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
    res.raise_for_status()
    return res.json()["content"][0]["text"].strip()

def get_unsplash_image(keyword):
    if not UNSPLASH_KEY:
        return None
    try:
        en_kw = keyword.replace("catering", "catering food").replace("Kłodzko", "").replace("Kotlina Kłodzka", "").replace("Ziemia Kłodzka", "").replace("event", "corporate event").replace("ślub", "wedding").strip()
        res = requests.get("https://api.unsplash.com/search/photos",
            params={"query": en_kw or "catering food elegant", "per_page": 5, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"})
        res.raise_for_status()
        results = res.json().get("results", [])
        if not results:
            return None
        photo = results[0]
        try:
            requests.get(photo["links"]["download_location"], headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=5)
        except:
            pass
        return {
            "url": photo["urls"]["regular"],
            "photographer": photo["user"]["name"],
            "photographer_url": photo["user"]["links"]["html"] + "?utm_source=wazakotlina&utm_medium=referral",
            "unsplash_url": photo["links"]["html"] + "?utm_source=wazakotlina&utm_medium=referral",
            "alt": photo.get("alt_description", keyword) or keyword
        }
    except Exception as e:
        print(f"[{now()}] Błąd Unsplash: {e}")
        return None

def upload_image(image, alt_text):
    try:
        img_res = requests.get(image["url"], timeout=30)
        img_res.raise_for_status()
        auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
        filename = re.sub(r'[^\w\s-]', '', alt_text.lower()).encode('ascii','ignore').decode('ascii')
        filename = re.sub(r'\s+', '-', filename)[:40].strip('-') + f"-{random.randint(100,999)}.jpg"
        res = requests.post(f"{WP_URL}/wp-json/wp/v2/media",
            headers={"Authorization": f"Basic {auth}", "Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": "image/jpeg"},
            data=img_res.content)
        res.raise_for_status()
        media = res.json()
        caption = f'Photo by <a href="{image["photographer_url"]}" target="_blank" rel="noopener">{image["photographer"]}</a> on <a href="{image["unsplash_url"]}" target="_blank" rel="noopener">Unsplash</a>'
        requests.post(f"{WP_URL}/wp-json/wp/v2/media/{media['id']}",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"alt_text": alt_text, "caption": caption})
        return media["id"], media.get("source_url", "")
    except Exception as e:
        print(f"[{now()}] Błąd wgrywania zdjęcia: {e}")
        return None, None

def choose_keyword():
    history_path = "keywords/waza_used.json"
    used = []
    if os.path.exists(history_path):
        with open(history_path) as f:
            used = json.load(f)
    available = [k for k in KEYWORDS if k["focus"] not in used]
    if not available:
        available = KEYWORDS
        used = []
    chosen = random.choice(available)
    used.append(chosen["focus"])
    os.makedirs("keywords", exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(used, f, ensure_ascii=False)
    return chosen

def generate_article(kw, image):
    focus = kw["focus"]
    related = kw.get("related", [])
    all_kw = ", ".join([focus] + related)
    services_str = "\n".join([f'- <a href="{s["url"]}">{s["name"]}</a> — {s["desc"]}' for s in random.sample(SERVICES, min(3, len(SERVICES)))])
    ext_str = "\n".join([f'- <a href="{l["url"]}" target="_blank" rel="nofollow noopener">{l["name"]}</a>' for l in random.sample(EXTERNAL_LINKS, 2)])

    img_html = ""
    if image:
        attribution = f'<p style="font-size:0.75rem;color:#888;margin-top:4px;">Photo by <a href="{image["photographer_url"]}" target="_blank" rel="noopener">{image["photographer"]}</a> on <a href="{image["unsplash_url"]}" target="_blank" rel="noopener">Unsplash</a></p>'
        img_html = f'<figure style="margin:20px 0;"><img src="{image["url"]}" alt="{focus}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;">{attribution}</figure>'

    print(f"[{now()}] Generuję metadane...")
    meta_raw = claude_request(f"""Dla artykułu SEO o "{all_kw}" dla firmy cateringowej Waża Kotlina (Ziemia Kłodzka) zwróć TYLKO JSON:
{{"title":"max 60 znaków z frazą {focus}","slug":"slug-ascii","meta_description":"max 160 znaków z frazą i CTA","focus_keyword":"{focus}","all_keywords":"{all_kw}"}}""", 400)
    meta_raw = re.sub(r'```json\s*|```\s*', '', meta_raw).strip()
    meta = json.loads(meta_raw[meta_raw.find('{'):meta_raw.rfind('}')+1])
    print(f"[{now()}] Metadane OK: {meta['title']}")

    print(f"[{now()}] Generuję treść...")
    content = claude_request(f"""Napisz artykuł blogowy po polsku (~{kw['length']} słów) o: {all_kw}
Firma: Waża Kotlina — catering i eventy na Ziemi Kłodzkiej, tel. 512 777 662, waza.catering@gmail.com

Zwróć TYLKO czysty HTML zaczynając od <div class="toc">.

STRUKTURA:
1. Spis treści: <div class="toc"><h2>Spis treści</h2><ul>...</ul></div>
2. Pierwsze 100 słów zawiera "{focus}"
3. Min 5 nagłówków H2
4. Linki do usług: {services_str}
5. Link do kontaktu: <a href="https://wazakotlina.pl/kontakt/">zapytaj o wycenę</a>
6. Zdjęcie: {img_html}
7. Linki zewnętrzne: {ext_str}
8. FAQ: min 4 pytania H3+P o {focus}
9. CTA na końcu z numerem 512 777 662

Używaj "{focus}" 10-15 razy. Krótkie akapity. Lokalne frazy: Kotlina Kłodzka, Ziemia Kłodzka, Kłodzko.""", 7000)
    print(f"[{now()}] Treść OK, {len(content)} znaków")

    return {
        "title": meta["title"],
        "slug": meta["slug"],
        "meta_description": meta["meta_description"],
        "focus_keyword": meta["focus_keyword"],
        "all_keywords": meta.get("all_keywords", focus),
        "content": content,
    }

def publish(article, featured_id=None):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    body = {
        "title": article["title"], "slug": article["slug"],
        "content": article["content"], "excerpt": article["meta_description"],
        "status": POST_STATUS,
    }
    if featured_id:
        body["featured_media"] = featured_id
    res = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json=body)
    res.raise_for_status()
    post = res.json()
    print(f"[{now()}] Opublikowano ID: {post['id']} — {post.get('link','')}")
    return post["id"], post.get("link", "")

def set_rank_math(post_id, keywords, title, description):
    try:
        res = requests.post(f"{WP_URL}/wp-json/directwebs/v1/set-seo",
            json={"post_id": post_id, "keywords": keywords, "title": title, "description": description, "token": DW_TOKEN},
            timeout=10)
        res.raise_for_status()
        if res.json().get("success"):
            print(f"[{now()}] Rank Math OK")
    except Exception as e:
        print(f"[{now()}] Rank Math błąd: {e}")

def notify_indexing(post_url):
    gsc_json = os.environ.get("GSC_SERVICE_ACCOUNT", "")
    if not gsc_json:
        return
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_info(
            json.loads(gsc_json), scopes=["https://www.googleapis.com/auth/indexing"])
        service = build("indexing", "v3", credentials=creds)
        service.urlNotifications().publish(body={"url": post_url, "type": "URL_UPDATED"}).execute()
        print(f"[{now()}] Google Indexing API OK — {post_url}")
    except Exception as e:
        print(f"[{now()}] Indexing API błąd: {e}")

def main():
    print(f"\n{'='*50}")
    print(f"Waża Kotlina — Auto SEO Poster — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    kw = choose_keyword()
    print(f"[{now()}] Fraza: {kw['focus']}")

    image = get_unsplash_image(kw["focus"])
    featured_id = None
    if image:
        featured_id, _ = upload_image(image, kw["focus"])

    article = generate_article(kw, image)
    post_id, post_url = publish(article, featured_id)
    set_rank_math(post_id, article["all_keywords"], article["title"][:60], article["meta_description"][:160])
    notify_indexing(post_url)

    print(f"\n{'='*50}")
    print(f"SUKCES!")
    print(f"Tytuł:   {article['title']}")
    print(f"Fraza:   {article['all_keywords']}")
    print(f"Post ID: {post_id}")
    print(f"URL:     {post_url}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
