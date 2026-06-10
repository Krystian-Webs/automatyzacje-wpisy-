#!/usr/bin/env python3
"""
DirectWebs — Auto SEO Blog Post Generator v4
- Google Search Console API (frazy z pozycji 5-20)
- Claude analizuje i wybiera najlepsze frazy
- Unsplash zdjecia
- Rank Math 80+/100
"""

import os
import re
import json
import random
import base64
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

WP_URL        = os.environ["WP_URL"].rstrip("/")
WP_USER       = os.environ["WP_USER"]
WP_PASSWORD   = os.environ["WP_PASSWORD"]
CLAUDE_KEY    = os.environ["CLAUDE_KEY"]
UNSPLASH_KEY  = os.environ.get("UNSPLASH_KEY", "")
WP_CATEGORY   = int(os.environ.get("WP_CATEGORY_ID", "1"))
POST_STATUS   = os.environ.get("POST_STATUS", "publish")
DW_TOKEN      = "directwebs2026"
GSC_JSON      = os.environ.get("GSC_SERVICE_ACCOUNT", "")
GSC_SITE      = "sc-domain:directwebs.pl"

PORTFOLIO_SITES = [
    {"url": "https://dmitrowsky.pl", "name": "Dmitrowsky Content Lab", "desc": "fotograf i filmowiec"},
    {"url": "https://funpower.pl", "name": "Fun&Power", "desc": "autoryzowany dealer Yamaha"},
    {"url": "https://bolkoconcept.pl", "name": "Bolko Concept", "desc": "sklep z odziezą lnianą"},
    {"url": "https://bizneswsocial.pl", "name": "Biznes w Social", "desc": "marketing w social media"},
    {"url": "https://wazakotlina.pl", "name": "Waża Kotlina", "desc": "agroturystyka i noclegi"},
    {"url": "https://tamitu.com.pl", "name": "TamiTu", "desc": "strona usługowa"},
    {"url": "https://piotrowski-krotoszyn.pl", "name": "Piotrowski Krotoszyn", "desc": "biuro nieruchomości"},
    {"url": "https://regeneracja-turbo.eu", "name": "Regeneracja Turbo", "desc": "serwis turbosprężarek"},
    {"url": "https://kantorfloren.pl", "name": "Kantorfloren", "desc": "strona internetowa"},
    {"url": "https://klodzkieszlaki.pl", "name": "Kłodzkie Szlaki", "desc": "turystyka i szlaki"},
]

EXTERNAL_LINKS = [
    {"url": "https://web.dev/performance/", "name": "web.dev", "desc": "optymalizacja wydajności stron"},
    {"url": "https://developers.google.com/search/docs", "name": "Google Search Central", "desc": "dokumentacja SEO Google"},
    {"url": "https://pl.wikipedia.org/wiki/Optymalizacja_dla_wyszukiwarek_internetowych", "name": "Wikipedia SEO", "desc": "pozycjonowanie stron"},
    {"url": "https://pl.wikipedia.org/wiki/WordPress", "name": "Wikipedia WordPress", "desc": "system zarządzania treścią"},
    {"url": "https://schema.org/Article", "name": "Schema.org", "desc": "strukturyzowane dane"},
    {"url": "https://pagespeed.web.dev/", "name": "Google PageSpeed", "desc": "szybkość ładowania stron"},
]

def now():
    return datetime.now().strftime("%H:%M:%S")

def claude_request(prompt, max_tokens=1000):
    headers = {
        "x-api-key": CLAUDE_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
    res.raise_for_status()
    return res.json()["content"][0]["text"].strip()

def get_gsc_keywords():
    """Pobiera frazy z Google Search Console na pozycji 5-20."""
    if not GSC_JSON:
        print(f"[{now()}] Brak GSC_SERVICE_ACCOUNT, uzywam list.json")
        return None

    try:
        creds_data = json.loads(GSC_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=creds)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=GSC_SITE,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 100,
                "dimensionFilterGroups": [{
                    "filters": [{
                        "dimension": "query",
                        "operator": "notContains",
                        "expression": "directwebs"
                    }]
                }]
            }
        ).execute()

        rows = response.get("rows", [])
        
        # Filtruj frazy na pozycji 5-20 (łatwe do podbicia)
        good_keywords = []
        for row in rows:
            query = row["keys"][0]
            position = row.get("position", 0)
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            
            if 4 <= position <= 20 and impressions >= 10 and len(query) > 3:
                good_keywords.append({
                    "query": query,
                    "position": round(position, 1),
                    "clicks": clicks,
                    "impressions": impressions
                })

        print(f"[{now()}] GSC: znaleziono {len(good_keywords)} fraz na pozycji 5-20")
        return good_keywords if good_keywords else None

    except Exception as e:
        print(f"[{now()}] Blad GSC: {e}")
        return None

