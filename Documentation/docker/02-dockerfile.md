# 2 · The Dockerfile

> **Goal:** understand every line of a Dockerfile and *why* it's ordered the way it is.

[← Concepts](./01-concepts.md) · [Index](../README.MD) · Next: [Core Workflow →](./03-workflow.md)

---

## 📝 Anatomy

A Dockerfile is a **recipe** for building an image. Each line is an instruction that produces a new layer:

```dockerfile
# Start from an official base image (layer 1)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list FIRST (so this layer is cached separately)
COPY requirements.txt .

# Install dependencies (cached if requirements.txt unchanged)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code LAST (invalidated on any code change)
COPY . .

# Document that the app listens on port 8000 (informational only)
EXPOSE 8000

# The command to run when the container starts
CMD ["python", "app.py"]
```

---

## 🧱 Key Instructions

| Instruction | Purpose | Runs at |
|---|---|---|
| `FROM` | Base image. Every Dockerfile starts here. | build |
| `WORKDIR` | Sets working directory (creates it if absent). | build + run |
| `COPY` | Copies files from the build context (your machine) into the image. | build |
| `ADD` | Like `COPY` but also unpacks tarballs / fetches URLs. Prefer `COPY`. | build |
| `RUN` | Executes a command at **build time**. Result is baked into the layer. | build |
| `ENV` | Sets env vars available at build **and** runtime. | build + run |
| `ARG` | Build-time variable only. Not available at runtime. | build |
| `EXPOSE` | Documentation only — does **not** actually open ports. | metadata |
| `USER` | Switches the user for subsequent instructions / at runtime. | build + run |
| `CMD` | Default command at run time. Overridable via `docker run <img> <cmd>`. | run |
| `ENTRYPOINT` | Like `CMD` but harder to override — used for "executable containers". | run |
| `HEALTHCHECK` | Command Docker runs to check container health. | run |
| `VOLUME` | Declares a mount point for external volumes. | metadata |

---

## ⚠️ `RUN` vs `CMD` — the classic confusion

```
   Dockerfile
   ──────────
   RUN  ──► executes during `docker build`   ─► result baked into image
   CMD  ──► executes when `docker run` starts ─► starts your app
```

- **`RUN apt-get install curl`** → curl is now *in* the image.
- **`CMD ["python", "app.py"]`** → Python starts *only when a container is launched*.

You can have **many `RUN`s**, but only **one `CMD`** (last one wins).

### `CMD` vs `ENTRYPOINT` in one picture

```
   docker run myimg              docker run myimg --arg

   CMD ["a","b"]        ►  a b       ►  --arg     (CMD replaced)
   ENTRYPOINT ["a","b"] ►  a b       ►  a b --arg (args appended)

   Both set (best practice):
     ENTRYPOINT ["python", "app.py"]
     CMD        ["--port", "8000"]
   → default:      python app.py --port 8000
   → override:     python app.py --port 9000
```

Rule of thumb:
- **App container?** → `ENTRYPOINT` = the binary, `CMD` = default args.
- **Utility image?** → just `CMD`.

---

## 🚀 Layer-caching Discipline

The **order** of instructions is a performance decision.

**❌ Bad — cache busts on every code change:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt   # re-runs every time any file changes
CMD ["python", "app.py"]
```

**✅ Good — deps cached separately:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .               # only this layer busts on dep changes
RUN pip install -r requirements.txt
COPY . .                              # code changes don't invalidate deps
CMD ["python", "app.py"]
```

```
   Change a Python file        ►   Rebuild time:
   ────────────────────────────────────────────
   Bad Dockerfile              ►   ~60s (reinstalls all deps)
   Good Dockerfile             ►   ~2s  (only last COPY layer rebuilds)
```

---

## 🪶 Bonus: Multi-Stage Builds (preview)

Ship *only* what you need at runtime by using a "builder" stage:

```dockerfile
# ─── Stage 1: build ─────────────────────
FROM golang:1.22 AS builder
WORKDIR /src
COPY . .
RUN go build -o /out/app ./cmd/app

# ─── Stage 2: runtime (tiny) ────────────
FROM gcr.io/distroless/base-debian12
COPY --from=builder /out/app /app
ENTRYPOINT ["/app"]
```

Final image = **just the binary**. No compiler, no source, no shell. Often 10–20× smaller.

---

Next: [**Core Workflow →**](./03-workflow.md)
