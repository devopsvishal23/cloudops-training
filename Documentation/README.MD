# 🐳 Docker — From First Principles

> Build the mental model first. Commands come after.

---

## 📑 Table of Contents

1. [The Problem Docker Solves](#-the-problem-docker-solves)
2. [The Core Idea: Namespaces + cgroups](#-the-core-idea-linux-namespaces--cgroups)
3. [Three Concepts You Must Nail](#-three-concepts-you-must-nail)
4. [The Dockerfile](#-the-dockerfile)
5. [The Core Workflow](#-the-core-workflow)
6. [Docker Compose](#-docker-compose--multi-container-apps)
7. [ECR — AWS Container Registry](#-ecr--awss-container-registry)
8. [Week 4 Lab Sequence](#-week-4-lab-sequence)
9. [What to Build for Your Repo](#-what-to-build-for-your-repo)

---

## 🧨 The Problem Docker Solves

Cast your mind back to a classic ops nightmare: **"it works on my machine."**

A developer hands you an app. It needs:
- Python **3.9**
- A specific version of a **C library**
- Three **environment variables** set just right

Your server has Python **3.6**, a different **libc**, and a different **locale**. You spend two days debugging what is fundamentally a **packaging problem**, not a code problem.

### Pre-Docker solutions (all painful)

| Approach | Pain |
|---|---|
| **VMs** | Full OS per app · 10–20 GB images · minutes to boot · huge overhead |
| **Manual dependency docs** | Rot immediately · always wrong · always incomplete |
| **Chef / Puppet / Ansible** | Better, but you're still mutating a shared OS |

> 💡 **Docker's insight:** *what if we could package an app with exactly the environment it needs, without the overhead of a full VM?*

---

## 🧬 The Core Idea: Linux Namespaces + cgroups

Docker isn't magic. It's a clean interface on top of **two Linux kernel features** that have existed since 2002 and 2006.

### Namespaces — *"what can this process see?"*

The kernel gives a process its own isolated view of:

| Namespace | Isolates |
|---|---|
| `mount` | The filesystem |
| `network` | Network stack — its own `eth0`, its own IP |
| `pid` | Process IDs — PID 1 inside, invisible to the host |
| `uts` | Hostname |

### cgroups — *"how much resource can this process use?"*

- Max **512 MB** RAM
- Max **0.5** CPU cores
- Max **100 MB/s** disk I/O

If the process exceeds limits, the kernel enforces them — it can't steal from neighbors.

### So what *is* a container?

```
┌──────────────────────────────────────────────────────────┐
│                    Your Linux Kernel                     │
│                                                          │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐        │
│  │ Container  │   │ Container  │   │ Container  │        │
│  │    A       │   │    B       │   │    C       │        │
│  │ (process)  │   │ (process)  │   │ (process)  │        │
│  │            │   │            │   │            │        │
│  │ namespaces │   │ namespaces │   │ namespaces │        │
│  │ + cgroups  │   │ + cgroups  │   │ + cgroups  │        │
│  └────────────┘   └────────────┘   └────────────┘        │
│                                                          │
│           No hypervisor · No emulated HW                 │
└──────────────────────────────────────────────────────────┘
```

> A **container = a process (tree)** running inside a set of **namespaces**, with **cgroup** limits applied. That's it.

This is why containers start in **milliseconds** — there's no OS to boot. The kernel is already running; you're just spawning a process with extra isolation.

### 🍎 On macOS

```
┌───────────────────── Your Mac ────────────────────────┐
│                                                       │
│   Docker CLI  ──────► (talks to daemon)               │
│                          │                            │
│                          ▼                            │
│   ┌──────── Tiny Linux VM (Apple Hypervisor) ───────┐ │
│   │  Docker daemon                                  │ │
│   │  ┌───────────┐  ┌───────────┐  ┌───────────┐    │ │
│   │  │ container │  │ container │  │ container │    │ │
│   │  └───────────┘  └───────────┘  └───────────┘    │ │
│   └─────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

Containers need a Linux kernel, so Docker Desktop runs a tiny Linux VM under the hood. This is why file-sharing between Mac and containers has some latency.

---

## 🎯 Three Concepts You Must Nail

### 1. Image vs Container

The most important distinction in Docker:

| | **Image** | **Container** |
|---|---|---|
| **What it is** | Read-only, layered filesystem snapshot | Running (or stopped) instance of an image |
| **Analogy** | Class definition | Object / instance |
| **AWS analogy** | AMI | Running EC2 instance |
| **Stored where** | Registry (ECR, Docker Hub) or local cache | On your Docker host |
| **Mutable?** | ❌ No. Ever. | ✅ Yes — gets a thin writable layer on top |

```
        IMAGE  (read-only)                 CONTAINER  (running)
   ┌──────────────────────┐         ┌──────────────────────────┐
   │  Layer 4: app code   │         │ ░░ writable layer ░░░░░░ │ ← ephemeral
   │  Layer 3: pip deps   │  ───►   ├──────────────────────────┤
   │  Layer 2: apt curl   │         │  Layer 4: app code       │
   │  Layer 1: ubuntu     │         │  Layer 3: pip deps       │
   └──────────────────────┘         │  Layer 2: apt curl       │
                                    │  Layer 1: ubuntu         │
                                    └──────────────────────────┘
```

> When the container dies, the writable layer is gone. The image is untouched. **Ten containers from the same image share the same read-only layers** in memory/disk — huge efficiency win.

### 2. Image Layers

Each instruction in a Dockerfile creates a new layer:

```
┌───────────────────────────────────────────────────────────┐
│ Layer 4 (rw):  Your app code           ← smallest, changes most  │
├───────────────────────────────────────────────────────────┤
│ Layer 3 (ro):  pip install -r req.txt  ← medium                  │
├───────────────────────────────────────────────────────────┤
│ Layer 2 (ro):  apt install curl        ← large, rarely changes   │
├───────────────────────────────────────────────────────────┤
│ Layer 1 (ro):  ubuntu:22.04 base       ← largest, ~never changes │
└───────────────────────────────────────────────────────────┘
```

> 🧠 **Rule of thumb:** put things that change *least often* at the **top** of your Dockerfile. Docker will cache them and rebuilds will be seconds, not minutes.

### 3. The Registry

An image name is actually a **URL in disguise**:

```
nginx:1.25
│      │
│      └──── tag (version)
└─────────── image name  (implicitly:  docker.io/library/nginx)


123456789.dkr.ecr.ap-south-1.amazonaws.com / my-app : v1.2
│                                            │        │
│                                            │        └── tag
│                                            └─────────── repository
└──────────────────────────────────────────────────────── ECR registry host
```

---

## 📝 The Dockerfile

A Dockerfile is a **recipe** for building an image. Each line is an instruction:

```dockerfile
# Start from an official base image (layer 1)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list first (so this layer is cached separately)
COPY requirements.txt .

# Install dependencies (layer 2 — cached if requirements.txt unchanged)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (layer 3 — invalidated on any code change)
COPY . .

# Document that the app listens on port 8000 (informational only)
EXPOSE 8000

# The command to run when the container starts
CMD ["python", "app.py"]
```

### Key instructions

| Instruction | Purpose |
|---|---|
| `FROM` | Base image. Every Dockerfile starts here. |
| `WORKDIR` | Sets working directory (creates it if absent). |
| `COPY` | Copies files from the build context (your machine) into the image. |
| `RUN` | Executes a command at **build time**. Result is baked into the layer. |
| `ENV` | Sets env vars available at build **and** runtime. |
| `EXPOSE` | Documentation only — does **not** actually open ports. |
| `CMD` | Default command at **run time**. Can be overridden. |
| `ENTRYPOINT` | Like `CMD` but harder to override — used for "executable containers". |

### ⚠️ `RUN` vs `CMD` — classic confusion

```
   Dockerfile
   ──────────
   RUN  ──► executes during `docker build`  ─► result baked into image
   CMD  ──► executes when `docker run` starts ─► starts your app
```

---

## 🔁 The Core Workflow

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

### Common commands

```bash
# Build an image from the Dockerfile in current directory, tag it
docker build -t my-app:v1 .

# Run a container from that image
#   -p 8080:8000  →  maps host port 8080 → container port 8000
#   -d            →  detached (background)
docker run -d -p 8080:8000 my-app:v1

# See running containers
docker ps

# See logs
docker logs <container-id>

# Get a shell inside a running container
docker exec -it <container-id> /bin/bash

# Stop and remove
docker stop <container-id>
docker rm   <container-id>

# Push to a registry
docker tag  my-app:v1 123456.dkr.ecr.region.amazonaws.com/my-app:v1
docker push           123456.dkr.ecr.region.amazonaws.com/my-app:v1
```

---

## 🧩 Docker Compose — Multi-Container Apps

Your real app is never one container. It's **app + database + cache**. Compose lets you define and run multi-container setups with a single YAML file.

```yaml
# docker-compose.yml
services:
  web:
    build: .                    # build from local Dockerfile
    ports:
      - "8080:8000"
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

### Compose networking (the killer feature)

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

> Services find each other by **service name** (`db`, `web`, `redis`). No IPs needed. DNS-based service discovery baked in.

### Compose commands

```bash
docker compose up -d       # start everything
docker compose logs -f     # tail logs from all services
docker compose down        # stop and remove containers
docker compose down -v     # also removes volumes (⚠️ data loss)
```

---

## ☁️ ECR — AWS's Container Registry

ECR is what Docker Hub is, but **private** and inside your AWS account.

- **Week 5 (CI/CD):** pipeline pushes to ECR.
- **Weeks 6–8 (Kubernetes/EKS):** EKS pulls from ECR.

### The push/pull flow

```
   ┌─────────────┐   1. get-login-password   ┌──────────────┐
   │  Your Mac   │ ────────────────────────► │     AWS      │
   │  (docker)   │ ◄──────── token ───────── │     IAM      │
   └──────┬──────┘                           └──────────────┘
          │
          │ 2. docker login  (token valid 12h)
          ▼
   ┌──────────────┐    3. docker push      ┌───────────────┐
   │  Local image │ ─────────────────────► │      ECR      │
   └──────────────┘                        │  repository   │
                                           └───────┬───────┘
                                                   │ 4. docker pull
                                                   ▼
                                            ┌──────────────┐
                                            │ EC2 / EKS /  │
                                            │  ECS node    │
                                            └──────────────┘
```

### Commands

```bash
# 1. Authenticate Docker to ECR (token valid 12 hours)
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com

# 2. Create a repository
aws ecr create-repository --repository-name my-app --region ap-south-1

# 3. Tag and push
docker tag  my-app:v1 <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
docker push           <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
```

---

## 📅 Week 4 Lab Sequence

Structured for **1.5–2 hr/day**.

| Day | Focus | What you do |
|---|---|---|
| **1** | Install + first container | Install Docker Desktop · `docker run hello-world` · `docker run -it ubuntu:22.04 /bin/bash` — poke around, install something, exit, re-run. **Observe that your changes are gone.** Internalise the ephemeral nature. |
| **2** | Build your first image | Minimal Python Flask (or Node) app · write a Dockerfile · `build`, `run`, `curl` · iterate on it — change code, rebuild, **observe layer caching speed**. |
| **3** | Docker Compose | Add a Postgres container · wire your app via env vars · `depends_on` · `docker compose up` · verify app talks to DB · `docker compose down -v`, bring it back up, **verify data is gone without the volume**. |
| **4** | ECR | Create an ECR repository · push your image · pull it back down · run it · **understand the auth flow**. |
| **5** | Cleanup + GitHub | Write a `README.md` · push everything to GitHub · run `docker system prune` and understand what it cleaned up. |

---

## 📦 What to Build for Your Repo

```
week4-docker/
├── app/
│   ├── app.py            # minimal Flask app with a /health endpoint
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml    # app + postgres
└── README.md             # documents the build, run, push commands
```

This becomes the app you'll:

- **Week 5** — containerise in CI/CD
- **Weeks 6–8** — deploy to Kubernetes (EKS)

> 🎯 **Keep it simple.** A Flask app with one route is enough. **The infrastructure is the point, not the app code.**

---

<sub>📚 Part of the CloudOps Training curriculum · Week 4</sub>