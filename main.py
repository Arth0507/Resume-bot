import json
import re

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai
from auth import check_password, current_user, hash_password, make_token
from db import conn, init_db
from extractor import extract_text
from jd import match as jd_score
from limiter import check
from ml import predict
from suggest import analyze

app = FastAPI(title="Resume Role Predictor")
init_db()

MAX_SIZE = 5 * 1024 * 1024  # 5 MB


class SignupIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class TextIn(BaseModel):
    text: str


class ChatIn(BaseModel):
    message: str


class JDIn(BaseModel):
    text: str


# ---------- helpers ----------
def chat_for(uid: int, chat_id=None) -> int:
    """Wo chat jo user ne khol rakhi hai. ID galat ya na ho to latest chat (ya nayi) deta hai."""
    with conn() as c:
        if chat_id is not None:
            row = c.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, uid)).fetchone()
            if row:
                return row["id"]
        row = c.execute("SELECT id FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
        if row:
            return row["id"]
        return c.execute("INSERT INTO chats(user_id) VALUES(?)", (uid,)).lastrowid


def save(chat_id: int, role: str, kind: str, content: str):
    with conn() as c:
        c.execute("INSERT INTO messages(chat_id, role, kind, content) VALUES(?,?,?,?)",
                  (chat_id, role, kind, content))


def build_result(filename: str, text: str):
    words = len(text.split())
    if words < 40:
        raise HTTPException(400, "Too little text found in the resume. Paste the full resume or use a clear PDF/DOCX.")
    preds = predict(text)
    sug = analyze(text, preds[0]["role"])

    # This information is given to the AI during chat
    context = (
        "Resume text:\n" + text[:5000]
        + "\n\nTop fields predicted by the ML model: "
        + ", ".join(f"{p['role']} ({p['percent']}%)" for p in preds)
        + f"\nResume health score: {sug['health']}/100"
        + "\nChecks that failed: " + (", ".join(sug["failed"]) or "none")
        + "\nMissing skills: " + (", ".join(sug["skills_missing"]) or "none")
    )
    return {"filename": filename, "words": words, "predictions": preds,
            "suggestions": sug, "context": context}


# ---------- auth ----------
@app.post("/api/signup")
def signup(d: SignupIn):
    email = d.email.strip().lower()
    if not d.name.strip():
        raise HTTPException(400, "Please enter your name")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "Email is not valid")
    if len(d.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    with conn() as c:
        if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(400, "This email is already registered")
        uid = c.execute("INSERT INTO users(name, email, password_hash) VALUES(?,?,?)",
                        (d.name.strip(), email, hash_password(d.password))).lastrowid
    return {"token": make_token(uid), "user": {"id": uid, "name": d.name.strip(), "email": email}}


@app.post("/api/login")
def login(d: LoginIn):
    email = d.email.strip().lower()
    check(f"login:{email}", 10)
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row or not check_password(d.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": make_token(row["id"]),
            "user": {"id": row["id"], "name": row["name"], "email": row["email"]}}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return user


# ---------- resume analysis ----------
@app.post("/api/predict")
def predict_file(file: UploadFile = File(...), user=Depends(current_user),
                 x_chat_id: int | None = Header(default=None)):
    check(f"analyse:{user['id']}", 10)
    data = file.file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "File is larger than 5 MB")
    try:
        text = extract_text(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(400, "Could not read the file. Please try another one.")

    result = build_result(file.filename, text)
    cid = chat_for(user["id"], x_chat_id)
    save(cid, "user", "label", "📎 " + (file.filename or "file"))
    save(cid, "assistant", "result", json.dumps(result))
    return result


@app.post("/api/predict-text")
def predict_text(d: TextIn, user=Depends(current_user),
                 x_chat_id: int | None = Header(default=None)):
    check(f"analyse:{user['id']}", 10)
    result = build_result("pasted text", d.text)
    cid = chat_for(user["id"], x_chat_id)
    label = d.text[:200] + ("..." if len(d.text) > 200 else "")
    save(cid, "user", "label", label)
    save(cid, "assistant", "result", json.dumps(result))
    return result


# ---------- job description match ----------
@app.post("/api/jd-match")
def jd_match(d: JDIn, user=Depends(current_user),
             x_chat_id: int | None = Header(default=None)):
    check(f"analyse:{user['id']}", 10)
    cid = chat_for(user["id"], x_chat_id)
    with conn() as c:
        res = c.execute(
            "SELECT content FROM messages WHERE chat_id=? AND kind='result' ORDER BY id DESC LIMIT 1",
            (cid,)).fetchone()
    if not res:
        raise HTTPException(400, "Upload your resume first, then match it with a job description.")

    context = json.loads(res["content"]).get("context", "")
    resume_text = context.split("\n\nTop fields predicted")[0].replace("Resume text:\n", "", 1)

    try:
        result = jd_score(resume_text, d.text)
    except ValueError as e:
        raise HTTPException(400, str(e))

    label = "Job description: " + d.text[:150] + ("..." if len(d.text) > 150 else "")
    save(cid, "user", "label", label)
    save(cid, "assistant", "jd", json.dumps(result))
    return result


# ---------- AI chat ----------
@app.post("/api/chat")
def chat(d: ChatIn, user=Depends(current_user),
         x_chat_id: int | None = Header(default=None)):
    check(f"chat:{user['id']}", 15)
    msg = d.message.strip()[:3000]
    if not msg:
        raise HTTPException(400, "Message is empty")
    cid = chat_for(user["id"], x_chat_id)

    with conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? AND kind='text' ORDER BY id DESC LIMIT 12",
            (cid,)).fetchall()
        res = c.execute(
            "SELECT content FROM messages WHERE chat_id=? AND kind='result' ORDER BY id DESC LIMIT 1",
            (cid,)).fetchone()

    history = [dict(r) for r in reversed(rows)] + [{"role": "user", "content": msg}]
    context = json.loads(res["content"]).get("context", "") if res else ""

    try:
        reply = ai.chat(history, context)
    except Exception as e:
        raise HTTPException(502, str(e))

    save(cid, "user", "text", msg)
    save(cid, "assistant", "text", reply)
    return {"reply": reply}


