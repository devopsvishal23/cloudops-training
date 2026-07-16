# 1 · Setup & Daily Workflow

> **Goal:** by the end of this file you should be able to connect a local project to GitHub from scratch, push it for the first time, and repeat the daily add → commit → push cycle without hesitating.

[Index](./README.md) · Next: [Troubleshooting →](./02-troubleshooting.md)

---

## 🧰 One-Time Setup (per Mac)

You're on Mac, VS Code is your editor. Do this **once** — Git remembers it globally after.

```bash
# Check if git is already configured
git config --global user.name
git config --global user.email
```

If those return nothing, set them:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

> 💡 This name/email is stamped into every commit you make on this machine — it's how GitHub attributes commits to you.

---

## 🌐 Create the GitHub Repo First

1. Go to **github.com → New repository**
2. Name it (e.g. `cloudops-upskill`)
3. **Do not** initialise with a README — you already have local files, and an auto-created README would conflict with your first push
4. Click **Create**

GitHub will show you a URL like:

```text
https://github.com/yourusername/cloudops-upskill.git
```

Keep that URL — you need it in the next step.

---

## 🔗 Connect Your Local Folder to GitHub

```bash
cd ~/cloudops-upskill

# Initialise git if not done already
git init

# Point it at your GitHub repo
git remote add origin https://github.com/yourusername/cloudops-upskill.git

# Verify the remote is set
git remote -v
```

`origin` is just a **local nickname** for that GitHub URL — you'll refer to it by name in every push/pull from here on.

---

## 🚀 Your First Push (do this once)

```bash
git add .
git commit -m "week4: final cleanup and readme"
git push -u origin main
```

`-u origin main` sets the **upstream** — the link between your local `main` branch and GitHub's `main` branch. After this first time, every future push is just:

```bash
git push
```

### What each command actually does

| Command | What happens | Goes to GitHub? |
|---|---|---|
| `git add .` | Stages everything in the current directory — tells Git "track these changes" | ❌ No — local only |
| `git commit -m "…"` | Saves a snapshot locally with a message | ❌ No — local only |
| `git push` | Sends your local commits to GitHub | ✅ Yes — this is the network step |

> ⚠️ **Common mistake:** people think `git commit` uploads to GitHub. It doesn't. `push` is the only step that touches the network.

```text
   Working Directory        Staging Area           Local Repo              GitHub
   (your edited files)      (git add)               (git commit)          (git push)

   ┌───────────────┐      ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
   │  file.py (M)  │ ───► │  file.py       │ ───► │  snapshot #1  │ ───► │   origin/main │
   └───────────────┘      │  staged        │      │  (commit)     │      └───────────────┘
                          └───────────────┘      └───────────────┘
                                                        local only        now on GitHub
```

---

## 🔁 Day-to-Day Workflow Going Forward

Every time you finish a lab:

```bash
git status                        # see what changed
git add .                         # stage everything
git commit -m "week5: brief description"
git push                          # send to GitHub
```

```text
 ┌──────────┐   edit files   ┌──────────────┐   git add .   ┌──────────┐   git commit   ┌───────────┐   git push   ┌────────┐
 │  Start   │ ─────────────► │ git status   │ ────────────► │ Staged   │ ─────────────► │ Committed │ ───────────► │ GitHub │
 │  a lab   │                │ (check diff) │               │          │                │ (local)   │              │        │
 └──────────┘                └──────────────┘               └──────────┘                └───────────┘              └────────┘
```

> 🧠 **Habit to build:** always run `git status` before `git add .` — it's a free preview of exactly what you're about to stage, and it catches "I'm in the wrong folder" mistakes before they happen (see [Troubleshooting →](./02-troubleshooting.md)).

---

Next: [**Troubleshooting →**](./02-troubleshooting.md)
