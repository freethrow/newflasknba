# Deploying to PythonAnywhere

## Prerequisites

- PythonAnywhere account (free tier works for SQLite apps)
- Your code pushed to GitHub (or uploaded via the PA Files tab)
- A [Resend](https://resend.com) account with an API key for password reset emails

---

## 1. Upload the code

**Option A — clone from GitHub (recommended):**

Open a PythonAnywhere Bash console and run:

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/newflasknba.git
cd newflasknba
```

**Option B — upload a zip** via the Files tab, then unzip:

```bash
cd ~
unzip newflasknba.zip
cd newflasknba
```

---

## 2. Create a virtualenv and install dependencies

```bash
cd ~/newflasknba
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> PythonAnywhere free tier has Python 3.12 available. Select it explicitly when
> creating the web app in the next step.

---

## 3. Create the web app

1. Go to the **Web** tab → **Add a new web app**
2. Choose **Manual configuration** (not a framework wizard)
3. Select **Python 3.12**

Then set the following fields in the Web tab:

| Field | Value |
|---|---|
| Source code | `/home/<username>/newflasknba` |
| Working directory | `/home/<username>/newflasknba` |
| WSGI configuration file | `/home/<username>/newflasknba/wsgi.py` |
| Virtualenv | `/home/<username>/newflasknba/venv` |

---

## 4. Set environment variables

In the **Web** tab, scroll down to **Environment variables** and add:

```
DATABASE_URL=sqlite:////home/<username>/newflasknba/instance/nba.sqlite
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
CURRENT_SEASON=2026
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
MAIL_FROM=nba@yourdomain.com
```

Generate your `SECRET_KEY` in the Bash console:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. Initialise or migrate the database

**Fresh install (no existing data):**

```bash
cd ~/newflasknba
source venv/bin/activate
export DATABASE_URL="sqlite:////home/<username>/newflasknba/instance/nba.sqlite"
export SECRET_KEY="same-key-as-above"
export CURRENT_SEASON="2026"

flask --app src.nba_predictions db upgrade
```

**Migrating an existing `nba.sqlite` from the old app:**

```bash
# Copy your existing database into the instance folder
cp /path/to/old/nba.sqlite ~/newflasknba/instance/nba.sqlite

# Run migrations against it (Alembic will only apply missing changes)
flask --app src.nba_predictions db upgrade
```

**Seed an admin account (first-time setup only):**

```bash
flask --app src.nba_predictions seed
```

This creates user `admin` with password `admin`. **Change the password immediately** after first login via the admin dashboard.

---

## 6. Reload the web app

Click the green **Reload** button in the Web tab. Visit your `<username>.pythonanywhere.com` URL to confirm it works.

---

## 7. Rebuild Tailwind CSS (if templates changed)

The compiled `output.css` is committed to the repo, so this is only needed after template edits. On your **local machine**:

```bash
./tailwindcss -i src/nba_predictions/static/css/input.css \
              -o src/nba_predictions/static/css/output.css \
              --minify
git add src/nba_predictions/static/css/output.css
git commit -m "rebuild tailwind"
git push
```

Then on PythonAnywhere:

```bash
cd ~/newflasknba && git pull
```

And reload the web app.

---

## 8. Promote a user to admin

```bash
cd ~/newflasknba
source venv/bin/activate
export DATABASE_URL="sqlite:////home/<username>/newflasknba/instance/nba.sqlite"
export SECRET_KEY="..."

flask --app src.nba_predictions user promote <username>
```

---

## 9. Database backups

### Manual backup

```bash
sqlite3 ~/newflasknba/instance/nba.sqlite \
  ".backup $HOME/backups/nba-$(date +%F).sqlite"
```

Create the backups folder first if it doesn't exist:

```bash
mkdir -p ~/backups
```

### Scheduled daily backup (PythonAnywhere Tasks tab)

1. Go to the **Tasks** tab → **Add a new scheduled task**
2. Set frequency: **Daily**
3. Command:

```bash
mkdir -p ~/backups && sqlite3 ~/newflasknba/instance/nba.sqlite ".backup $HOME/backups/nba-$(date +%F).sqlite" && find ~/backups -name "nba-*.sqlite" -mtime +30 -delete
```

This backs up daily and automatically removes backups older than 30 days.

### Restore from backup

```bash
# Stop traffic first (reload → stop the web app), then:
cp ~/backups/nba-2026-04-09.sqlite ~/newflasknba/instance/nba.sqlite
# Reload the web app to bring it back up
```

---

## 10. Updating the app

```bash
cd ~/newflasknba
git pull
source venv/bin/activate
pip install -r requirements.txt          # pick up any new packages
flask --app src.nba_predictions db upgrade  # apply any new migrations
```

Then reload the web app in the Web tab.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| 500 error on startup | Web tab → **Error log** link |
| `ModuleNotFoundError` | Virtualenv path correct? `pip list` to verify packages |
| Static files 404 | PA auto-serves `/static/` — confirm the path in Web tab static files section |
| DB changes not persisting | `DATABASE_URL` env var set correctly? Four slashes for absolute path |
| Emails not sending | `RESEND_API_KEY` set? Resend sandbox only delivers to verified addresses |
