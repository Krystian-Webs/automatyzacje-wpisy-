#!/usr/bin/env python3
"""
DirectWebs — Auto SEO Blog Post Generator
Uruchamia się automatycznie przez GitHub Actions (wt/czw/sob o 8:00)
"""

import os
import json
import random
import base64
import requests
from datetime import datetime

# ── KONFIGURACJA Z GITHUB SECRETS ─────────────────────
WP_URL      = os.environ["WP_URL"].rstrip("/")
WP_USER     = os.environ["WP_USER"]
WP_PASSWORD = os.environ["WP_PASSWORD"]
CLAUDE_KEY  = os.environ["CLAUDE_KEY"]
WP_CATEGORY = int(os.environ.get("WP_CATEGORY_ID", "1"))
POST_STATUS = os.environ.get("POST_STATUS", "publish")  # publish lub draft

# ── SŁOWA KLUCZOWE ────────────────────────────────────
# System losuje jedną grupę na każde uruchomienie
# Edytuj listę keywords/list.json żeby dodać własne frazy

def load_keywords():
    path = os.path.join(os.path.dirname(__file__), "keywords", "list.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Wczytaj historię użytych fraz
    history_path = os.path.join(os.path.dirname(__file__), "keywords", "used.json")
    used = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            used = json.load(f)
    
    # Wybierz frazę której jeszcze nie użyto
    available = [kw for kw in data if kw["focus"] not in used]
    
    # Jeśli wszystkie użyte — zacznij od nowa
    if not available:
        available = data
        used = []
    
    chosen = random.choice(available)
    
    # Zapisz jako użytą
    used.append(chosen["focus"])
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False)
    
    return chosen

# ── GENERUJ ARTYKUŁ PRZEZ CLAUDE ─────────────────────
def generate_article(kw_data):
    focus    = kw_data["focus"]
    related  = ", ".join(kw_data.get("related", []))
    art_type = kw_data.get("type", "poradnik")
    length   = kw_data.get("length", 1800)

    type_desc = {
        "poradnik":   "poradnik how-to z praktycznymi krokami",
        "porownanie": "artykuł porównawczy",
        "lista":      "artykuł w formie listy (Top X)",
        "faq":        "artykuł FAQ z pytaniami i odpowiedziami",
        "lokalne":    "artykuł SEO lokalny",
    }.get(art_type, "artykuł blogowy")

    prompt = f"""Jesteś ekspertem SEO i copywriterem dla agencji webdesign DirectWebs.pl z Polski.
Kontekst: DirectWebs tworzy strony WordPress i sklepy WooCommerce. Autor: Krystian. Lokalizacja: Polska.

Napisz {type_desc} (~{length} słów) zoptymalizowany pod frazy: {focus}, {related}
Focus keyword: "{focus}"

Zwróć WYŁĄCZNIE poprawny JSON (bez markdown, bez backticks, bez tekstu przed ani po):
{{
  "title": "tytuł SEO z focus keyword, max 60 znaków",
  "slug": "slug-bez-polskich-znakow",
  "meta_description": "meta opis 140-155 znaków z CTA",
  "focus_keyword": "{focus}",
  "content": "PELNA TRESC HTML"
}}

Wymagania dla content:
- H2 i H3 z wariantami frazy kluczowej
- Pierwsze 100 słów zawiera focus keyword
- Gęstość słowa kluczowego 1-1.5%
- Min 5 sekcji H2
- Sekcja FAQ na końcu (min 5 pytań jako <h3> + <p>)
- Link wewnętrzny: <a href="https://directwebs.pl/skontaktuj-sie-porozmawiajmy-o-twoim-projekcie/">bezpłatna wycena strony</a>
- Zakończ mocnym CTA do kontaktu
- <strong> przy ważnych pojęciach
- <ul>/<ol> gdzie pasuje
- Naturalny polski, bez sztucznego upychania fraz"""

    headers = {
        "x-api-key": CLAUDE_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }

    print(f"[{now()}] 🤖 Wysyłam prompt do Claude API...")
    res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
    res.raise_for_status()

    raw = res.json()["content"][0]["text"]

    # Wyciągnij JSON z odpowiedzi
    import re
    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        raise ValueError("Claude nie zwrócił poprawnego JSON")
    
    article = json.loads(match.group(0))
    print(f"[{now()}] ✅ Artykuł wygenerowany: {article['title']}")
    return article

# ── PUBLIKUJ NA WORDPRESS ─────────────────────────────
def publish_to_wordpress(article):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }

    # Utwórz wpis
    print(f"[{now()}] 📤 Publikuję na WordPress ({WP_URL})...")
    body = {
        "title":      article["title"],
        "slug":       article["slug"],
        "content":    article["content"],
        "excerpt":    article["meta_description"],
        "status":     POST_STATUS,
        "categories": [WP_CATEGORY],
    }

    res = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=body)
    res.raise_for_status()
    post = res.json()
    post_id = post["id"]
    print(f"[{now()}] ✅ Wpis utworzony (ID: {post_id})")

    # Ustaw Rank Math meta
    print(f"[{now()}] 🏷️  Ustawiam Rank Math SEO...")
    meta = {
        "meta": {
            "rank_math_focus_keyword":       article.get("focus_keyword", ""),
            "rank_math_description":          article.get("meta_description", ""),
            "rank_math_title":                article["title"] + " — DirectWebs",
            "rank_math_robots":               ["index", "follow"],
            "rank_math_rich_snippet":         "article",
            "rank_math_snippet_article_type": "BlogPosting",
        }
    }
    requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=headers, json=meta)
    print(f"[{now()}] ✅ Rank Math ustawiony")

    return post_id, post.get("link", "")

# ── UTILS ─────────────────────────────────────────────
def now():
    return datetime.now().strftime("%H:%M:%S")

# ── MAIN ──────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"DirectWebs Auto SEO Poster — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    print(f"[{now()}] 🔍 Wybieram słowo kluczowe...")
    kw_data = load_keywords()
    print(f"[{now()}] ✅ Wybrano: {kw_data['focus']}")

    article = generate_article(kw_data)

    post_id, post_url = publish_to_wordpress(article)

    print(f"\n{'='*50}")
    print(f"✅ SUKCES!")
    print(f"Tytuł:    {article['title']}")
    print(f"Keyword:  {article['focus_keyword']}")
    print(f"Post ID:  {post_id}")
    print(f"URL:      {post_url}")
    print(f"Status:   {POST_STATUS}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
