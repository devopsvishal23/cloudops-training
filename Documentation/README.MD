# 🐳 Docker — From First Principles

> Build the mental model first. Commands come after.

A structured, opinionated walkthrough of Docker for the **CloudOps Training** curriculum (Week 4). Content is split into small, focused files so you can read it in order or jump straight to what you need.

---

## 📚 Reading Order

| # | Topic | File | Read time |
|---|---|---|---|
| 1 | **Core Concepts** — namespaces, cgroups, image vs container, layers, registry | [`docker/01-concepts.md`](./docker/01-concepts.md) | ~10 min |
| 2 | **The Dockerfile** — anatomy, key instructions, `RUN` vs `CMD` | [`docker/02-dockerfile.md`](./docker/02-dockerfile.md) | ~6 min |
| 3 | **Multi-Stage Builds** — why, how, when (real bug case study) | [`docker/02a-multistage-builds.md`](./docker/02a-multistage-builds.md) | ~8 min |
| 4 | **Core Workflow** — build → run → push, common commands | [`docker/03-workflow.md`](./docker/03-workflow.md) | ~5 min |
| 5 | **Docker Compose** — multi-container apps + private networking | [`docker/04-compose.md`](./docker/04-compose.md) | ~6 min |
| 6 | **ECR** — AWS's private registry, auth flow, push/pull | [`docker/05-ecr.md`](./docker/05-ecr.md) | ~5 min |
| 7 | **Common Pitfalls & Gotchas** — the traps everyone hits | [`docker/06-pitfalls.md`](./docker/06-pitfalls.md) | ~8 min |
| 8 | **Cheat-Sheet** — one-liner command reference | [`docker/07-cheatsheet.md`](./docker/07-cheatsheet.md) | reference |
| 9 | **Week 4 Lab Sequence** — 5-day hands-on plan + repo scaffold | [`docker/08-week4-lab.md`](./docker/08-week4-lab.md) | ~4 min |

---

## 🎯 The One-Slide Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   Dockerfile  ──build──►  Image  ──push──►  Registry (ECR/Hub)       │
│                             │                     │                  │
│                             │                     └──pull──►  Host   │
│                             ▼                                        │
│                         Container   =   process                      │
│                                       + namespaces (isolation)       │
│                                       + cgroups   (resource limits)  │
│                                                                      │
│   Compose  ──►  multi-container app on a private DNS network         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**A container is not a VM.** It's a normal Linux process with an isolated view of the filesystem, network, and process tree — plus hard resource ceilings. That's why it starts in milliseconds.

---

## 🧭 Where to Start

- **New to Docker?** → Read files 1 → 9 in order.
- **Need a command right now?** → [Cheat-Sheet](./docker/07-cheatsheet.md).
- **Something is broken?** → [Pitfalls & Gotchas](./docker/06-pitfalls.md).
- **Doing Week 4 labs?** → [Week 4 Lab Sequence](./docker/08-week4-lab.md).

---

<sub>📚 Part of the CloudOps Training curriculum · Week 4 · Docker</sub>