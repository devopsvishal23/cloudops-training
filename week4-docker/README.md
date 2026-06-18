# Week 4 — Docker

## Structure
week4-docker/
├── app.py                # Flask app, /health and / endpoints
├── requirements.txt
├── Dockerfile
├── docker-compose.yml    # app + postgres for local dev
└── README.md

## Run locally
docker compose -f week4-docker/docker-compose.yml up --build
curl http://localhost:8080/health
curl http://localhost:8080/

## ECR
Repository: <account-id>.dkr.ecr.ap-south-1.amazonaws.com/cloudops-app

## CI/CD — Week 5
Pipeline: .github/workflows/hello.yml
Trigger: push to main
Steps: checkout → build → test → push to ECR
Tags pushed: latest, short SHA (7 chars), full SHA