# ---------- chats (sidebar) ----------
@app.get("/api/history")
def history(user=Depends(current_user), x_chat_id: int | None = Header(default=None)):
    cid = chat_for(user["id"], x_chat_id)
    with conn() as c:
        rows = c.execute("SELECT role, kind, content FROM messages WHERE chat_id=? ORDER BY id",
                         (cid,)).fetchall()
    out = []
    for r in rows:
        content = json.loads(r["content"]) if r["kind"] in ("result", "jd") else r["content"]
        out.append({"role": r["role"], "kind": r["kind"], "content": content})
    return {"chat_id": cid, "messages": out}


@app.get("/api/chats")
def list_chats(user=Depends(current_user)):
    with conn() as c:
        rows = c.execute(
            """SELECT ch.id,
                      (SELECT content FROM messages m WHERE m.chat_id=ch.id AND m.role='user'
                       ORDER BY m.id LIMIT 1) AS title,
                      (SELECT COUNT(*) FROM messages m WHERE m.chat_id=ch.id) AS n
               FROM chats ch WHERE ch.user_id=? ORDER BY ch.id DESC LIMIT 50""",
            (user["id"],)).fetchall()
    return {"chats": [{"id": r["id"], "title": (r["title"] or "New chat")[:60]} for r in rows]}


@app.post("/api/chats/new")
def new_chat(user=Depends(current_user)):
    with conn() as c:
        row = c.execute("SELECT id FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 1",
                        (user["id"],)).fetchone()
        if row:
            n = c.execute("SELECT COUNT(*) FROM messages WHERE chat_id=?", (row["id"],)).fetchone()[0]
            if n == 0:  # khali chat pehle se hai, nayi mat banao
                return {"chat_id": row["id"]}
        cid = c.execute("INSERT INTO chats(user_id) VALUES(?)", (user["id"],)).lastrowid
    return {"chat_id": cid}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: int, user=Depends(current_user)):
    with conn() as c:
        row = c.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Chat not found")
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    return {"ok": True}


# ---------- frontend ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")