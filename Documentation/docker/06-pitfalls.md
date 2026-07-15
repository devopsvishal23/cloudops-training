# 6 · Common Pitfalls & Gotchas

> The traps *everyone* hits. Read this before you spend 3 hours debugging one of them.

[← ECR](./05-ecr.md) · [Index](../README.MD) · Next: [Cheat-Sheet →](./07-cheatsheet.md)

---

## 1. 🥶 `COPY . .` Kills Your Cache

**Symptom:** every rebuild reinstalls all your dependencies, even when only your app code changed.

**Cause:** `COPY . .` comes *before* `RUN pip install`, so any file change busts the deps layer.

```dockerfile
# ❌ Bad
COPY . .
RUN pip install -r requirements.txt

# ✅ Good — deps cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Also: use a `.dockerignore` file so `COPY . .` doesn't drag `.git/`, `node_modules/`, `venv/`, etc. into the image.

```
# .dockerignore
.git
.venv
node_modules
__pycache__
*.log
.env
Dockerfile
docker-compose.yml
```

---

## 2. 🏷 The `:latest` Trap

`:latest` is **not** a special "newest" tag — it's just a default name. It moves whenever someone (or CI) pushes with no tag.

```
   Monday   :  docker pull my-app:latest  →  v1.2
   Tuesday  :  someone pushes buggy v1.3 as :latest
   Wednesday:  docker pull my-app:latest  →  v1.3  💥 prod breaks
```

**Rule:** never deploy `:latest`. Use immutable tags (git SHA, semver). Keep `:latest` for humans, if at all.

---

## 3. 👤 Running as Root

By default your container runs as **UID 0 (root)**. If someone escapes it, they're root on your kernel.

```dockerfile
# ✅ Create and switch to a non-root user
RUN useradd -m -u 1001 appuser
USER appuser
```

Bonus: many Kubernetes security policies (Pod Security Standards, OPA) will *reject* pods running as root.

---

## 4. 🖥 Platform Mismatch (Apple Silicon)

Building on an **M1/M2/M3 Mac** produces `linux/arm64` images by default. Push to ECR → EKS node runs `linux/amd64` → boom:

```
exec /app: exec format error
```

**Fix:** build for the target platform explicitly.

```bash
docker build --platform linux/amd64 -t my-app:v1 .
```

Or build multi-arch with buildx:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t my-app:v1 --push .
```

---

## 5. 💾 Losing Data on `docker compose down -v`

```
   docker compose down       ►  removes containers, keeps volumes
   docker compose down -v    ►  removes containers AND volumes  💥
```

The `-v` flag is a **data-destroying operation**. Muscle memory can murder your dev database. Read before you type.

---

## 6. 🌐 `EXPOSE` Doesn't Publish Ports

```dockerfile
EXPOSE 8000       # documentation only — port is NOT open on the host
```

You still need `-p 8080:8000` on `docker run` (or `ports:` in Compose) to actually reach it.

```
   EXPOSE          ►  "this container listens on 8000" (metadata)
   -p 8080:8000    ►  "map my host's 8080 to the container's 8000" (real)
```

---

## 7. 🔒 Secrets in Layers

Anything you `COPY` or `ENV` into a Dockerfile is **permanently in that layer**, even if you delete it later:

```dockerfile
# ❌ AWS keys now live in the image forever
ENV AWS_SECRET_ACCESS_KEY=...

# ❌ .env file baked into a layer even if you rm it in a later RUN
COPY .env /tmp/.env
RUN rm /tmp/.env
```

Anyone with `docker pull` can inspect the layers and extract them.

**Fix:** pass secrets at *runtime* (`-e`, `--env-file`), or use BuildKit's `--secret` mount for build-time secrets, or a real secret manager (AWS Secrets Manager, SSM).

---

## 8. 🦴 Zombie Containers & Signal Handling (PID 1 problem)

Your app runs as **PID 1** inside the container. PID 1 has special kernel semantics — it must reap zombie children and forward signals. Most language runtimes *don't* do this properly.

**Symptom:** `docker stop` takes 10 seconds (the SIGKILL grace period) because your app never received `SIGTERM`.

**Fix:** use an init like `tini`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends tini
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "app.py"]
```

Or run with `docker run --init ...`.

---

## 9. 🐘 Fat Images

A 2 GB Python image is a bad Python image. Common causes:

| Cause | Fix |
|---|---|
| Using `python:3.11` (Debian full) | Switch to `python:3.11-slim` or `-alpine` |
| Leaving `apt` cache in the layer | `RUN apt-get update && apt-get install -y X && rm -rf /var/lib/apt/lists/*` |
| Copying the whole repo | Use `.dockerignore` |
| Shipping build tools to prod | Use a **multi-stage build** |

Rule of thumb: aim for **< 200 MB** for interpreted apps, **< 30 MB** for compiled ones (distroless / scratch).

---

## 10. 🕒 Time & Timezones

By default many base images have no timezone data. Logs show UTC, cron jobs surprise you.

```dockerfile
RUN apt-get install -y tzdata
ENV TZ=Asia/Kolkata
```

---

## 11. 📜 Logs Filling the Disk

`docker logs` reads from JSON files on disk under `/var/lib/docker/containers/…`. On a long-lived container, this file grows without bound.

**Fix:** cap log size in the daemon config (`/etc/docker/daemon.json`):

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

Or ship logs to CloudWatch / Loki / ELK and stop caring about disk.

---

## 12. 🧨 `docker system prune -a` at 2 AM

`prune -a` deletes **all images not currently used by a running container** — including the ones you'd need to roll back.

Do it deliberately, not on autopilot. On CI runners it's fine. On a dev laptop before a demo, it's not.

---

## Quick Debugging Checklist

When something breaks, in this order:

```
   1.  docker ps -a                ► is the container even alive?
   2.  docker logs <name>          ► what did it say before dying?
   3.  docker inspect <name>       ► env vars? mounts? exit code?
   4.  docker exec -it <name> sh   ► poke around inside a running one
   5.  docker run -it --rm <img> sh► run the image manually, bypass CMD
   6.  docker events               ► watch what the daemon is doing
```

---

Next: [**Cheat-Sheet →**](./07-cheatsheet.md)
