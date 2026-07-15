# 4 · Docker Compose — Multi-Container Apps

> **Goal:** define a whole app (web + db + cache) in one YAML file, and understand how services find each other.

[← Workflow](./03-workflow.md) · [Index](../README.MD) · Next: [ECR →](./05-ecr.md)

---

## Why Compose?

Your real app is never one container. It's **app + database + cache**. Running each one with `docker run` and wiring them together by hand is tedious and error-prone. Compose gives you:

- **One YAML file** describing every service.
- **One command** to start/stop everything.
- **A private network** with DNS-based service discovery.
- **Named volumes** for data that must outlive a container.

---

## A Realistic Example

```yaml
# docker-compose.yml
services:
  web:
    build: .                    # build from local Dockerfile
    ports:
      - "8080:8000"             # host:container
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db

  db:
    image: postgres:15          # pull from Docker Hub
    environment:
      - POSTGRES_PASSWORD=pass
      - POSTGRES_USER=user
      - POSTGRES_DB=mydb
    volumes:
      - pgdata:/var/lib/postgresql/data   # persist data

volumes:
  pgdata:
```

Notice `DATABASE_URL` uses **`db`** as the hostname — that's the *service name*, not an IP.

---

## 🕸 The Private Network

```
   ┌──────────────── Compose private network ─────────────────┐
   │                                                          │
   │   ┌───────────┐          ┌───────────┐                   │
   │   │   web     │ ──DNS──► │    db     │                   │
   │   │  :8000    │          │  :5432    │                   │
   │   └─────┬─────┘          └───────────┘                   │
   │         │                                                │
   └─────────┼────────────────────────────────────────────────┘
             │  host port 8080 → container 8000
             ▼
        ┌─────────┐
        │  You    │  curl http://localhost:8080
        └─────────┘
```

> Every Compose project gets its own **user-defined bridge network**. Services address each other by **service name** — no IPs, no `/etc/hosts` hacks, no service registry. This is exactly the same pattern Kubernetes uses (service DNS).

---

## 💾 Volumes: Ephemeral vs Persistent

```
   No volume        ►  data lives in container's writable layer
                       └─► `docker compose down` = data GONE

   Named volume     ►  data lives in a Docker-managed volume
                       └─► `docker compose down`    = data survives
                       └─► `docker compose down -v` = data gone

   Bind mount       ►  data lives on your host filesystem
                       └─► survives everything; useful for dev
```

Example bind mount for hot-reloading during development:

```yaml
services:
  web:
    build: .
    volumes:
      - ./app:/app          # edit locally → container sees changes
```

---

## 🚦 `depends_on` — What It Actually Does

```
   depends_on:  ► starts db BEFORE web
                ► does NOT wait for db to be READY
```

For real readiness, use a healthcheck:

```yaml
services:
  db:
    image: postgres:15
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      retries: 5

  web:
    build: .
    depends_on:
      db:
        condition: service_healthy   # now waits for the healthcheck
```

---

## 🎛 The Commands

```bash
docker compose up -d          # start everything, detached
docker compose ps             # what's running
docker compose logs -f        # tail logs from all services
docker compose logs -f web    # just one service
docker compose exec web sh    # shell into the web service
docker compose restart web    # restart one service
docker compose down           # stop & remove containers + network
docker compose down -v        # ⚠️ also removes named volumes (data loss)
docker compose build          # rebuild images
docker compose pull           # pull remote images (no rebuild)
```

---

## 🧠 Compose → Kubernetes Mapping (preview)

| Compose | Kubernetes equivalent |
|---|---|
| `service` | `Deployment` + `Pod` |
| `ports:` | `Service` (type `NodePort` / `LoadBalancer`) |
| service name as DNS | `Service` DNS (`db.default.svc.cluster.local`) |
| `volumes:` (named) | `PersistentVolumeClaim` |
| `environment:` | `env:` / `ConfigMap` / `Secret` |
| `depends_on` (healthcheck) | `readinessProbe` |

Getting comfortable with Compose is the fastest on-ramp to Kubernetes.

---

Next: [**ECR →**](./05-ecr.md)
