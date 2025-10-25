# Eurorack KB Relay (Option A)

A tiny FastAPI service that sits in front of your private Qdrant cluster.
It keeps your API key server-side. ChatGPT (Barkley) will call **/search**
on this relay to fetch context for answers.

## Files
- app.py
- requirements.txt
- Dockerfile
- .env.example

## Deploy Option 1: Render.com (no Docker needed)

1) Create a new **Web Service** on https://render.com
2) Connect a new GitHub repo with these files (push them to a repo)
3) Set:
   - **Runtime**: Docker *off* (use default build from `requirements.txt`)
   - **Start command**: `uvicorn app:app --host 0.0.0.0 --port 8080`
4) Add **Environment Variables**:
   - `QDRANT_ENDPOINT` = `https://...cloud.qdrant.io`
   - `QDRANT_API_KEY` = your key
   - `RELAY_BEARER_TOKEN` = a secret (you will share this with Barkley to call the relay)
5) Deploy. Your relay URL will look like: `https://eurorack-relay.onrender.com`

## Deploy Option 2: Docker anywhere

```bash
# build
docker build -t eurorack-relay .

# run (replace values)
docker run -it --rm -p 8080:8080 \
  -e QDRANT_ENDPOINT="https://...cloud.qdrant.io" \
  -e QDRANT_API_KEY="..." \
  -e RELAY_BEARER_TOKEN="your-secret" \
  eurorack-relay
```

## Local test without Docker
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export QDRANT_ENDPOINT="https://...cloud.qdrant.io"
export QDRANT_API_KEY="..."
export RELAY_BEARER_TOKEN="test123"
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Try it
```
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8080/search?q=enter+alt+mode+arbhar&k=5&collections=eurorack_manuals"
```

If you see JSON hits with payload metadata, you’re live.

## Give Barkley access
Send Barkley:
- The public relay URL: `https://...`
- The **RELAY_BEARER_TOKEN** you set
Then Barkley will call `/search` to fetch context for your questions.
