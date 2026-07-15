# 3 · The Core Workflow

> **Goal:** internalise the loop **`Dockerfile → build → run → push`** and the handful of commands you'll type every day.

[← Dockerfile](./02-dockerfile.md) · [Index](../README.MD) · Next: [Docker Compose →](./04-compose.md)

---

## 🔁 The Loop

```
   ┌──────────────┐   docker build   ┌────────┐   docker push   ┌──────────┐
   │  Dockerfile  │ ───────────────► │ Image  │ ──────────────► │ Registry │
   └──────────────┘                  └────────┘                 └──────────┘
                                         │                            │
                                         │ docker run                 │ docker pull
                                         ▼                            ▼
                                    ┌────────────┐              ┌────────────┐
                                    │ Container  │              │  Another   │
                                    │ (running)  │              │   host     │
                                    └────────────┘              └────────────┘
```

Learn this loop. Everything else (Compose, Kubernetes, CI/CD) is glue on top of it.

---

## 🛠 The 12 Commands You'll Actually Use

### Build

```bash
# Build the image in the current dir, tag as my-app:v1
docker build -t my-app:v1 .

# Build for a different platform (e.g. amd64 image from an M-series Mac)
docker build --platform linux/amd64 -t my-app:v1 .
```

### Run

```bash
# Detached, publish port 8080 → 8000, name it
docker run -d --name web -p 8080:8000 my-app:v1

# Interactive (shell into a fresh container)
docker run -it --rm ubuntu:22.04 /bin/bash

# With env vars and a volume
docker run -d \
  -e DATABASE_URL=postgres://... \
  -v $(pwd)/data:/data \
  -p 8080:8000 \
  my-app:v1
```

Flags you'll see everywhere:

| Flag | Meaning |
|---|---|
| `-d` | Detached (background) |
| `-it` | Interactive + TTY (for shells) |
| `--rm` | Auto-remove when it exits |
| `-p H:C` | Publish **host** port → **container** port |
| `-e KEY=VAL` | Set env var |
| `-v host:container` | Mount volume / bind path |
| `--name` | Give the container a friendly name |
| `--network` | Attach to a specific network |

### Inspect

```bash
docker ps                     # running containers
docker ps -a                  # all, including stopped
docker images                 # local images
docker logs -f web            # follow logs
docker inspect web            # full JSON of container state
docker stats                  # live CPU/mem per container
docker exec -it web /bin/bash # shell inside a running container
```

### Ship

```bash
docker tag my-app:v1  registry.example.com/my-app:v1
docker push           registry.example.com/my-app:v1

docker pull           registry.example.com/my-app:v1
```

### Clean up

```bash
docker stop web && docker rm web    # stop + remove one container
docker rmi my-app:v1                # remove an image
docker system prune                 # remove stopped containers, unused nets, dangling images
docker system prune -a --volumes    # aggressive — also removes unused images + volumes
```

---

## 🔍 What Happens During `docker run`

```
   docker run -d -p 8080:8000 my-app:v1
        │
        ├─► 1. Is the image local? ── no ──► pull from registry
        │                          └─ yes ─┐
        │                                  ▼
        ├─► 2. Create container:
        │     • allocate namespaces (mount/net/pid/uts/ipc)
        │     • apply cgroup limits
        │     • add writable layer on top of image
        │
        ├─► 3. Configure networking:
        │     • attach to bridge network
        │     • set up iptables rule:  host:8080 → container:8000
        │
        └─► 4. Start PID 1 = CMD/ENTRYPOINT
                └─► your app is now running
```

---

## 🧠 Mental Model: `stop` vs `rm` vs `rmi`

```
   docker stop  ──►  sends SIGTERM to PID 1 (container still exists)
   docker rm    ──►  deletes the container (writable layer gone)
   docker rmi   ──►  deletes the IMAGE from local cache
```

You can `docker start` a stopped container. Once `rm`'d, it's gone.

---

Next: [**Docker Compose →**](./04-compose.md)
