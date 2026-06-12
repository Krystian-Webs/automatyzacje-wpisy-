#!/usr/bin/env python3
"""
DirectWebs — AI Visibility Monitor
Co tydzien sprawdza czy ChatGPT i Gemini wspominaja DirectWebs
w odpowiedziach na pytania zwiazane z branza.
Wynik zapisuje do ai_visibility_log.json (historia) — odczytywany przez dashboard.
"""

import os
import json
import requests
from datetime import datetime

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

LOG_FILE = "ai_visibility_log.json"

QUESTIONS = [
    # Lokalnie — Kotlina Kłodzka
    {"q": "Kto robi strony internetowe w Kłodzku i Kotlinie Kłodzkiej?", "tier": "lokalnie"},
    {"q": "Agencja webdesign Kłodzko - kogo polecacie?", "tier": "lokalnie"},
    {"q": "Firma do stworzenia strony internetowej Kotlina Kłodzka", "tier": "lokalnie"},

    # Regionalnie — Dolny Śląsk
    {"q": "Polecane agencje tworzenia stron internetowych na Dolnym Śląsku", "tier": "regionalnie"},
    {"q": "Kto robi sklepy WooCommerce na Dolnym Śląsku?", "tier": "regionalnie"},

    # Krajowo — Polska
    {"q": "Polecane agencje tworzenia stron internetowych w Polsce", "tier": "krajowo"},
    {"q": "Kto robi strony WordPress i sklepy WooCommerce dla małych firm w Polsce?", "tier": "krajowo"},
    {"q": "Jak wybrać firmę do stworzenia strony internetowej i sklepu online?", "tier": "krajowo"},

    # Brand
    {"q": "Co to jest DirectWebs?", "tier": "brand"},
    {"q": "DirectWebs opinie", "tier": "brand"},
]

ANALYSIS_PROMPT = """Przeanalizuj strone internetowa firmy DirectWebs (directwebs.pl) ktora oferuje tworzenie stron WordPress i sklepow WooCommerce, SEO, grafike i marketing w social media. Firma dziala z Kotliny Klodzkiej (Dolny Slask, Polska) i chce byc widoczna lokalnie (Kotlina Klodzka), regionalnie (Dolny Slask) i krajowo (Polska) w wyszukiwarkach i AI.

Zwroc TYLKO JSON bez tekstu przed/po:
{"score": liczba 0-100 jak dobrze ta firma prezentuje sie jako lokalny ekspert w AI/wyszukiwarkach,
 "strengths": ["max 3 krotkie punkty co dziala dobrze"],
 "improvements": ["max 3 krotkie konkretne rekomendacje co poprawic pod lokalne AI/SEO (Kotlina Klodzka, Dolny Slask)"]}"""

BRAND = "directwebs"

def now():
    return datetime.now().strftime("%H:%M:%S")

def sanitize(text):
    """Usuwa klucze API z tekstu zanim trafi do logu."""
    if OPENAI_KEY:
        text = text.replace(OPENAI_KEY, "***")
    if GEMINI_KEY:
        text = text.replace(GEMINI_KEY, "***")
    return text

def analyze_site_gemini():
    """Prosi Gemini o ocene jak DirectWebs prezentuje sie jako ekspert (na podstawie wiedzy/web)."""
    if not GEMINI_KEY:
        return None
    try:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
            json={
                "contents": [{"parts": [{"text": ANALYSIS_PROMPT}]}],
                "tools": [{"google_search": {}}],
            },
            timeout=30,
        )
        res.raise_for_status()
        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {"error": sanitize(str(e))}

def check_openai(question):
    if not OPENAI_KEY:
        return None
    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 500,
            },
            timeout=30,
        )
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"]
        mentioned = BRAND in text.lower()
        return {"mentioned": mentioned, "response_excerpt": text[:400]}
    except Exception as e:
        return {"error": sanitize(str(e))}

def check_gemini(question):
    if not GEMINI_KEY:
        return None
    try:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": question}]}]},
            timeout=30,
        )
        res.raise_for_status()
        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        mentioned = BRAND in text.lower()
        return {"mentioned": mentioned, "response_excerpt": text[:400]}
    except Exception as e:
        return {"error": sanitize(str(e))}

def main():
    print(f"\n{'='*50}")
    print(f"DirectWebs AI Visibility Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    results = {"date": datetime.now().strftime("%Y-%m-%d"), "checks": []}

    for item in QUESTIONS:
        q, tier = item["q"], item["tier"]
        print(f"[{now()}] [{tier}] Pytanie: {q}")
        entry = {"question": q, "tier": tier}

        gpt = check_openai(q)
        if gpt:
            entry["chatgpt"] = gpt
            status = "✅ wspomniano" if gpt.get("mentioned") else ("❌ brak" if "error" not in gpt else f"err: {gpt['error']}")
            print(f"  ChatGPT: {status}")

        gem = check_gemini(q)
        if gem:
            entry["gemini"] = gem
            status = "✅ wspomniano" if gem.get("mentioned") else ("❌ brak" if "error" not in gem else f"err: {gem['error']}")
            print(f"  Gemini:  {status}")

        results["checks"].append(entry)

    print(f"[{now()}] Analiza strony directwebs.pl...")
    site_analysis = analyze_site_gemini()
    results["site_analysis"] = site_analysis
    if site_analysis and "error" not in site_analysis:
        print(f"  Score: {site_analysis.get('score')}/100")
        for s in site_analysis.get("strengths", []):
            print(f"  + {s}")
        for i in site_analysis.get("improvements", []):
            print(f"  - {i}")
    elif site_analysis:
        print(f"  Blad analizy: {site_analysis.get('error')}")

    # Wczytaj historie i dopisz
    history = []
    if os.path.exists(LOG_FILE):
        try:
            history = json.load(open(LOG_FILE))
        except Exception:
            history = []

    history.append(results)
    history = history[-52:]  # max 52 tygodnie (1 rok)

    json.dump(history, open(LOG_FILE, "w"), ensure_ascii=False, indent=2)

    total_checks = len(QUESTIONS) * (1 if OPENAI_KEY else 0) + len(QUESTIONS) * (1 if GEMINI_KEY else 0)
    mentions = sum(
        1 for c in results["checks"]
        for k in ("chatgpt", "gemini")
        if k in c and c[k].get("mentioned")
    )

    print(f"\n{'='*50}")
    print(f"SUKCES! Wzmianki DirectWebs: {mentions}/{total_checks}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
