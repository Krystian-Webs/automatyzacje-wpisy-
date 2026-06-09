# DirectWebs — Auto SEO Blog Posts 🤖

Automatyczne generowanie i publikowanie wpisów SEO na WordPress przez Claude AI.
Działa **wtorek + czwartek + sobota o 9:00** — bez żadnej akcji z Twojej strony.

---

## Jak uruchomić (jednorazowe ustawienie ~5 minut)

### Krok 1 — Wgraj kod na GitHub

1. Zaloguj się na [github.com](https://github.com)
2. Kliknij **+** → **New repository**
3. Nazwa: `dw-seo-autoposter`
4. Ustaw jako **Private**
5. Kliknij **Create repository**
6. Wgraj wszystkie pliki z tego folderu

### Krok 2 — Dodaj sekrety (klucze dostępu)

W repozytorium → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Dodaj po kolei:

| Nazwa | Wartość |
|-------|---------|
| `WP_URL` | `https://directwebs.pl` |
| `WP_USER` | Twój login WordPress (np. `admin`) |
| `WP_PASSWORD` | Application Password z WordPress |
| `CLAUDE_KEY` | Klucz z console.anthropic.com |
| `WP_CATEGORY_ID` | ID kategorii bloga (np. `1`) |
| `POST_STATUS` | `publish` lub `draft` |

**Jak wygenerować WordPress Application Password:**
1. Zaloguj się do WP Admin
2. Użytkownicy → Twój profil → przewiń na dół
3. Sekcja "Application Passwords" → nazwa: "GitHub Actions" → Dodaj
4. Skopiuj wygenerowane hasło

### Krok 3 — Gotowe!

Od teraz system sam:
- Wtorek o 9:00 → generuje i publikuje wpis
- Czwartek o 9:00 → generuje i publikuje wpis
- Sobota o 9:00 → generuje i publikuje wpis

---

## Jak dodać własne słowa kluczowe

Edytuj plik `keywords/list.json` i dodaj nowe grupy:

```json
{
  "focus": "główna fraza kluczowa",
  "related": ["fraza powiązana 1", "fraza powiązana 2"],
  "type": "poradnik",
  "length": 1800
}
```

Dostępne typy: `poradnik`, `porownanie`, `lista`, `faq`, `lokalne`

---

## Ręczne uruchomienie

Możesz odpuścić wpis ręcznie w dowolnym momencie:
**Actions** → **Auto SEO Blog Post** → **Run workflow**

---

## Monitorowanie

Po każdym uruchomieniu sprawdź:
**Actions** → kliknij ostatni run → zobaczysz logi z tytułem wpisu i linkiem
