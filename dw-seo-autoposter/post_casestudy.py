#!/usr/bin/env python3
"""
DirectWebs — Case Study Poster
Co tydzień publikuje artykul "case study" o jednej z realizacji portfolio DirectWebs.
Buduje autorytet (E-E-A-T) i daje naturalny link do zywych projektow.
"""

import os
import re
import json
import base64
import requests
from datetime import datetime

WP_URL      = os.environ["WP_URL"].rstrip("/")
WP_USER     = os.environ["WP_USER"]
WP_PASSWORD = os.environ["WP_PASSWORD"]
CLAUDE_KEY  = os.environ["CLAUDE_KEY"]
WP_CATEGORY = int(os.environ.get("WP_CATEGORY_ID", "1"))
POST_STATUS = os.environ.get("POST_STATUS", "publish")
DW_TOKEN    = "directwebs2026"

# ── PORTFOLIO — case study (rotacja po kolei) ─────────────────
# desc: krotki opis | work: co konkretnie zrobil DirectWebs | industry: branza
PORTFOLIO = [
    {"url": "https://piotrowski-krotoszyn.pl", "name": "Piotrowski Krotoszyn",
     "industry": "biuro nieruchomości",
     "work": "strona internetowa z prezentacją ofert nieruchomości, formularzem kontaktowym i SEO lokalnym pod Krotoszyn"},
    {"url": "https://abmmarket.pl", "name": "ABM Market",
     "industry": "dystrybucja wody Staropolanka",
     "work": "sklep internetowy WooCommerce z katalogiem produktów wody źródlanej, konfiguracja płatności i automatyczne SEO produktów"},
    {"url": "https://snugy.pl", "name": "Snugy",
     "industry": "sklep z materacami online",
     "work": "sklep WooCommerce z prezentacją materacy, opisami produktów i optymalizacją Core Web Vitals"},
    {"url": "https://wazakotlina.pl", "name": "Waża Kotlina",
     "industry": "catering i eventy w Kotlinie Kłodzkiej",
     "work": "strona z prezentacją usług cateringowych i sal eventowych, automatyczny blog SEO publikujący artykuły lokalne"},
    {"url": "https://dmitrowsky.pl", "name": "Dmitrowsky Content Lab",
     "industry": "fotografia i film",
     "work": "portfolio online z galerią realizacji, zoptymalizowane pod szybkie ładowanie zdjęć"},
    {"url": "https://funpower.pl", "name": "Fun&Power",
     "industry": "autoryzowany dealer Yamaha",
     "work": "strona dealerska z prezentacją oferty motocykli i sprzętu, formularz kontaktowy do salonu"},
    {"url": "https://bolkoconcept.pl", "name": "Bolko Concept",
     "industry": "odzież lniana",
     "work": "sklep internetowy z kolekcją odzieży, identyfikacja wizualna marki i grafiki produktowe"},
    {"url": "https://bizneswsocial.pl", "name": "Biznes w Social",
     "industry": "marketing w social media",
     "work": "strona usługowa prezentująca ofertę marketingową z landing page pod kampanie"},
    {"url": "https://tamitu.com.pl", "name": "TamiTu",
     "industry": "usługi lokalne",
     "work": "strona usługowa z podstawowym SEO i formularzem kontaktowym"},
    {"url": "https://regeneracja-turbo.eu", "name": "Regeneracja Turbo",
     "industry": "serwis turbosprężarek",
     "work": "strona usługowa z opisem usług regeneracji i formularzem zapytań"},
    {"url": "https://kantorfloren.pl", "name": "Kantorfloren",
     "industry": "usługi finansowe",
     "work": "strona wizytówkowa z informacjami o usługach i danymi kontaktowymi"},
    {"url": "https://klodzkieszlaki.pl", "name": "Kłodzkie Szlaki",
     "industry": "turystyka — Ziemia Kłodzka",
     "work": "serwis turystyczny prezentujący szlaki i atrakcje regionu, SEO lokalne"},
]

STATE_FILE = "casestudy_state.json"

def now():
    return datetime.now().strftime("%H:%M:%S")

