import os

import httpx

URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM = (
    "You are a friendly career coach who reviews resumes. "
    "Always reply in clear, simple English, in short and practical answers. "
    "Only use facts that are present in the resume information provided; never invent details. "
    "If no resume information is given, give general career advice and ask the user to upload their resume."
)


def chat(messages, context=""):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set in the .env file")

    system = SYSTEM
    if context:
        system += "\n\nUser's resume information:\n" + context[:7000]

    body = {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        "messages": [{"role": "system", "content": system}] + messages[-12:],
        "temperature": 0.6,
        "max_tokens": 1500,
    }
    r = httpx.post(URL, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=60)

    if r.status_code == 401:
        raise RuntimeError("Groq API key is invalid")
    if r.status_code == 429:
        raise RuntimeError("Free limit reached, please try again in a little while")
    if r.status_code != 200:
        raise RuntimeError(f"Groq error {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"] or "(The model returned an empty reply. Please try again.)"