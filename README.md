# AI Assistant API

FastAPI backend for the AI Assistant for Visually Impaired People graduation project.

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your environment file from `.env.example`.
4. Provide Firebase credentials using either:
   - `FIREBASE_CREDENTIALS_PATH`
   - `FIREBASE_CREDENTIALS_JSON`

5. Start the server:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Production Notes

- Set `DEBUG=False`
- Set `ENABLE_DOCS=False` unless you want Swagger exposed
- Set `ALLOWED_ORIGINS` to your real frontend origins
- Never commit `.env` or `firebase-credentials.json`
- If your hosting platform prefers environment variables, use `FIREBASE_CREDENTIALS_JSON`

## Docker

Build:

```bash
docker build -t ai-assistant-api .
```

Run:

```bash
docker run -p 8000:8000 --env-file .env ai-assistant-api
```

## Render Deployment

Create a new Web Service on Render and use:

- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables in Render:

- `FIREBASE_CREDENTIALS_JSON`
- `FIREBASE_DATABASE_URL`
- `API_V1_PREFIX`
- `PROJECT_NAME`
- `DEBUG=False`
- `TEST_MODE=False`
- `ALLOWED_ORIGINS_RAW=*`
- `ENABLE_DOCS=True`
- `HOST=0.0.0.0`

If Render provides `PORT`, do not hardcode it in the dashboard.
