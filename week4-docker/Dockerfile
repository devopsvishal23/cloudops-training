# week4-docker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Dependencies first — this layer gets cached separately
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code last — this layer is the one that changes most
COPY app/ .

EXPOSE 8000

CMD ["python", "app.py"]