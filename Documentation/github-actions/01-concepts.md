# 1 · Core Concepts

> **Goal:** by the end of this file you should be able to explain, in your own words, *what a GitHub Actions workflow actually is*, and lay out a repo so that a folder move can never silently break your pipeline again.

Part of: **GitHub Actions docs** (Week 5) · Next: *2 — Workflow Anatomy* (coming next)

---

## 🧨 The Problem GitHub Actions Solves

Before CI/CD, the pipeline lived in your head and your terminal history:

```
write code → docker build → docker tag → docker push to ECR → done
```

That's fine for one person doing it once. It breaks down the moment:

- You forget to push after a code change
- A teammate's broken code never gets tested before merging
- You're shipping at 11pm and mistype a tag

> 💡 **The insight:** move the pipeline out of your head and into a file. The file lives in the repo, is version-controlled, and runs the *same way every time*, on every push — no human in the loop to forget a step.

That file is a **workflow**, and GitHub Actions is the engine that runs it.

---

## 🧬 The Mental Model

```
 Your laptop            GitHub                 GitHub Actions Runner
     │                     │                            │
     │   git push main     │                            │
     │────────────────────▶│                            │
     │                     │      trigger workflow       │
     │                     │─────────────────────────▶ │
     │                     │                            │ checkout code
     │                     │                            │ run each step
     │                     │                            │ (build/test/push)
     │                     │                            │ discard the VM
```

The **runner** is a brand-new Linux VM GitHub spins up for that run only. It has *nothing* on it by default — no Docker layers cached, no app code, no AWS credentials. Every workflow starts from zero and must explicitly check out code, install tools, authenticate, and do the work. When the job ends, the VM is destroyed. Nothing persists between runs unless you explicitly cache or push it somewhere (a registry, an artifact store).

This statelessness is the whole point — it's why "works in CI" is a much stronger claim than "works on my machine." But it also means **paths and structure have to be exactly right on every single run**, because there's no leftover state to paper over a wrong path.

---

## 🎯 Core Vocabulary

| Term | Definition |
|---|---|
| **Workflow** | A YAML file in `.github/workflows/`. Defines what runs and when. One repo can have many. |
| **Trigger** (`on:`) | What causes the workflow to run — `push`, `pull_request`, `schedule`, `workflow_dispatch` (manual). |
| **Job** | A unit of work that runs on one runner. A workflow can have multiple jobs, running in parallel or with dependencies (`needs:`). |
| **Step** | A single command or action inside a job. Steps run sequentially, share the same filesystem/workspace. |
| **Action** | A reusable, packaged step someone else wrote — `actions/checkout@v4`, `aws-actions/amazon-ecr-login@v2`. You consume these, you don't write them from scratch. |
| **Runner** | The ephemeral VM (or self-hosted machine) that actually executes the job. |
| **Secrets** | Sensitive values (AWS keys, tokens) stored in GitHub repo/org settings, injected as env vars at runtime via `${{ secrets.NAME }}`. Never hardcoded in YAML. |

---

## 📁 Folder Structure — How It *Should* Be Laid Out

This is the part that actually causes real-world pipeline failures — not YAML syntax, not missing actions. **Structure drift.**

### The one hard rule GitHub enforces

Workflow files **must** live at `.github/workflows/*.yml` relative to the repo root. That's the only structural constraint GitHub itself imposes. Everything else — where your Dockerfile is, where your app code is — is entirely up to you, and GitHub has **zero mechanism to keep those paths in sync** with what your workflow file references.

```
your-project/                      ← repo root
├── .github/
│   └── workflows/
│       ├── build.yml              ← CI: build + test on every push
│       ├── deploy.yml             ← CD: deploy on merge to main (separate concern)
│       └── README.md              ← 1-liner: "build context = ./app, see below"
├── app/                           ← application code, self-contained
│   ├── Dockerfile
│   ├── requirements.txt (or package.json, go.mod...)
│   └── src/
├── tests/                         ← if not colocated with app/
└── README.md
```

### Why this shape, specifically

- **One workflow file per concern** (`build.yml`, `deploy.yml`, `lint.yml`) instead of one giant file. Easier to read, easier to trigger selectively (`on.push.paths`), easier to bisect when something breaks.
- **App code stays self-contained** under one folder (`app/`), so the workflow only ever needs to know *one* path prefix, not a scattered set of file locations.
- **A one-line `README.md` next to the workflows** stating the current build context / Dockerfile path. It costs nothing to write and it's the difference between "I remembered to update the path" and "the pipeline silently breaks three commits later."

### The mistake pattern worth internalizing

Every real failure in this training so far traced back to the same root cause, not three different bugs:

> **Code moved. The workflow's path string didn't move with it.**

`context: ./app` in a YAML file is just a string. GitHub Actions doesn't validate it against your repo layout until the run actually executes and fails to find the Dockerfile. There is no compiler, no linter, no red squiggle warning you at commit time. You find out **after** you push, in the Actions tab, sometimes several commits after the actual restructure happened — making it harder to connect cause and effect.

**The rule that prevents it:** any commit that moves files (`mv`, folder rename, restructure) must, in the *same commit*, `grep` the workflow files for the old path and update it. Treat the workflow YAML as part of the folder structure, not a separate concern that gets fixed later.

```bash
# run this before committing any restructure
grep -rn "context:\|Dockerfile\|working-directory:" .github/workflows/
```

---

## 🎯 Three Concepts You Must Nail

1. **The runner is stateless.** Nothing survives between runs. If it's not checked out, installed, or authenticated in the workflow itself, it doesn't exist.
2. **Paths in YAML are just strings.** GitHub Actions has no awareness of your repo's folder structure beyond `.github/workflows/`. A path is only ever validated by actually running and failing.
3. **A workflow and a folder structure are one artifact, not two.** Whenever one changes, the other must be checked — in the same commit, not "I'll fix CI after."

---

Next: **2 — Workflow Anatomy** (trigger → job → step breakdown, reading a real YAML file line by line)