def claude_request(prompt, max_tokens=4000):
    headers = {"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": "claude-sonnet-4-6", "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
    if res.status_code != 200:
        print(f"[CLAUDE API ERROR {res.status_code}] {res.text}")
    res.raise_for_status()
    return res.json()["content"][0]["text"].strip()

def get_next_project():
    """Rotacja po kolei — pamieta indeks w pliku state."""
    idx = 0
    if os.path.exists(STATE_FILE):
        try:
            idx = json.load(open(STATE_FILE)).get("idx", 0)
        except Exception:
            idx = 0
    project = PORTFOLIO[idx % len(PORTFOLIO)]
    json.dump({"idx": idx + 1}, open(STATE_FILE, "w"))
    return project

def set_seo(post_id, keywords, title, description):
    try:
        res = requests.post(f"{WP_URL}/wp-json/directwebs/v1/set-seo",
            json={"post_id": post_id, "keywords": keywords, "title": title,
                  "description": description, "token": DW_TOKEN}, timeout=10)
        res.raise_for_status()
        print(f"[{now()}] SEO ustawione: {res.json().get('plugin_used')}")
    except Exception as e:
        print(f"[{now()}] Blad SEO: {e}")

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
        service.urlNotifications().publish(
            body={"url": post_url, "type": "URL_UPDATED"}).execute()
        print(f"[{now()}] Google Indexing API OK")
    except Exception as e:
        print(f"[{now()}] Blad Indexing API: {e}")

def generate_case_study(project):
    prompt = f"""Napisz case study (artykul blogowy) po polsku (~1200-1500 slow) o realizacji strony internetowej dla klienta.

KLIENT: {project['name']} ({project['industry']})
LINK DO ZYWEJ STRONY: {project['url']}
CO ZROBIL DIRECTWEBS: {project['work']}

Zwroc TYLKO JSON bez tekstu przed/po:
{{
  "title": "tytul max 60 znakow, np. 'Jak stworzylismy strone dla {project['name']}'",
  "slug": "slug-ascii",
  "meta_description": "max 160 znakow, zachecajacy opis case study",
  "focus_keyword": "strona internetowa dla {project['industry']}",
  "content": "PELNY HTML artykulu — bez markdown, bez komentarzy"
}}

STRUKTURA TRESCI (w polu content):
1. Wstep — krotko o kliencie i wyzwaniu (branza: {project['industry']})
2. <h2>Co przygotowalismy</h2> — opis realizacji: {project['work']}
3. <h2>Efekty</h2> — opisz spodziewane/realne korzysci (szybkosc, UX, SEO, konwersja)
4. Link do zywej strony: <a href="{project['url']}" target="_blank" rel="noopener">{project['name']}</a>
5. <h2>Chcesz podobna strone?</h2> z linkiem <a href="https://directwebs.pl/skontaktuj-sie-porozmawiajmy-o-twoim-projekcie/">bezplatna wycena</a>
6. Krotkie CTA na koniec

WAZNE: pisz konkretnie, profesjonalnie, jak case study agencji. Uzyj <h2>, <p>, <strong>. Min 3 naglowki H2."""

    raw = claude_request(prompt, 6000)
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw).strip()
    start = raw.find('{')
    end = raw.rfind('}') + 1
    return json.loads(raw[start:end])

def publish(article):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    body = {
        "title": article["title"],
        "slug": article["slug"],
        "content": article["content"],
        "excerpt": article["meta_description"],
        "status": POST_STATUS,
        "categories": [WP_CATEGORY],
    }
    res = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=body)
    res.raise_for_status()
    post = res.json()
    print(f"[{now()}] Wpis utworzony ID: {post['id']} — {post.get('link')}")
    return post["id"], post.get("link")

def main():
    print(f"\n{'='*50}")
    print(f"DirectWebs Case Study Poster — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    project = get_next_project()
    print(f"[{now()}] Realizacja: {project['name']} ({project['url']})")

    article = generate_case_study(project)
    print(f"[{now()}] Tytul: {article['title']}")

    post_id, post_url = publish(article)
    set_seo(post_id, article["focus_keyword"], article["title"][:60], article["meta_description"][:160])
    notify_indexing(post_url)

    print(f"\n{'='*50}\nSUKCES! {article['title']}\n{'='*50}\n")

if __name__ == "__main__":
    main()
