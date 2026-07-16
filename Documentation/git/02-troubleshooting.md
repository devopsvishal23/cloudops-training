# 2 · Troubleshooting — SSH Keys & Common Mistakes

> **Goal:** recognise the two most common early Git/GitHub errors on a Mac with multiple accounts, and know the fix without re-Googling it every time.

[← Setup & Workflow](./01-setup-and-workflow.md) · [Index](./README.md)

---

## 🔑 Issue 1 — Wrong SSH Key Being Used

**Symptom:** Git authenticates as the wrong GitHub account (e.g. `nixacetech`) when the repo belongs to a different one (e.g. `devopsvishal23`).

**Cause:** you have multiple GitHub accounts on this Mac, and SSH is picking the wrong key by default because both accounts resolve to the same host, `github.com`.

```text
        git push
           │
           ▼
   ┌───────────────┐        SSH tries default key         ┌──────────────┐
   │  Your Mac     │ ─────────────────────────────────►   │  github.com  │
   │  (git push)   │        (~/.ssh/id_rsa or similar)     │              │
   └───────────────┘                                       └──────┬───────┘
                                                                    │
                                             authenticates as the account
                                             that key belongs to — maybe
                                             NOT the one you intended
                                                                    ▼
                                                          ❌ wrong account / denied
```

### Step 1 — Check what keys you have

```bash
ls ~/.ssh/
```

You'll likely see multiple keys — something like `id_rsa`, `id_ed25519`, or named keys like `nixacetech` and `devopsvishal23`.

### Step 2 — Check which account each key belongs to

```bash
ssh -T git@github.com
# Hi nixacetech!   ← wrong account currently active
```

### Step 3 — Fix: tell SSH which key to use for which account

Open (or create) the SSH config file:

```bash
code ~/.ssh/config
```

Add a **separate host alias per account**:

```text
# Personal / devopsvishal23
Host github-devops
  HostName github.com
  User git
  IdentityFile ~/.ssh/<your_devopsvishal23_key>

# Other account / nixacetech
Host github-nixace
  HostName github.com
  User git
  IdentityFile ~/.ssh/<your_nixacetech_key>
```

> 💡 Replace `<your_devopsvishal23_key>` with the actual filename you saw in `ls ~/.ssh/`.

### Step 4 — Point the remote at the alias, not `github.com`

```bash
git remote set-url origin git@github-devops:devopsvishal23/cloudops-training.git
```

### Step 5 — Verify it works

```bash
ssh -T git@github-devops
# Hi devopsvishal23!   ← correct now

git push -u origin main
```

| Host alias | Maps to key | Use for repos owned by |
|---|---|---|
| `github-devops` | `~/.ssh/<devopsvishal23_key>` | `devopsvishal23` |
| `github-nixace` | `~/.ssh/<nixacetech_key>` | `nixacetech` |

> 🧠 **Why this works:** SSH host aliases let you have as many "identities" for `github.com` as you have keys — each alias is really just "use this key when connecting to github.com," addressed by a name you invent. The remote URL's `git@github-devops:...` looks like a hostname but is actually just a lookup into `~/.ssh/config`.

---

## 📁 Issue 2 — "Nothing to Commit"

**Symptom:** `git commit` (or `git add .`) reports nothing to do, even though you know you changed files.

**Cause:** you were inside a **subdirectory** (e.g. `app/`), not the repo root. `git add .` from a subdirectory only stages files in that folder and below — it can't see changes elsewhere in the repo.

```bash
cd ~/cloudops-upskill    # go to repo root
git status               # now shows all week4 files
git add .
git commit -m "week4: final cleanup and readme"
git push -u origin main
```

> 💡 **Quick check:** if `git status` ever looks emptier than you expect, run `git rev-parse --show-toplevel` to confirm where the repo root actually is, then `cd` there.

---

## 🧯 Quick Reference

| Symptom | Root Cause | Fix |
|---|---|---|
| Pushes as the wrong GitHub account | SSH using the wrong default key | Add host aliases in `~/.ssh/config`, point the remote at the alias |
| `nothing to commit` when you know files changed | You're inside a subdirectory, not the repo root | `cd` to repo root, re-run `git status` |

> If you're not sure which key file belongs to which account, run `ls ~/.ssh/` and match it against `ssh -T git@github.com` output before editing the config.

---

[← Back to Setup & Workflow](./01-setup-and-workflow.md) · [Index](./README.md)