def load_keywords_from_file():
    """Fallback — wczytaj frazy z list.json."""
    path = os.path.join(os.path.dirname(__file__), "keywords", "list.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    history_path = os.path.join(os.path.dirname(__file__), "keywords", "used.json")
    used = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            used = json.load(f)
    available = [kw for kw in data if kw["focus"] not in used]
    if not available:
        available = data
        used = []
    chosen = random.choice(available)
    used.append(chosen["focus"])
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False)
    return chosen

def choose_best_keyword(gsc_keywords):
    """Claude wybiera najlepszą frazę z danych GSC."""
    kw_list = "\n".join([
        f"- \"{k['query']}\" (pozycja: {k['position']}, wyswietlenia: {k['impressions']}, klikniecia: {k['clicks']})"
        for k in gsc_keywords[:30]
    ])

    prompt = f"""Jesteś ekspertem SEO. Masz dane z Google Search Console dla strony agencji webdesign directwebs.pl.

Frazy na pozycji 5-20 (łatwe do podbicia artykułem blogowym):
{kw_list}

Wybierz JEDNĄ najlepszą frazę do napisania artykułu blogowego. Kryteria:
1. Duże wyświetlenia (wysoki potencjał ruchu)
2. Fraza informacyjna (pasuje do artykułu poradnikowego)
3. Związana z tworzeniem stron, SEO, WordPress lub webdesignem

Zwróć TYLKO JSON bez tekstu przed ani po:
{{"focus":"wybrana fraza","reason":"krótkie uzasadnienie","related":["fraza powiązana 1","fraza powiązana 2","fraza powiązana 3"],"type":"poradnik","length":1800}}"""

    raw = claude_request(prompt, 500)
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw).strip()
    start = raw.find('{')
    end = raw.rfind('}') + 1
    result = json.loads(raw[start:end])
    print(f"[{now()}] Claude wybrał: \"{result['focus']}\" — {result['reason']}")
    return result

def get_blog_posts():
    try:
        res = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"per_page": 20, "status": "publish", "_fields": "id,title,link"},
            timeout=10
        )
        res.raise_for_status()
        posts = res.json()
        return [{"title": p["title"]["rendered"], "url": p["link"]} for p in posts]
    except Exception as e:
        print(f"[{now()}] Blad pobierania wpisow: {e}")
        return []

def get_unsplash_images(keyword, count=3):
    if not UNSPLASH_KEY:
        return []
    try:
        en_keyword = keyword.replace("strona internetowa", "website")
        en_keyword = en_keyword.replace("sklep internetowy", "online store")
        en_keyword = en_keyword.replace("pozycjonowanie", "SEO optimization")
        en_keyword = en_keyword.replace("strony www", "website design")
        en_keyword = en_keyword.replace("hosting", "web hosting server")
        en_keyword = en_keyword.replace("wordpress", "wordpress website")

        res = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": en_keyword, "per_page": 10, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
        )
        res.raise_for_status()
        results = res.json().get("results", [])
        images = []
        for photo in results[:count]:
            images.append({
                "url": photo["urls"]["regular"],
                "photographer": photo["user"]["name"],
                "alt": photo.get("alt_description", keyword) or keyword
            })
        print(f"[{now()}] Pobrano {len(images)} zdjec z Unsplash")
        return images
    except Exception as e:
        print(f"[{now()}] Blad Unsplash: {e}")
        return []

