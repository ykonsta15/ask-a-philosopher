# Ask a Philosopher

A production-ready one-shot Streamlit app that answers any question from three philosophical perspectives: Socrates, Plato, and Aristotle.

## Features

- One-shot generation (no conversation history)
- Single OpenAI model call returns all three perspectives as strict JSON
- Robust JSON parsing with one repair retry on invalid output
- Deterministic style variation via hash-based opener/closer hints
- Short outputs per philosopher (2-3 sentences, up to ~80 words)
- Safe redirection behavior for self-harm, illegal wrongdoing, and explicit medical/legal directive requests

## Project Structure

- `app.py` - Streamlit UI and submit flow
- `llm.py` - OpenAI client wrapper and JSON parse/repair logic
- `style.py` - Variant banks and deterministic style hint selection
- `utils.py` - Hashing, sentence helpers, input sanitation
- `requirements.txt` - Python dependencies

## Prerequisites

- Python 3.11+
- OpenAI API key

## Setup

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your API key:

```bash
export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-5-mini"
```

For local development, you can also create a `.env` file in the repo root:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5-mini
```

## Run

```bash
streamlit run app.py
```

Optional: enable in-app `Debug mode` to inspect parser/repair behavior and raw model JSON.

## Smoke Test

Run a quick variation check across 5 prompts:

```bash
python scripts/smoke_test_variation.py
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. In Streamlit Community Cloud, create a new app from your GitHub repo.
3. Set the app entry point to `app.py`.
4. In app settings, add a secret:
   - `OPENAI_API_KEY = your_api_key_here`
5. Deploy.

## Deploy on Railway

This repo includes a `Dockerfile` that runs:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

### Railway UI Steps

1. Push your latest code to GitHub.
2. In Railway, click `New Project`.
3. Select `Deploy from GitHub repo`.
4. Choose this repository.
5. Railway will detect the `Dockerfile` and build automatically.
6. Open your service, go to `Variables`, and add:
   - `OPENAI_API_KEY` = your OpenAI API key
   - `OPENAI_MODEL` = `gpt-5-mini` (or your preferred model)
7. Go to `Settings` and ensure the service has a public domain (Railway can generate one).
8. Redeploy (or trigger a new deploy) after adding variables.

### Notes

- Do not commit secrets; keep them in Railway Variables.
- `PORT` is provided by Railway and is consumed by the Docker command.
- If you rename the Streamlit entry file from `app.py`, update the `Dockerfile` command accordingly.

## Notes

- Do not commit `.env` or API keys.
- Each new submit overwrites prior results in the app session.
