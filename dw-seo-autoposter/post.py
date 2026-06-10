#!/usr/bin/env python3
"""
DirectWebs — Auto SEO Blog Post Generator
Uruchamia się automatycznie przez GitHub Actions (wt/czw/sob o 8:00)
"""

import os
import re
import json
import random
import base64
import requests
from datetime import datetime

WP_URL        = os.environ["WP_URL"].rstrip("/")
WP_USER       = os.environ["WP_USER"]
WP_PASSWORD   = os.environ["WP_PASSWORD"]
CLAUDE_KEY    = os.environ["CLAUDE_KEY"]
UNSPLASH_KEY  = os.environ.get("UNSPLASH_KEY", "")
WP_CATEGORY   = int(os.environ.get("WP_CATEGORY_ID", "1"))
POST_STATUS   = os.environ.get("POST_STATUS", "publish")

def load_keywords():
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

def get_unsplash_image(keyword):
    if not UNSPLASH_KEY:
        print(f"[{now()}] Brak UNSPLASH_KEY, pomijam zdjecie")
        return None
    try:
        en_keyword = keyword.replace("strona internetowa", "website")
        en_keyword = en_keyword.replace("sklep internetowy", "online store")
        en_keyword = en_keyword.replace("pozycjonowanie", "SEO")
        en_keyword = en_keyword.replace("strony www", "website")
        en_keyword = en_keyword.replace("hosting", "web hosting")

        res = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": en_keyword, "per_page": 5, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}
        )
        res.raise_for_status()
        results = res.json().get("results", [])
        if not results:
            print(f"[{now()}] Brak wynikow Unsplash dla: {en_keyword}")
            return None
        photo = random.choice(results[:3])
        image_url = photo["urls"]["regular"]
        photographer = photo["user"]["name"]
        print(f"[{now()}] Znaleziono zdjecie (fot. {photographer})")
        return image_url
    except Exception as e:
        print(f"[{now()}] Blad Unsplash: {e}")
        return None

def upload_image_to_wordpress(image_url, title):
    try:
        print(f"[{now()}] Pobieram zdjecie z Unsplash...")
        img_res = requests.get(image_url, timeout=30)
        img_res.raise_for_status()

        auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()

        # Bezpieczna nazwa pliku - tylko ASCII
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = filename.encode('ascii', 'ignore').decode('ascii')
        filename = re.sub(r'[\s]+', '-', filename)[:50] + ".jpg"
        filename = filename.strip('-')
        if not filename or filename == ".jpg":
            filename = "featured-image.jpg"

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
        media_id = res.json()["id"]
        print(f"[{now()}] Zdjecie wgrane do WP, ID: {media_id}")
        return media_id
    except Exception as e:
        print(f"[{now()}] Blad wgrywania zdjecia: {e}")
        return None

def generate_article(kw_data):
    focus    = kw_data["focus"]
    related  = ", ".join(kw_data.get("related", []))
    art_type = kw_data.get("type", "poradnik")
    length   = kw_data.get("length", 1800)

    type_desc = {
        "poradnik":   "poradnik how-to z praktycznymi krokami",
        "porownanie": "artykul porownawczy",
        "lista":      "artykul w formie listy Top X",
        "faq":        "artykul FAQ z pytaniami i odpowiedziami",
        "lokalne":    "artykul SEO lokalny",
    }.get(art_type, "artykul blogowy")

    print(f"[{now()}] Krok 1: Generuje metadane...")
    meta_prompt = f"""Dla artykulu SEO o frazie "{focus}" zwroc TYLKO ten JSON bez zadnego tekstu przed ani po:
{{"title":"tytuł max 60 znaków z frazą {focus}","slug":"slug-bez-polskich-znakow","meta_description":"opis 140-155 znaków z CTA","focus_keyword":"{focus}"}}"""

    meta_raw = claude_request(meta_prompt, 500)
    meta_raw = re.sub(r'```json\s*', '', meta_raw)
    meta_raw = re.sub(r'```\s*', '', meta_raw).strip()
    start = meta_raw.find('{')
    end = meta_raw.rfind('}') + 1
    meta = json.loads(meta_raw[start:end])
    print(f"[{now()}] Metadane OK: {meta['title']}")

    print(f"[{now()}] Krok 2: Generuje tresc artykulu...")
    content_prompt = f"""Napisz {type_desc} po polsku (~{length} slow) o frazie "{focus}" (powiazane: {related}).

Zwroc TYLKO czysty HTML bez zadnych komentarzy, bez markdown, bez tekstu przed ani po.
Zacznij od <h2> (nie od h1).

Wymagania:
- Min 5 sekcji H2 z wariantami frazy "{focus}"
- Pierwsze 100 slow zawiera "{focus}"
- Gestosc slowa kluczowego 1-1.5%
- Sekcja FAQ na koncu min 5 pytan jako h3 + p
- Dodaj link: <a href="https://directwebs.pl/skontaktuj-sie-porozmawiajmy-o-twoim-projekcie/">bezplatna wycena strony</a>
- Zakonczenie z CTA
- Naturalny polski jezyk"""

    content = claude_request(content_prompt, 8000)
    print(f"[{now()}] Tresc OK, dlugosc: {len(content)} znakow")

    return {
        "title": meta["title"],
        "slug": meta["slug"],
        "meta_description": meta["meta_description"],
        "focus_keyword": meta["focus_keyword"],
        "content": content,
    }

def publish_to_wordpress(article, featured_media_id=None):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }

    print(f"[{now()}] Publikuje na WordPress ({WP_URL})...")
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
        print(f"[{now()}] Ustawiam okładkę (media ID: {featured_media_id})")

    res = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=body)
    res.raise_for_status()
    post = res.json()
    post_id = post["id"]
    print(f"[{now()}] Wpis utworzony ID: {post_id}")

    print(f"[{now()}] Ustawiam Rank Math SEO...")
    meta = {
        "meta": {
            "rank_math_focus_keyword":        article.get("focus_keyword", ""),
            "rank_math_description":           article.get("meta_description", ""),
            "rank_math_title":                 article["title"] + " - DirectWebs",
            "rank_math_robots":                ["index", "follow"],
            "rank_math_rich_snippet":          "article",
            "rank_math_snippet_article_type":  "BlogPosting",
        }
    }
    requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=headers, json=meta)
    print(f"[{now()}] Rank Math ustawiony")

    return post_id, post.get("link", "")

def now():
    return datetime.now().strftime("%H:%M:%S")

def main():
    print(f"\n{'='*50}")
    print(f"DirectWebs Auto SEO Poster - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    print(f"[{now()}] Wybieram slowo kluczowe...")
    kw_data = load_keywords()
    print(f"[{now()}] Wybrano: {kw_data['focus']}")

    article = generate_article(kw_data)

    featured_media_id = None
    image_url = get_unsplash_image(kw_data["focus"])
    if image_url:
        featured_media_id = upload_image_to_wordpress(image_url, article["title"])

    post_id, post_url = publish_to_wordpress(article, featured_media_id)

    print(f"\n{'='*50}")
    print(f"SUKCES!")
    print(f"Tytul:   {article['title']}")
    print(f"Keyword: {article['focus_keyword']}")
    print(f"Post ID: {post_id}")
    print(f"URL:     {post_url}")
    print(f"Okladka: {'TAK' if featured_media_id else 'BRAK'}")
    print(f"Status:  {POST_STATUS}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
