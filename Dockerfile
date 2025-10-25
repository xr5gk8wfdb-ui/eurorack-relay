FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install base tools (needed for some deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Render will provide $PORT, so don't hardcode 8080
ENV PORT=$PORT

# Start using uvicorn and bind to 0.0.0.0:$PORT (important for Render)
CMD exec uvicorn app:app --host 0.0.0.0 --port $PORT