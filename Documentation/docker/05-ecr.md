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

## 🛠 Step-by-Step

### 1. Authenticate Docker to ECR

```bash
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com
```

You should see `Login Succeeded`.

### 2. Create a repository

```bash
aws ecr create-repository \
  --repository-name my-app \
  --region ap-south-1 \
  --image-scanning-configuration scanOnPush=true
```

> 💡 `scanOnPush=true` = free vulnerability scan on every push. Always turn this on.

### 3. Tag and push

```bash
# Tag your local image with the ECR URI
docker tag my-app:v1 \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1

# Push
docker push \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
```

### 4. Pull it back (from any authenticated host)

```bash
docker pull <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
docker run -d -p 8080:8000 \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/my-app:v1
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