def upload_image_to_wordpress(image_url, alt_text, title):
    try:
        img_res = requests.get(image_url, timeout=30)
        img_res.raise_for_status()

        auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()

        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = filename.encode('ascii', 'ignore').decode('ascii')
        filename = re.sub(r'[\s]+', '-', filename)[:40]
        filename = filename.strip('-') + f"-{random.randint(100,999)}.jpg"
        if not filename or filename == ".jpg":
            filename = f"image-{random.randint(1000,9999)}.jpg"

        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
        }

        res = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers=headers,
            data=img_res.content
        )
        res.raise_for_status()
        media = res.json()
        media_id = media["id"]
        media_url = media.get("source_url", "")

        auth_headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers=auth_headers,
            json={"alt_text": alt_text, "caption": f"Fot. {alt_text}"}
        )

        return media_id, media_url
    except Exception as e:
        print(f"[{now()}] Blad wgrywania zdjecia: {e}")
        return None, None

def set_rank_math_seo(post_id, keywords, title, description):
    try:
        res = requests.post(
            f"{WP_URL}/wp-json/directwebs/v1/set-seo",
            json={
                "post_id": post_id,
                "keywords": keywords,
                "title": title,
                "description": description,
                "token": DW_TOKEN,
            },
            timeout=10
        )
        res.raise_for_status()
        data = res.json()
        if data.get("success"):
            print(f"[{now()}] Rank Math OK — frazy: {keywords}")
    except Exception as e:
        print(f"[{now()}] Blad Rank Math: {e}")

def generate_article(kw_data, blog_posts, images):
    focus   = kw_data["focus"]
    related = kw_data.get("related", [])
    art_type = kw_data.get("type", "poradnik")
    length  = kw_data.get("length", 1800)
    all_keywords = ", ".join([focus] + related)

    type_desc = {
        "poradnik":   "poradnik how-to z praktycznymi krokami",
        "porownanie": "artykul porownawczy",
        "lista":      "artykul w formie listy Top X",
        "faq":        "artykul FAQ z pytaniami i odpowiedziami",
        "lokalne":    "artykul SEO lokalny",
    }.get(art_type, "artykul blogowy")

    portfolio_links = random.sample(PORTFOLIO_SITES, min(3, len(PORTFOLIO_SITES)))
    portfolio_str = "\n".join([f'- <a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a> ({s["desc"]})' for s in portfolio_links])

    ext_links = random.sample(EXTERNAL_LINKS, min(2, len(EXTERNAL_LINKS)))
    ext_str = "\n".join([f'- <a href="{l["url"]}" target="_blank" rel="nofollow noopener">{l["name"]}</a> ({l["desc"]})' for l in ext_links])

    internal_posts = random.sample(blog_posts, min(3, len(blog_posts))) if blog_posts else []
    internal_str = "\n".join([f'- <a href="{p["url"]}">{p["title"]}</a>' for p in internal_posts])

    img_placeholders = ""
    for i, img in enumerate(images[:2]):
        img_placeholders += f'\nZDJECIE_{i+1}: <img src="{img["url"]}" alt="{focus} - {img["alt"]}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;margin:20px 0;">\n'

    # KROK 1: Metadane
    print(f"[{now()}] Krok 1: Generuje metadane...")
    meta_prompt = f"""Dla artykulu SEO o frazach "{all_keywords}" zwroc TYLKO JSON bez tekstu przed ani po:
{{"title":"max 60 znakow — fraza {focus} na poczatku","slug":"slug-ascii","meta_description":"max 160 znakow z fraza {focus} i CTA","focus_keyword":"{focus}","all_keywords":"{focus}, {', '.join(related)}"}}"""

    meta_raw = claude_request(meta_prompt, 600)
    meta_raw = re.sub(r'```json\s*', '', meta_raw)
    meta_raw = re.sub(r'```\s*', '', meta_raw).strip()
    start = meta_raw.find('{')
    end = meta_raw.rfind('}') + 1
    json_candidate = meta_raw[start:end]
    try:
        meta = json.loads(json_candidate)
    except json.JSONDecodeError:
        meta = json.loads(json_candidate.split('\n')[0])
    print(f"[{now()}] Metadane OK: {meta['title']}")

    # KROK 2: Tresc
    print(f"[{now()}] Krok 2: Generuje tresc artykulu...")
    content_prompt = f"""Napisz {type_desc} po polsku (~{length} slow) o frazach: {all_keywords}.
Glowna fraza: "{focus}"

Zwroc TYLKO czysty HTML. Bez komentarzy. Bez markdown. Zacznij od <div class="toc">.

STRUKTURA:
1. SPIS TRESCI: <div class="toc"><h2>Spis treści</h2><ul>[lista H2]</ul></div>
2. PIERWSZE 100 SLOW zawiera "{focus}"
3. MIN 6 H2 z wariantami frazy "{focus}"
4. LINKI WEWNETRZNE: {internal_str if internal_str else "brak"}
5. LINKI PORTFOLIO: {portfolio_str}
6. LINKI ZEWNETRZNE: {ext_str}
7. ZDJECIA: {img_placeholders}
8. LINK: <a href="https://directwebs.pl/skontaktuj-sie-porozmawiajmy-o-twoim-projekcie/">bezplatna wycena strony</a>
9. FAQ: <h2 id="faq">FAQ — {focus}</h2> (min 5 pytan h3+p)
10. CTA na koncu

WAZNE: uzyj "{focus}" 15-20 razy, krotkie akapity, <strong> dla pojec"""

    content = claude_request(content_prompt, 8000)
    print(f"[{now()}] Tresc OK, {len(content)} znakow")

    return {
        "title": meta["title"],
        "slug": meta["slug"],
        "meta_description": meta["meta_description"],
        "focus_keyword": meta["focus_keyword"],
        "all_keywords": meta.get("all_keywords", focus),
        "content": content,
    }

