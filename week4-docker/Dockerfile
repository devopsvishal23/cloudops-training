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