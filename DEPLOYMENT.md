# GitHub Actions Deployment Guide

Acest document explică cum să setezi GitHub Actions pentru a rula scraperul automat.

## 1. Pregatire Git & GitHub

### Initialize repository local
```powershell
cd d:\Scrapper\promo-scraper-bot
git init
git add .
git commit -m "Initial commit: promo scraper with Metro, Kaufland, Linella"
```

### Creeaza repository pe GitHub
1. Mergi pe [github.com/new](https://github.com/new)
2. Alege nume (ex: `promo-scraper-bot`)
3. Selecteaza **Private** (recommended, pentru Telegram tokens)
4. Nu bifati "Initialize README" (ai deja commit local)
5. Click "Create repository"

### Conecteaza local la GitHub
```powershell
git remote add origin https://github.com/YOUR_USERNAME/promo-scraper-bot.git
git branch -M main
git push -u origin main
```

## 2. Configureaza Secrets in GitHub

Secrets sunt variabile protejate, inaccesibile in logs publici.

1. Mergi la repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** si adauga:

| Secret Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token-ul de la @BotFather |
| `TELEGRAM_CHANNEL_ID` | ID-ul canalului (ex: `@channel_name` sau `-100...`) |

## 3. Configureaza Variables in GitHub (Optional)

Variables sunt pentru setari neconfidențiale.

1. In aceeasi pagina **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository variable** si adauga:

| Variable Name | Default | Descriere |
|---|---|---|
| `MIN_DISCOUNT_PERCENTAGE` | `30` | Numai produse cu reducere > aceasta % |
| `TELEGRAM_SEND_DELAY_SECONDS` | `1.1` | Delay intre mesaje (anti-rate-limit) |
| `TELEGRAM_MAX_POSTS_PER_RUN` | `20` | Max grupuri trimise per rulare |

## 4. Workflow deja configurat

Fisierul `.github/workflows/scraper.yml` are:

- **Schedule**: Ruleaza zilnic la 08:00 UTC (editabil in `cron` field)
- **Manual trigger**: Poti apasa "Run workflow" manual din GitHub UI
- **Playwright**: Se instaleaza Chromium automat pentru Metro scraper
- **Artifacts**: DB-ul se salveaza ca artifact (7 zile)
- **Timeout**: 60 minute (suficient pentru ~1689 produse Metro)

## 5. Verifica workflow status

1. Mergi la repo → **Actions**
2. Selecteaza cel mai recent workflow run
3. Vezi logs detaliate si eventuale erori

## 6. Editare schedule (cron)

In `.github/workflows/scraper.yml`, linia:
```yaml
- cron: '0 8 * * *'
```

Format cron: `minute hour day month weekday`

Exemple:
- `0 8 * * *` → zilnic la 08:00
- `0 8 * * 1` → luni la 08:00
- `0 6,14 * * *` → 06:00 si 14:00 zilnic
- `*/30 * * * *` → la fiecare 30 minute

## 7. Dezactivare workflow

Daca ai nevoie sa opresti temporar:
1. Repo → **Actions** → selecteaza workflow
2. Click **...** → **Disable workflow**

## 8. Notificari pe esec

Poti adauga notificari via:
- GitHub email (default la esec)
- Slack integration
- Alt webhook

(Ne gandim daca adaugam Telegram notification direct cand esueaza jobul)

## Troubleshooting

### Workflow nu se executa la schedule
- GitHub Actions necesita fie un push recent, fie activitate in 60 zile
- Daca e inactiv prea mult, schedula se pauzează automat
- Solutie: Apasa manual "Run workflow" sa reactivezi

### Error "DrissionPage not found" in runner
- Deja sunt pip dependencies in `requirements.txt`
- Runner instaleaza playwright si chromium automat
- Daca e error persistent, verifica ca `requirements.txt` e up-to-date

### Telegram token expusă accidental
1. Regenereaza imediat token-ul la @BotFather
2. Updateaza SECRET in GitHub
3. Vechi token e invalid

### Database grow prea mult
- Currently, schema-ul e simple si nu are paginare pe delete
- Poti eventual adauga cleanup periodic daca baza creste enorm (ex. delete dupa 30 zile)
- Artifacts se șterg automat după 7 zile (configurable)

---

Cu workflow-ul asta, scraperul o sa:
1. Se ruleze automat zilnic la 08:00 UTC
2. Poseze promotiinew in Telegram
3. Salveze versiune DB ca artifact (backup)
4. Notifice pe email daca ceva merge gresit
