# Hands-On Recap Checklist

The drill to redo after any gap in studying — a quick "am I still fluent" self-check before moving ahead. Evergreen: edit in place as drills are added/retired, don't fork a dated copy each time.

Deeper explanations live in [`Documentation/`](../Documentation/README.MD) — this file stays action-only, linking out instead of re-explaining.

---

## Flask app → containerized → shipped

1. Write a Flask app **blindly** (no copy-paste) — practice for "write it on a shared screen" interviews.
2. Run it locally in a venv:
   ```bash
   python3 -m venv path/to/venv
   source path/to/venv/bin/activate
   python3 -m pip install <deps>
   ```
3. Write a `Dockerfile` for it and confirm it runs containerized. Reference: [`docker/02-dockerfile.md`](../Documentation/docker/02-dockerfile.md).
4. Write a `docker-compose.yml` to run app + database together. Reference: [`docker/04-compose.md`](../Documentation/docker/04-compose.md).
5. Write a compose file **blindly** for app + database + cache.
6. Rule: `docker-compose.yml` and `Dockerfile` live at the **same directory level**.
7. Explain Compose's container naming pattern (`<project>-<service>-<replica>`) without looking it up. Reference: [`docker/04b-docker-compose-container-naming-generation.md`](../Documentation/docker/04b-docker-compose-container-naming-generation.md).

## ECR

8. Create an ECR repo → push an image → pull it back down → run it. Confirm you can still recite the auth flow unaided.
   ```bash
   export AWS_REGION=us-east-2
   export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ```
9. Explain *why* `docker login` is required for ECR at all, and how ECR's short-lived token auth differs from Docker Hub's username/password. Reference: [`docker/05-ecr.md`](../Documentation/docker/05-ecr.md).
10. Recite the push sequence from memory: **authenticate → tag → push → verify it landed.**

## Docker housekeeping

11. Know these cold:
    ```bash
    docker stop $(docker ps -q)
    docker container prune
    docker system df        # what's actually consuming disk
    ```
    Reference: [`docker/07-cheatsheet.md`](../Documentation/docker/07-cheatsheet.md) · [`docker/06-pitfalls.md`](../Documentation/docker/06-pitfalls.md)

## Git

12. `git log -1 --oneline` — quick "what's the last commit" check.

## CI/CD / GitHub Actions

13. Explain the mental model: what problem CI/CD solves vs. running the build/push commands by hand. Reference: [`github-actions/01-concepts.md`](../Documentation/github-actions/01-concepts.md).
14. Recite the key terms unaided: **workflow, trigger, job, step, action.**
15. Write a GitHub Actions workflow that builds and pushes to ECR on `push to main`.

## Multi-stage builds

16. Write a multi-stage Dockerfile for the same project, blind. Reference: [`docker/02a-multistage-builds.md`](../Documentation/docker/02a-multistage-builds.md) — includes a real bug case study worth re-reading if the build silently doesn't shrink like expected.

---

Open questions and concepts parked for later → [`backlog.md`](./backlog.md). Dated journal of study sessions → [`log.md`](./log.md).
