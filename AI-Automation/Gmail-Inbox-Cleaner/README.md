# Gmail Inbox Cleaner — AI-Powered Email Manager

> Built with Python + Gmail API + Claude (Anthropic) as POC #1 of an AI Automation series.

---

## TABLE OF CONTENTS

1. [What This Tool Does](#what-this-tool-does)
2. [How To Use It](#how-to-use-it)
3. [Setup & Configuration Guide](#setup--configuration-guide)
4. [Project File Structure](#project-file-structure)
5. [Cost & Quota Reference](#cost--quota-reference)
6. [Safety Guardrails](#safety-guardrails)
7. [Troubleshooting](#troubleshooting)

---

## What This Tool Does

Gmail Inbox Cleaner is a terminal-based AI automation tool that:

- Scans your **entire Gmail inbox** for unread emails
- Groups them by **sender** in a ranked bifurcation table (highest volume at top)
- Lets you **bulk delete or mark as read** by sender in one keypress
- Uses **Claude AI** to automatically categorize low-volume senders (1–9 emails) into groups like PROMOTIONAL, NEWSLETTER, RECRUITER, TRANSACTIONAL, etc.
- Allows **bulk action by category** — delete all newsletters in one confirmation
- Uses a **local cache** so rescans are instant without hitting the Gmail API again
- Runs in **DRY RUN mode by default** — nothing is touched until you go live

---

## How To Use It

### Starting the Tool

```bash
# Step 1: Navigate to the project folder
cd ~/gmail-cleaner

# Step 2: Activate the Python virtual environment
source venv/bin/activate

# Step 3: Run the tool
python main.py
```

---

### Main Menu Options

Once the tool loads you will see the bifurcation table followed by this menu:

```
# = act on sender | [A] Analyze single-senders with Claude | [R] Redisplay | [F] Fresh fetch | [Q] Quit
```

| Key | What It Does |
|-----|-------------|
| `1–999` | Select a sender by its number in the table |
| `A` | Run Claude AI analysis on all senders with 1–9 emails |
| `R` | Redisplay the current table instantly (no API call) |
| `F` | Force a fresh fetch from Gmail and rebuild the cache |
| `Q` | Quit the tool |

---

### Reading the Bifurcation Table

```
========================================================================
  Data fetched: 2026-06-29 01:12:22  (4 min ago)
  #     SENDER EMAIL                               NAME                 EMAILS
========================================================================
  1     newsletters-noreply@linkedin.com           Cyber Press             439
  2     news@newsalertth.thehindu.com              The Hindu               102
  3     netbanking@svcbank.com                     NetBanking               99
========================================================================
  Total senders: 338  |  Total unread emails: 2708
========================================================================
```

- `#` — Sender number. Type this and press Enter to act on it.
- `SENDER EMAIL` — The exact from-address of the sender.
- `NAME` — The display name the sender uses.
- `EMAILS` — How many unread emails from this sender are in your inbox.
- Table is sorted by email count — highest volume senders appear first.

---

### Acting on a Single Sender

Type the sender number and press Enter:

```
Your choice: 1

  Selected: newsletters-noreply@linkedin.com
  Unread emails from this sender: 439

  CHOOSE AN ACTION:
  [1] Preview - show subject lines of all emails from this sender
  [2] Delete All - move all emails from this sender to Trash
  [3] Mark All as Read - keep them but mark as read
  [4] Back - go back to sender table
```

| Action | What Happens |
|--------|-------------|
| `1` Preview | Lists all subject lines so you can review before acting |
| `2` Delete All | Moves all emails from this sender to Gmail Trash (recoverable for 30 days) |
| `3` Mark All as Read | Removes unread status but keeps emails in inbox |
| `4` Back | Returns to the main table without doing anything |

For Delete and Mark as Read you will always be asked to confirm:

```
Confirm: trash ALL 439 emails from newsletters-noreply@linkedin.com? (yes/no):
```

Type `yes` to proceed or anything else to cancel.

---

### Using Claude AI Analysis — The [A] Option

Press `A` at the main menu to activate AI-powered bulk analysis.

**What it does:**
- Filters all senders who have sent you **9 or fewer emails**
- Sends sender name, email address, subject line, and a short preview to Claude
- Claude categorizes each into one of 8 categories
- Displays a grouped summary so you can bulk action by category

**Example output:**

```
========================================================================
  SINGLE-SENDER ANALYSIS — Powered by Claude
========================================================================

  Found 287 senders with 9 or fewer emails.
  Estimated Claude cost: $0.000287 (negligible)
  Estimated time: ~15 API call(s)

  Proceed with Claude analysis? (yes/no): yes

  Sending 287 emails to Claude in batches of 20...
  Classifying batch 1/15 (20 emails)... done.
  ...

========================================================================
  ANALYSIS RESULTS — Grouped by Category
========================================================================
  [1] 🛍️  PROMOTIONAL       47 emails   Recommended: DELETE
  [2] 📰  NEWSLETTER         38 emails   Recommended: DELETE
  [3] 💼  RECRUITER          29 emails   Recommended: DELETE
  [4] 📱  SOCIAL             22 emails   Recommended: DELETE
  [5] 🏦  TRANSACTIONAL      18 emails   Recommended: KEEP
  [6] 🔒  SECURITY           12 emails   Recommended: KEEP
  [7] 👤  PERSONAL            8 emails   Recommended: KEEP
  [8] ❓  UNKNOWN             4 emails   Recommended: REVIEW
========================================================================
```

**Category meanings:**

| Category | Emoji | Description | Default Recommendation |
|----------|-------|-------------|----------------------|
| PROMOTIONAL | 🛍️ | Sales, offers, discounts, deals | DELETE |
| NEWSLETTER | 📰 | Blogs, digests, thought leadership | DELETE |
| RECRUITER | 💼 | Job offers, hiring outreach | DELETE |
| SOCIAL | 📱 | LinkedIn, Facebook, Instagram, Reddit | DELETE |
| TRANSACTIONAL | 🏦 | Receipts, bank alerts, invoices, statements | KEEP |
| SECURITY | 🔒 | Login alerts, 2FA, account verification | KEEP |
| PERSONAL | 👤 | Real human wrote this directly to you | KEEP |
| UNKNOWN | ❓ | Claude was not confident enough to categorize | REVIEW |

**Acting on a category:**

Type the category number, review the sender list shown, then choose:

```
  [1] Delete All — move all to Trash
  [2] Mark All as Read — keep but mark read
  [3] Skip — do nothing, go back
```

One confirmation deletes all emails across all senders in that category at once.

---

### Cache Behaviour

| Situation | What Happens |
|-----------|-------------|
| First run ever | Fetches from Gmail, saves cache locally |
| Run within 30 minutes of last fetch | Loads from cache instantly |
| Run after 30 minutes | Auto-fetches fresh data from Gmail |
| Press `R` | Reprints current table — zero API calls |
| Press `F` | Forces fresh Gmail fetch regardless of cache age |
| After any live delete or mark-as-read | Cache updates automatically |

Cache is stored in `email_cache.json` in the project folder.

---

### Going Live — Disabling Dry Run

By default the tool runs in **DRY RUN mode** — it shows what would happen but touches nothing. To enable real actions open `main.py` and change line 8:

```python
# Find this:
DRY_RUN = True

# Change to:
DRY_RUN = False
```

Save and run again. All delete and mark-as-read actions will now execute against your real Gmail inbox.

> ⚠️ Emails moved to Trash are NOT permanently deleted.
> Gmail keeps Trash for 30 days. You can recover any email by going to
> Gmail → Trash → selecting the email → Move to Inbox.

---

## Setup & Configuration Guide

### Prerequisites

| Requirement | Version | How to Check |
|-------------|---------|-------------|
| macOS | Any recent version | — |
| Python 3 | 3.9 or higher | `python3 --version` |
| Gmail Account | Personal or Workspace | — |
| Anthropic Account | Free tier works | console.anthropic.com |

---

### STEP 1 — Create Project Folder and Virtual Environment

```bash
mkdir ~/gmail-cleaner
cd ~/gmail-cleaner
python3 -m venv venv
source venv/bin/activate
```

You will see `(venv)` at the start of your terminal prompt when active.

**Verify:**
```
(venv) yourusername@MacBook gmail-cleaner %
```

---

### STEP 2 — Create Google Cloud Project

1. Go to: `https://console.cloud.google.com/projectcreate`
2. Sign in with the Gmail account you want to clean
3. In the **Project name** field type: `gmail-cleaner-poc`
4. Click **CREATE** and wait ~15 seconds
5. Click **SELECT PROJECT** from the notification that appears

**Verify:** The dropdown at the top of the page shows `gmail-cleaner-poc`

---

### STEP 3 — Enable the Gmail API

1. Go to: `https://console.cloud.google.com/apis/library/gmail.googleapis.com`
2. Confirm the project dropdown shows `gmail-cleaner-poc`
3. Click the blue **ENABLE** button

**Verify:** The ENABLE button is replaced by a **MANAGE** button

---

### STEP 4 — Configure OAuth Consent (Google Auth Platform)

Google uses a new UI called Google Auth Platform. Complete all three sub-steps:

#### 4A — Branding
1. Go to: `https://console.cloud.google.com/auth/overview`
2. Click **Branding** in the left sidebar
3. Fill in **App name:** `Gmail Cleaner POC`
4. Fill in **User support email:** your Gmail address
5. Fill in **Developer contact:** your Gmail address
6. Click **SAVE**

#### 4B — Audience
1. Click **Audience** in the left sidebar
2. Select **External**
3. Click **SAVE**
4. Under **Test users** click **+ ADD USERS**
5. Enter your Gmail address and click **ADD**

#### 4C — Data Access
1. Click **Data access** in the left sidebar
2. Click **ADD OR REMOVE SCOPES**
3. Search for: `gmail.modify`
4. Check the box next to `https://www.googleapis.com/auth/gmail.modify`
5. Click **UPDATE** then **SAVE**

---

### STEP 5 — Create OAuth Credentials

1. Go to: `https://console.cloud.google.com/apis/credentials`
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Under **Application type** select **Desktop app**
4. Name it: `gmail-cleaner-desktop`
5. Click **CREATE**
6. Click **DOWNLOAD JSON** in the popup
7. Move and rename the downloaded file:

```bash
mv ~/Downloads/client_secret_*.json ~/gmail-cleaner/credentials.json
```

**Verify:**
```bash
cat ~/gmail-cleaner/credentials.json
# Must start with: {"installed":{"client_id":"
```

> ⚠️ SECURITY: credentials.json is a master key to your Google account API access.
> Never share it. Never upload it to GitHub.

---

### STEP 6 — Get Anthropic API Key

1. Go to: `https://console.anthropic.com/settings/keys`
2. Click **Create Key**, name it `gmail-cleaner-poc`, click **Create Key**
3. Copy the key immediately — it is shown only once
4. Create your `.env` file:

```bash
printf 'ANTHROPIC_API_KEY=sk-ant-api03-your-real-key-here\n' > ~/gmail-cleaner/.env
```

**Verify:**
```bash
cat ~/gmail-cleaner/.env
# Must show: ANTHROPIC_API_KEY=sk-ant-api03-...
```

> ⚠️ SECURITY: Set a $5/month spend cap at https://console.anthropic.com/settings/billing
> This prevents any accidental bill spikes.

---

### STEP 7 — Add Security Exclusions to Git

```bash
cd ~/gmail-cleaner
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
echo ".env" >> .gitignore
echo "email_cache.json" >> .gitignore
echo "venv/" >> .gitignore
```

> ⚠️ Never upload credentials.json, token.json, or .env to GitHub.

---

### STEP 8 — Install Python Dependencies

```bash
cd ~/gmail-cleaner
source venv/bin/activate
pip install google-auth-oauthlib google-api-python-client anthropic python-dotenv
```

**Verify:**
```bash
pip list | grep -E "google-auth-oauthlib|google-api-python-client|anthropic|python-dotenv"
```

Expected output:
```
anthropic                0.112.0
google-api-python-client 2.198.0
google-auth-oauthlib     1.4.0
python-dotenv            1.2.2
```

---

### STEP 9 — First Run and Gmail Authorization

```bash
cd ~/gmail-cleaner
source venv/bin/activate
python main.py
```

On first run a browser window opens automatically. Complete these steps:

1. Sign in with your Gmail account
2. If you see **"Google hasn't verified this app"** click **Advanced** then **Go to Gmail Cleaner POC (unsafe)** — this is your own app, it is safe
3. Click **Continue** on the permissions screen
4. The browser shows **"The authentication flow has completed"** — close the tab
5. Return to your terminal — the tool continues loading automatically

After first authorization a `token.json` file is saved. You will never need to authorize in the browser again.

---

## Project File Structure

```
~/gmail-cleaner/
├── venv/                  ← Python virtual environment (auto-generated)
├── classifier.py          ← Claude AI categorization logic
├── gmail_client.py        ← Gmail API connection, fetch, trash, mark-as-read
├── main.py                ← Main orchestrator and interactive UI
├── credentials.json       ← Google OAuth credentials ⚠️ never share
├── token.json             ← Auto-generated after first login ⚠️ never share
├── email_cache.json       ← Local email cache (auto-generated)
├── .env                   ← Anthropic API key ⚠️ never share
├── .gitignore             ← Protects all secret files from git
└── README.md              ← This file
```

---

## Cost & Quota Reference

### Gmail API

- **Cost: $0.00** — Gmail API is completely free for personal use
- Daily quota: 1,000,000 units per day
- A full scan of 4,500 emails uses ~15,000 units (1.5% of daily limit)
- You could run this tool 60 times a day and never hit the limit

### Anthropic API (Claude)

Model used: `claude-sonnet-4-6`

| Token Type | Price |
|------------|-------|
| Input | $3.00 per million tokens |
| Output | $15.00 per million tokens |

| Action | Approximate Cost |
|--------|-----------------|
| Classify 1 email | $0.000001 |
| Analyse 250 single-senders | $0.000250 |
| Full session (2700 emails) | $0.003 |
| Running daily for a month | $0.05 – $0.10 |

**Recommended:** Set a $5/month hard cap at `https://console.anthropic.com/settings/billing`

---

## Safety Guardrails

| Guardrail | How It Works |
|-----------|-------------|
| Dry Run Mode | `DRY_RUN = True` in main.py shows actions without executing them |
| Trash Not Delete | All deletions go to Gmail Trash — never permanent delete |
| 30-Day Recovery | Gmail keeps Trash for 30 days — full recovery window |
| Confirmation Required | Every bulk action asks `(yes/no)` before executing |
| Cache Protection | email_cache.json excluded from git via .gitignore |
| Credential Protection | credentials.json, token.json, .env all excluded from git |
| API Spend Cap | $5/month hard limit set in Anthropic console |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError: credentials.json` | Wrong working folder | Run `cd ~/gmail-cleaner && python main.py` |
| `TypeError: Could not resolve authentication method` | .env missing variable prefix | Run `cat .env` — must start with `ANTHROPIC_API_KEY=` |
| `Access blocked: app not verified` | Not added as test user | Go to Step 4B and add your email as a test user |
| `TimeoutError` during fetch | Sequential API calls too slow | Already fixed — tool uses batch fetching |
| `Token has been expired or revoked` | token.json is stale | Delete token.json and run again to re-authorize |
| Cache shows wrong counts after deletions | Cache not refreshed | Press `F` to force a fresh fetch from Gmail |

---

*Built as POC #1 of an AI Automation Series*
*Stack: Python 3 · Gmail API · Claude (Anthropic) · OAuth 2.0*
