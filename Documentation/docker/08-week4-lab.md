# 8 · Week 4 Lab Sequence

> **Goal:** 5 focused days, 1.5–2 hr each, ending with a real containerised app pushed to ECR and committed to your repo.

[← Cheat-Sheet](./07-cheatsheet.md) · [Index](../README.MD)

---

## 🗓 The Week at a Glance

```
   Day 1 ─► Install + first container   (feel the ephemerality)
   Day 2 ─► Build your first image      (layer caching)
   Day 3 ─► Docker Compose              (multi-container + volumes)
   Day 4 ─► ECR                         (auth + push/pull)
   Day 5 ─► Cleanup + GitHub            (ship it)
```

---

## Day 1 — Install + First Container

**Objective:** internalise that containers are **ephemeral**.

- Install Docker Desktop for Mac.
- Verify: `docker version`, `docker info`.
- Run:
  ```bash
  docker run hello-world
  docker run -it ubuntu:22.04 /bin/bash
  ```
- Inside the Ubuntu shell: `apt update && apt install -y cowsay`, then `exit`.
- Re-run `docker run -it ubuntu:22.04 /bin/bash` — **cowsay is gone**.

**Reflect:** the writable layer dies with the container. This is the whole point.

---

## Day 2 — Build Your First Image

**Objective:** feel the layer cache.

- Create `app/app.py` — a minimal Flask app with a `/health` endpoint.
- Create `app/requirements.txt`.
- Write a **good** Dockerfile (deps copied before code).
- Build & run:
  ```bash
  docker build -t week4-app:v1 .
  docker run -d -p 8080:8000 --name web week4-app:v1
  curl http://localhost:8080/health
  ```
- Change one line in `app.py`. Rebuild. **Notice** only the last layer rebuilds.
- Now put `COPY . .` *before* `RUN pip install`. Rebuild. **Notice** it reinstalls everything.

**Deliverable:** working `Dockerfile` + a screenshot / note of the cache-hit vs cache-miss rebuild time.

---

## Day 3 — Docker Compose

**Objective:** multi-container app with a real database.

- Add a `db` service (`postgres:15`) to `docker-compose.yml`.
- Wire your Flask app to it via `DATABASE_URL=postgresql://user:pass@db:5432/mydb`.
- Add a `pgdata` named volume.
- Add `depends_on` with a healthcheck (see [Compose doc](./04-compose.md#-depends_on--what-it-actually-does)).
- Run:
  ```bash
  docker compose up -d
  docker compose logs -f
  ```
- Verify the app can talk to Postgres (add a route that does `SELECT 1`).
- Test persistence:
  ```bash
  docker compose down          # data survives
  docker compose up -d         # verify
  docker compose down -v       # data GONE
  docker compose up -d         # verify DB is empty
  ```

**Deliverable:** `docker-compose.yml` + notes on what `-v` did.

---

## Day 4 — ECR

**Objective:** push your image somewhere real.

- Ensure your AWS CLI is configured (`aws sts get-caller-identity`).
- Create an ECR repo:
  ```bash
  aws ecr create-repository --repository-name week4-app \
    --region ap-south-1 --image-scanning-configuration scanOnPush=true
  ```
- Authenticate, tag, push (see [ECR doc](./05-ecr.md)).
- Delete your local image (`docker rmi ...`), then `docker pull` it back and run it.
- Check the ECR console — you should see the scan results.

**Deliverable:** screenshot of the image in ECR + scan status.

---

## Day 5 — Cleanup + GitHub

**Objective:** ship it.

- Write a `README.md` inside `week4-docker/` documenting:
  - What the app does.
  - How to build & run locally (`docker compose up -d`).
  - How to push to ECR.
- Add a `.dockerignore`.
- Push to GitHub.
- Run `docker system df` — look at the space used.
- Run `docker system prune` — understand what disappeared and why.

**Deliverable:** GitHub repo link.

---

## 📦 Repo Scaffold

Create this folder in your CloudOps repo:

```
week4-docker/
├── app/
│   ├── app.py            # minimal Flask app with a /health endpoint
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml    # app + postgres
├── .dockerignore
└── README.md             # build, run, push commands
```

### Starter files

**`app/app.py`**
```python
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify(status="ok", db=os.getenv("DATABASE_URL", "unset"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

**`app/requirements.txt`**
```
flask==3.0.3
psycopg[binary]==3.2.1
```

**`Dockerfile`**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
EXPOSE 8000
CMD ["python", "app.py"]
```

**`docker-compose.yml`**
```yaml
services:
  web:
    build: .
    ports: ["8080:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=pass
      - POSTGRES_USER=user
      - POSTGRES_DB=mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

**`.dockerignore`**
```
.git
.venv
__pycache__
*.pyc
*.log
.env
Dockerfile
docker-compose.yml
README.md
```

---

## ✅ Definition of Done

You're done with Week 4 when you can:

- [ ] Explain, in one sentence, what a container is (namespaces + cgroups).
- [ ] Explain image vs container without hesitation.
- [ ] Write a Dockerfile that respects layer caching.
- [ ] Bring up a multi-service app with `docker compose up`.
- [ ] Push and pull an image from ECR.
- [ ] Read a `docker logs` output and diagnose a failing container.

This app becomes the foundation for **Week 5 (CI/CD)** and **Weeks 6–8 (EKS)**. Keep it simple — the infrastructure is the point.

---

[← Back to index](../README.MD)
