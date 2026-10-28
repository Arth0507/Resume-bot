# Resume Role Predictor

A resume analysis chatbot built with **FastAPI**, a trained **scikit-learn** model, **SQLite** and the **Groq** LLM API.
Upload a resume (PDF or DOCX) and the app predicts which job fields it matches best, scores the resume, suggests improvements, matches it against a job description and lets you chat with an AI career coach.

## Features

- **Job field prediction:** TF-IDF + Random Forest model trained on 2,400+ resumes across 24 categories. Shows the top 3 matches.
- **Resume health score:** 9 rule-based checks (email, LinkedIn/GitHub, summary, education, skills, projects, numbers, action verbs, length) with improvement tips.
- **Skill gap, roles and companies:** skills you have vs. skills worth learning, plus example roles and companies for the predicted field.
- **Job description match:** paste a job description and get a keyword match percentage with matched and missing keywords (TF-IDF + cosine similarity).
- **AI career coach:** chat about your resume using Groq. The AI is given your resume and the ML results as context.
- **Accounts and history:** sign up and log in (bcrypt + JWT). Chats are saved in SQLite and shown in a sidebar.
- **Rate limiting** to protect the API key.

## Screenshots

| Login | Result | AI chat |
|---|---|---|
| ![login](docs/login.png) | ![result](docs/result.png) | ![chat](docs/chat.png) |

Confusion matrix of the model: ![confusion matrix](docs/confusion_matrix.png)

## Model performance

Tested on 497 resumes the model had never seen (20% hold-out split).

| Model | Top-1 accuracy | Top-3 accuracy |
|---|---|---|
| Logistic Regression | 68.01% | 88.93% |
| Linear SVC | 71.83% | 92.56% |
| Complement Naive Bayes | 59.56% | 86.92% |
| **Random Forest (used)** | **75.45%** | **93.76%** |

Random guessing over 24 classes would give about 4%. Categories such as Finance, Accountant, Banking and Consultant overlap a lot, and BPO and Automobile have very few resumes, so those are the weakest classes. The training notebook is in `notebooks/train_model.ipynb`.

**Dataset:** [Resume Dataset on Kaggle](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset) (`Resume.csv`). It is not included in this repo because of its size.

## Tech stack

Python, FastAPI, scikit-learn, SQLite, Groq API, HTML/CSS/JavaScript.

## Project structure

```
Resume-bot/
├── main.py          # FastAPI app and all API routes
├── ml.py            # clean_text, model loading, prediction
├── extractor.py     # text extraction from PDF / DOCX / TXT
├── suggest.py       # resume health checks, skills, roles, companies
├── jd.py            # job description matching
├── ai.py            # Groq API calls
├── auth.py          # password hashing and JWT login
├── db.py            # SQLite tables
├── limiter.py       # simple rate limiter
├── models/model.joblib
├── notebooks/train_model.ipynb
├── static/          # index.html, style.css, app.js
└── requirements.txt
```

## Setup

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:
```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # Linux / Mac
```
3. Install the libraries:
```
   pip install -r requirements.txt
```
4. Create a `.env` file in the project folder:
```
   GROQ_API_KEY=your_groq_key
   GROQ_MODEL=a_chat_model_available_on_your_groq_account
   SECRET_KEY=a_long_random_string
```
   Get a free key at https://console.groq.com. Model names change over time, so check the models list for your account.
   Generate a secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`
5. Run the app:
```
   uvicorn main:app --reload
```
6. Open http://127.0.0.1:8000

The model was trained with scikit-learn 1.6.1, so keep that version (it is pinned in `requirements.txt`).

## Limitations

- Prediction gives a job *field*, not an exact job title (for example, all IT roles fall under one category).
- Scanned PDFs and images are not supported (no OCR).
- Company names are examples only and do not mean those companies are hiring.
- Resume text is stored in the local SQLite database. Do not use real personal data on a shared deployment.
- The rate limiter works in memory and resets when the server restarts.

## Future work

- Finer job roles with a larger, Indian-resume dataset
- OCR for scanned resumes
- PDF export of the analysis report
- Deployment with cookie-based sessions