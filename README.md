# Promo Scraper Bot (MVP)

Aplicatie Python pentru colectarea promotiilor alimentare din magazine online, salvare in SQLite si postare automata in Telegram channel.

## Ce face MVP-ul

- colecteaza promotii din Kaufland Moldova (prima sursa)
- colecteaza promotii din Kaufland Moldova, Linella si Metro (zakaz.md)
- arhitectura extensibila pentru mai multe surse
- normalizeaza datele intr-un format unic
- salveaza doar produse noi (fara duplicate)
- detecteaza produse nepostate si le trimite in Telegram
- marcheaza produsele trimise cu `posted_to_telegram = 1`

## Structura proiect

```text
promo-scraper-bot/
├── main.py
├── .env.example
├── requirements.txt
├── README.md
├── core/
│   ├── config.py
│   ├── database.py
│   ├── normalizer.py
│   └── telegram_bot.py
├── scrapers/
│   ├── base_scraper.py
│   ├── kaufland_scraper.py
│   └── scraper_registry.py
└── data/
    └── promotions.db
```

## Instalare

```powershell
cd d:\Scrapper\promo-scraper-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Daca vei folosi Playwright (cand pagina e randata prin JavaScript):

```powershell
playwright install chromium
```

## Configurare .env

1. Copiaza fisierul de exemplu:

```powershell
copy .env.example .env
```

2. Completeaza in `.env`:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `MIN_DISCOUNT_PERCENTAGE=30` (se posteaza doar produse cu reducere mai mare decat pragul)
- `TELEGRAM_SEND_DELAY_SECONDS` (optional, anti-rate-limit)
- `TELEGRAM_MAX_POSTS_PER_RUN` (optional, limiteaza cate grupuri trimite per rulare)
- `TELEGRAM_ITEMS_PER_GROUP=4` (cate produse intra intr-un mesaj batch)

3. Optional: ajusteaza selectorii Kaufland din `.env` daca se schimba structura HTML.
4. Optional: ajusteaza selectorii Linella din `.env` daca se schimba structura HTML.
5. Optional: ajusteaza parametrii Metro (`METRO_MAX_PAGES`, `METRO_PAGE_WAIT_SECONDS`) in functie de viteza conexiunii.
6. Optional: foloseste `METRO_HEADLESS=1` pe server/CI (fara desktop); local poti lasa `METRO_HEADLESS=0`.

## Cum creezi botul Telegram

1. In Telegram, deschide **@BotFather**.
2. Ruleaza comanda `/newbot`.
3. Alege nume + username pentru bot.
4. Copiaza token-ul primit si pune-l in `.env` la `TELEGRAM_BOT_TOKEN`.
5. Creeaza un channel Telegram (public sau privat).
6. Adauga botul ca administrator in channel (cu drept de postare).
7. Seteaza `TELEGRAM_CHANNEL_ID`:
- pentru channel public: `@nume_channel`
- pentru channel privat: chat id numeric (de ex. `-1001234567890`)

## Rulare aplicatie

```powershell
cd d:\Scrapper\promo-scraper-bot
.\.venv\Scripts\Activate.ps1
python main.py
```

Fluxul de rulare:
1. ruleaza toate sursele din registry
2. normalizeaza + salveaza produse noi in SQLite
3. ia produsele cu `posted_to_telegram = 0`
4. posteaza in Telegram doar daca exista `name` si `new_price`
5. trimite batch-uri pe sursa (implicit 4 produse/grup); daca exista imagini, trimite album (`sendMediaGroup`)
6. daca albumul cu imagini esueaza, revine automat la mesaj text batch
7. marcheaza produsele trimise ca postate

## Baza de date

Tabelul `products` este creat automat la prima rulare.

`unique_key` se genereaza din:
- `source_code`
- `name`
- `new_price`

Daca produsul exista deja (aceeasi cheie), nu se insereaza din nou.

## Extindere cu alte magazine

1. Creeaza un nou scraper in `scrapers/`, ex: `lidl_scraper.py`.
2. Extinde `BaseScraper` si implementeaza `scrape()`.
3. Returneaza datele in acelasi format standard.
4. Inregistreaza noul scraper in `scrapers/scraper_registry.py`.
5. Adauga URL/selectori noi in `.env` pentru mentenanta usoara.

Model de format returnat de orice scraper:

```python
{
    "source_code": "kaufland",
    "source_name": "Kaufland",
    "name": "...",
    "new_price": "...",
    "old_price": "...",
    "discount": "...",
    "category": "...",
    "image_url": "...",
    "product_url": "...",
    "valid_from": "...",
    "valid_to": "..."
}
```

## Note utile

- Daca nu se gasesc produse, aplicatia afiseaza mesaj clar in consola.
- Scraperul Kaufland este gandit sa fie usor de ajustat prin selectori in `.env`.
- Scraperul Metro foloseste Chromium prin DrissionPage pentru a trece de protectia anti-bot si a citi paginile de promotii.
- Workflow-ul GitHub Actions restaureaza/salveaza `data/promotions.db` in cache, astfel deduplicarea si statusul `posted_to_telegram` se pastreaza intre rulari.
- Pentru rulare periodica, poti folosi Task Scheduler (Windows) sau cron (Linux).
