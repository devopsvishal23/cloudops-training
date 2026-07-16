# 🌱 Git & GitHub — From First Principles

> Get a repo connected and pushing reliably first. Troubleshooting comes after.

A structured, opinionated walkthrough of Git/GitHub setup for the **CloudOps Training** curriculum. Content is split into small, focused files so you can read it in order or jump straight to what you need.

---

## 📚 Reading Order

| # | Topic | File | Read time |
|---|---|---|---|
| 1 | **Setup & Daily Workflow** — global config, connect to GitHub, first push, day-to-day add/commit/push | [`01-setup-and-workflow.md`](./01-setup-and-workflow.md) | ~6 min |
| 2 | **Troubleshooting** — wrong SSH key/account, "nothing to commit" | [`02-troubleshooting.md`](./02-troubleshooting.md) | ~5 min |

---

## 🎯 The One-Slide Summary

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  Working Dir ──git add──► Staging ──git commit──► Local Repo ──git push──►│ GitHub
│  (edited files)           (git add .)             (snapshot,             │ (origin)
│                                                     local only)           │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘

   git status  → free preview of what's about to be staged, anywhere in the cycle
   git commit  → NEVER touches the network — push is the only network step
```

**Three commands cover 90% of daily use:** `git status`, `git add .`, `git commit -m "…"`, `git push`. Everything else in this folder is either one-time setup or fixing something that broke.

---

## 🧭 Where to Start

- **New repo, first time ever?** → [Setup & Daily Workflow](./01-setup-and-workflow.md), read top to bottom.
- **Already set up, just need the daily loop?** → [Setup & Daily Workflow → Day-to-Day section](./01-setup-and-workflow.md#-day-to-day-workflow-going-forward).
- **Pushing as the wrong GitHub account, or "nothing to commit"?** → [Troubleshooting](./02-troubleshooting.md).

---

<sub>📚 Part of the CloudOps Training curriculum · Git</sub>
