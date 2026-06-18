
## ECR
Repository: 793110104712.dkr.ecr.ap-south-1.amazonaws.com/cloudops-app
Push: docker tag cloudops-app:v1 <uri>:v1 && docker push <uri>:v1

# Week 4 — Docker

## What's here
Flask app with a `/health` and `/` endpoint, wired to Postgres via Compose.

## Run locally
docker compose up --build
curl http://localhost:8080/health

## Build and tag
docker build -t cloudops-app:v1 .

## ECR
Repository: <account-id>.dkr.ecr.ap-south-1.amazonaws.com/cloudops-app

### Authenticate
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com

### Push
docker tag cloudops-app:v1 <ecr-uri>:v1
docker push <ecr-uri>:v1