def publish_to_wordpress(article, featured_media_id=None):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }

    print(f"[{now()}] Publikuje na WordPress...")
    body = {
        "title":      article["title"],
        "slug":       article["slug"],
        "content":    article["content"],
        "excerpt":    article["meta_description"],
        "status":     POST_STATUS,
        "categories": [WP_CATEGORY],
    }

    if featured_media_id:
        body["featured_media"] = featured_media_id

    res = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=body)
    res.raise_for_status()
    post = res.json()
    post_id = post["id"]
    post_url = post.get("link", "")
    print(f"[{now()}] Wpis utworzony ID: {post_id} — {post_url}")
    return post_id, post_url

def main():
    print(f"\n{'='*50}")
    print(f"DirectWebs Auto SEO Poster v4 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # Pobierz frazy — najpierw z GSC, fallback na list.json
    gsc_keywords = get_gsc_keywords()

    if gsc_keywords:
        print(f"[{now()}] Uzywam danych z Google Search Console ({len(gsc_keywords)} fraz)")
        kw_data = choose_best_keyword(gsc_keywords)
    else:
        print(f"[{now()}] Uzywam fraz z list.json")
        kw_data = load_keywords_from_file()

    print(f"[{now()}] Wybrano: {kw_data['focus']}")

    blog_posts = get_blog_posts()
    images = get_unsplash_images(kw_data["focus"], count=3)

    uploaded_images = []
    for img in images:
        media_id, media_url = upload_image_to_wordpress(
            img["url"],
            f"{kw_data['focus']} - {img['alt']}",
            kw_data["focus"]
        )
        if media_id:
            uploaded_images.append({"id": media_id, "url": media_url, "alt": img["alt"]})

    for i, img in enumerate(images[:3]):
        if i < len(uploaded_images):
            images[i]["url"] = uploaded_images[i]["url"]

    article = generate_article(kw_data, blog_posts, images)
    featured_media_id = uploaded_images[0]["id"] if uploaded_images else None
    post_id, post_url = publish_to_wordpress(article, featured_media_id)

    seo_title = article["title"][:60]
    seo_desc = article["meta_description"][:160]
    set_rank_math_seo(post_id, article["all_keywords"], seo_title, seo_desc)

    print(f"\n{'='*50}")
    print(f"SUKCES!")
    print(f"Tytul:   {article['title']}")
    print(f"Keyword: {article['all_keywords']}")
    print(f"Post ID: {post_id}")
    print(f"URL:     {post_url}")
    print(f"Okladka: {'TAK' if featured_media_id else 'BRAK'}")
    print(f"Zdjecia: {len(uploaded_images)}")
    print(f"Zrodlo:  {'Google Search Console' if gsc_keywords else 'list.json'}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
