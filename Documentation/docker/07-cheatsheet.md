# 7 · Docker Cheat-Sheet

> One-liner reference. Pin this tab.

[← Pitfalls](./06-pitfalls.md) · [Index](../README.MD) · Next: [Week 4 Lab →](./08-week4-lab.md)

---

## 🏗 Images

```bash
docker build -t my-app:v1 .                     # build from ./Dockerfile
docker build --platform linux/amd64 -t x:v1 .   # cross-platform build
docker build --no-cache -t my-app:v1 .          # ignore cache
docker images                                    # list local images
docker image ls -a                              # list all (incl. dangling)
docker rmi my-app:v1                            # remove an image
docker image prune                              # remove dangling images
docker image prune -a                           # remove all unused images
docker history my-app:v1                        # show layers of an image
docker inspect my-app:v1                        # full metadata
docker tag  my-app:v1  registry/my-app:v1       # retag
docker save -o my-app.tar my-app:v1             # export image to tarball
docker load -i my-app.tar                       # import from tarball
```

---

## 🏃 Containers

```bash
docker run my-app:v1                            # foreground
docker run -d --name web my-app:v1              # detached + named
docker run -it --rm ubuntu bash                 # interactive, auto-remove
docker run -d -p 8080:8000 my-app:v1            # publish port
docker run -d -e KEY=val my-app:v1              # set env var
docker run -d --env-file .env my-app:v1         # env from file
docker run -d -v $(pwd):/app my-app:v1          # bind mount
docker run -d -v mydata:/data my-app:v1         # named volume
docker run -d --network mynet my-app:v1         # custom network
docker run -d --restart unless-stopped my-app:v1
docker run --memory=512m --cpus=0.5 my-app:v1   # resource limits

docker ps                                       # running
docker ps -a                                    # all (incl. stopped)
docker ps -q                                    # just IDs (great with xargs)

docker start   web
docker stop    web
docker restart web
docker pause   web
docker unpause web
docker rm      web              # remove stopped
docker rm -f   web              # force-remove (stop + rm)

docker logs -f web              # follow logs
docker logs --tail 100 web
docker exec -it web bash        # shell into running container
docker exec web env             # run one command inside
docker cp file.txt web:/tmp/    # copy in
docker cp web:/tmp/out.log .    # copy out
docker top     web              # ps inside the container
docker stats                    # live resource usage
docker inspect web              # full JSON state
docker diff    web              # what changed vs the image
```

---

## 🌐 Networks

```bash
docker network ls
docker network create mynet
docker network inspect mynet
docker network connect    mynet web
docker network disconnect mynet web
docker network rm         mynet
docker network prune                            # remove unused
```

---

## 💾 Volumes

```bash
docker volume ls
docker volume create mydata
docker volume inspect mydata
docker volume rm     mydata
docker volume prune                             # remove unused
```

---

## 🧩 Compose

```bash
docker compose up -d
docker compose up -d --build            # rebuild before starting
docker compose down
docker compose down -v                  # ⚠️ also removes volumes
docker compose ps
docker compose logs -f
docker compose logs -f web              # one service
docker compose exec web sh
docker compose run --rm web pytest      # one-off task
docker compose restart web
docker compose build web
docker compose pull
docker compose config                   # validate + render final YAML
```

---

## ☁️ Registry (Docker Hub / ECR / GHCR)

```bash
# Docker Hub
docker login
docker push  user/my-app:v1
docker pull  user/my-app:v1

# ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  <acct>.dkr.ecr.ap-south-1.amazonaws.com

aws ecr create-repository --repository-name my-app --region ap-south-1
aws ecr list-images       --repository-name my-app --region ap-south-1
aws ecr describe-images   --repository-name my-app --region ap-south-1

docker tag  my-app:v1  <acct>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
docker push            <acct>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
```

---

## 🧹 Cleanup

```bash
docker system df                 # what's using disk
docker system prune              # stopped containers, unused nets, dangling images
docker system prune -a           # + all unused images
docker system prune -a --volumes # + volumes  (☠️  destructive)

# Nuke everything
docker rm -f  $(docker ps -aq)
docker rmi -f $(docker images -q)
docker volume rm  $(docker volume ls -q)
docker network prune -f
```

---

## 🔧 Dockerfile — Instructions at a Glance

```dockerfile
FROM        image:tag [AS name]         # base image (or stage)
ARG         VAR=default                 # build-time variable
ENV         VAR=value                   # build+runtime env var
WORKDIR     /path                       # cd (creates dir if needed)
COPY        src dst                     # copy from build context
ADD         src dst                     # like COPY + tar/URL (avoid)
RUN         cmd                         # execute at BUILD time
USER        uid[:gid]                   # switch user
EXPOSE      port                        # metadata (does NOT publish)
VOLUME      ["/data"]                   # declare a mount point
HEALTHCHECK CMD curl -f localhost || exit 1
ENTRYPOINT  ["exe","arg"]               # fixed executable
CMD         ["arg1","arg2"]             # default args (or full cmd)
LABEL       org.opencontainers.image.source="..."
```

---

## 🎛 Common `run` Flags

| Flag | Purpose |
|---|---|
| `-d` | Detached (background) |
| `-it` | Interactive + TTY |
| `--rm` | Auto-remove on exit |
| `--name X` | Name the container |
| `-p H:C` | Publish port (host:container) |
| `-P` | Publish all `EXPOSE`d ports to random host ports |
| `-e K=V` | Env var |
| `--env-file f` | Env vars from file |
| `-v H:C` | Bind mount / named volume |
| `-w /path` | Working directory |
| `-u uid` | Run as user |
| `--network N` | Attach to network |
| `--restart` | `no` / `on-failure` / `unless-stopped` / `always` |
| `--memory` | RAM limit (e.g. `512m`) |
| `--cpus` | CPU limit (e.g. `0.5`) |
| `--init` | Add tini as PID 1 |
| `--platform` | Force platform (e.g. `linux/amd64`) |

---

Next: [**Week 4 Lab Sequence →**](./08-week4-lab.md)
