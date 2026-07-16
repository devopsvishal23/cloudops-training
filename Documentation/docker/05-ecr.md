# 5 · ECR — AWS's Container Registry

> **Goal:** understand the ECR auth flow and be able to push/pull an image confidently.

[← Compose](./04-compose.md) · [Index](../README.MD) · Next: [Pitfalls →](./06-pitfalls.md)

---

## Why ECR?

ECR is what Docker Hub is, but **private** and **inside your AWS account**. In this curriculum:

- **Week 5 (CI/CD):** your pipeline pushes to ECR.
- **Weeks 6–8 (EKS):** your cluster pulls from ECR.

You want images to live somewhere your AWS workloads can reach securely without shipping registry credentials around.

---

## 🔐 The Auth Flow

Docker itself doesn't speak AWS IAM. So the flow is: **AWS CLI mints a short-lived token, Docker uses it.**

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

Token TTL: **12 hours**. In CI/CD you re-login on every pipeline run.

---

## 🗝️ Where Does the Token Actually Live?

`docker login` doesn't hand you a token to manage yourself — it stores the result somewhere Docker checks automatically on the next `push`/`pull`.

### Locally

| Location | What's there |
|---|---|
| `~/.docker/config.json` | An auth entry for the ECR registry hostname |
| Credential helper (e.g. `osxkeychain` on Docker Desktop for Mac) | The actual token — `config.json` just holds a reference, not the raw value |

> 💡 If you open `~/.docker/config.json` expecting to see the token and it's not there, that's normal — Docker Desktop on macOS delegates storage to the macOS Keychain via `docker-credential-osxkeychain`. Check the `credsStore` field in that file to see which helper is active.

Either way, the token expires in **12 hours** — a new `docker login` is required after that, regardless of where it's stored.

### In CI/CD

- Pipelines (e.g. GitHub Actions via `aws-actions/amazon-ecr-login`) run the same `get-login-password | docker login` flow under the hood.
- **GitHub-hosted runners** are ephemeral VMs — destroyed after the job finishes, so the token never outlives the run.
- **Self-hosted runners** are *not* ephemeral by default — `~/.docker/config.json` (or its credential helper) can accumulate tokens across jobs unless you explicitly `docker logout` or wipe the runner's home directory between runs. Treat that as a cleanup step, not an afterthought.

---

## 🛠 Step-by-Step

### 1. Set up environment variables

Export these once per shell session — every command below reuses them, so you never hand-edit an account ID or region again.

```bash
export AWS_REGION=ap-south-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Verify
echo $AWS_ACCOUNT_ID
```

### 2. Authenticate Docker to ECR

ECR uses short-lived tokens, not a static password. This fetches a 12-hour token and pipes it straight into `docker login`:

```bash
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

You should see `Login Succeeded`.

### 3. Create a repository

```bash
aws ecr create-repository \
  --repository-name my-app \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true
```

> 💡 `scanOnPush=true` = free vulnerability scan on every push. Always turn this on.

The response's `repositoryUri` field is what you push to — it looks like:

```text
123456789.dkr.ecr.ap-south-1.amazonaws.com/my-app
```

### 4. Tag and push

Docker needs the full registry hostname in the image tag before it knows where to push:

```bash
# Tag your local image with the ECR URI
docker tag my-app:v1 \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:v1

# Push
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:v1
```

Watch the output — each layer pushes separately. If you push a second version later with only a code change, the base layers (e.g. `python:3.11-slim`, `pip install`) will show `Layer already exists` — same cache logic as local builds, applied to the registry.

### 5. Verify it landed

```bash
aws ecr describe-images \
  --repository-name my-app \
  --region $AWS_REGION
```

Or in the AWS Console: **ECR → Repositories → my-app** — you'll see the image with its digest and size.

### 6. Pull it back and run it (prove the round-trip)

```bash
# Delete your local copy first, so you know the next pull is real
docker rmi $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:v1

# Pull from ECR and run
docker run -d -p 8080:8000 \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:v1

curl http://localhost:8080/health
```

It pulls from ECR exactly like Docker Hub — the only difference is the hostname and the auth token.

### 7. Tag `:latest` too — good habit

```bash
docker tag my-app:v1 \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:latest

docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/my-app:latest
```

---

## 🧾 IAM: The Minimum Permissions

Two personas — treat them differently.

### Pushing (CI / your laptop)

```
ecr:GetAuthorizationToken           ─► get the login token
ecr:BatchCheckLayerAvailability     ─► which layers already exist
ecr:InitiateLayerUpload
ecr:UploadLayerPart
ecr:CompleteLayerUpload
ecr:PutImage
```

### Pulling (EKS nodes / ECS tasks)

```
ecr:GetAuthorizationToken
ecr:BatchCheckLayerAvailability
ecr:GetDownloadUrlForLayer
ecr:BatchGetImage
```

For EKS, attach the AWS-managed policy **`AmazonEC2ContainerRegistryReadOnly`** to your node IAM role and pulls just work.

---

## 🏷 Tagging Strategy (do this from day one)

Bad idea: only ever pushing `:latest`.

**Better:**

```
my-app:v1.2.3            ← semantic version (release)
my-app:main-a1b2c3d      ← branch + short git SHA (CI builds)
my-app:latest            ← moving pointer to newest release (optional)
```

Rule of thumb: **immutable tags for deploys**, mutable tags only for humans.

Enforce it with an **ECR lifecycle policy** to auto-expire old images:

```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 20 images",
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 20
    },
    "action": { "type": "expire" }
  }]
}
```

---

## 🧯 Common Errors

| Error | Cause | Fix |
|---|---|---|
| `no basic auth credentials` | You never logged in, or token expired | Re-run `aws ecr get-login-password ... \| docker login ...` |
| `denied: requested access to the resource is denied` | IAM missing `ecr:*` perms | Attach the right policy |
| `manifest for … not found` | Tag doesn't exist | Check `aws ecr list-images` |
| Push very slow / hangs | Wrong region endpoint | Match `--region` to the repo's region |
| `exec format error` on EKS | You built for `arm64` on M-series Mac | Rebuild with `--platform linux/amd64` |

---

Next: [**Pitfalls & Gotchas →**](./06-pitfalls.md)
