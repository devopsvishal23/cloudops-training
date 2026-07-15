# 1 · Core Concepts

> **Goal:** by the end of this file you should be able to explain, in your own words, *what a container actually is* and how it differs from a VM.

[← Back to index](../README.MD) · Next: [The Dockerfile →](./02-dockerfile.md)

---

## 🧨 The Problem Docker Solves

Cast your mind back to a classic ops nightmare: **"it works on my machine."**

A developer hands you an app. It needs:
- Python **3.9**
- A specific version of a **C library**
- Three **environment variables** set just right

Your server has Python **3.6**, a different **libc**, a different **locale**. You spend two days debugging what is fundamentally a **packaging problem**, not a code problem.

### Pre-Docker solutions (all painful)

| Approach | Pain |
|---|---|
| **VMs** | Full OS per app · 10–20 GB images · minutes to boot · huge overhead |
| **Manual dependency docs** | Rot immediately · always wrong · always incomplete |
| **Chef / Puppet / Ansible** | Better, but you're still mutating a shared OS |

> 💡 **Docker's insight:** *what if we could package an app with exactly the environment it needs, without the overhead of a full VM?*

---

## 🧬 The Core Idea: Namespaces + cgroups

Docker isn't magic. It's a clean interface on top of **two Linux kernel features** that have existed since 2002 and 2006.

### Namespaces — *"what can this process see?"*

| Namespace | Isolates |
|---|---|
| `mount` | The filesystem |
| `network` | Network stack — its own `eth0`, its own IP |
| `pid` | Process IDs — PID 1 inside, invisible to the host |
| `uts` | Hostname |
| `ipc` | Shared memory, semaphores |
| `user` | UID/GID mappings |

### cgroups — *"how much resource can this process use?"*

- Max **512 MB** RAM
- Max **0.5** CPU cores
- Max **100 MB/s** disk I/O

If the process exceeds limits, the kernel enforces them — it can't steal from neighbours.

### VM vs Container — side by side

```
        ── Virtual Machines ──                    ── Containers ──

   ┌──────────┐ ┌──────────┐ ┌──────────┐    ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  App A   │ │  App B   │ │  App C   │    │  App A   │ │  App B   │ │  App C   │
   ├──────────┤ ├──────────┤ ├──────────┤    ├──────────┤ ├──────────┤ ├──────────┤
   │ Bins/Lib │ │ Bins/Lib │ │ Bins/Lib │    │ Bins/Lib │ │ Bins/Lib │ │ Bins/Lib │
   ├──────────┤ ├──────────┤ ├──────────┤    └────┬─────┘ └────┬─────┘ └────┬─────┘
   │ Guest OS │ │ Guest OS │ │ Guest OS │         │            │            │
   ├──────────┴─┴──────────┴─┴──────────┤    ┌────┴────────────┴────────────┴────┐
   │           Hypervisor               │    │       Docker Engine               │
   ├────────────────────────────────────┤    ├───────────────────────────────────┤
   │            Host OS                 │    │            Host OS                │
   ├────────────────────────────────────┤    ├───────────────────────────────────┤
   │          Server / HW               │    │          Server / HW              │
   └────────────────────────────────────┘    └───────────────────────────────────┘

     GBs per app · minutes to boot          MBs per app · milliseconds to start
```

> A **container = a process (tree)** running inside a set of **namespaces**, with **cgroup** limits applied. That's it. **No hypervisor. No emulated hardware.** The process runs directly on your kernel.

### 🍎 On macOS

Containers need a Linux kernel — so Docker Desktop runs a tiny Linux VM under the hood using Apple's Hypervisor framework.

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

This is invisible in normal use but explains why file-sharing between Mac and containers has some latency.

---

## 🎯 Three Concepts You Must Nail

### 1. Image vs Container

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
┌──────────────────────────────────────────────────────────────┐
│ Layer 4 (rw):  Your app code           ← smallest, changes most    │
├──────────────────────────────────────────────────────────────┤
│ Layer 3 (ro):  pip install -r req.txt  ← medium                    │
├──────────────────────────────────────────────────────────────┤
│ Layer 2 (ro):  apt install curl        ← large, rarely changes     │
├──────────────────────────────────────────────────────────────┤
│ Layer 1 (ro):  ubuntu:22.04 base       ← largest, ~never changes   │
└──────────────────────────────────────────────────────────────┘
```

> 🧠 **Rule of thumb:** put things that change *least often* at the **top** of your Dockerfile. Docker caches them and rebuilds become seconds, not minutes.

### 3. The Registry

An image name is a **URL in disguise**:

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

| Registry | Use case |
|---|---|
| **Docker Hub** (`docker.io`) | Public default, official images |
| **ECR** | AWS private registry — what you'll use in CI/CD and EKS |
| **GHCR** | GitHub's registry — handy if your code is on GitHub |
| **Self-hosted** (`registry:2`) | Air-gapped or on-prem |

---

Next: [**The Dockerfile →**](./02-dockerfile.md)
