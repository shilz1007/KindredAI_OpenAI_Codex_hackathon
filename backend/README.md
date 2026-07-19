
# Kindred AI Backend

## Local OpenAI API key

When model integration is added, store the key only in a local `backend/.env` file.

```powershell
Copy-Item .env.example .env
```

Open `backend/.env` and replace the placeholder value for `OPENAI_API_KEY`. The file is ignored by Git.

Add the model assignments below to the same file:

```env
OPENAI_MODEL_MASTER=gpt-realtime-2
OPENAI_MODEL_AGENTS=gpt-5.1
```
