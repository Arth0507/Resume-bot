import re
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).parent / "models" / "model.joblib"

# Model ek hi baar load hota hai (server start par)
model = joblib.load(MODEL_PATH)


def clean_text(text):
    # Ye Colab ke clean_text se bilkul same hona chahiye
    text = str(text).lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)      # links
    text = re.sub(r"\S+@\S+", " ", text)                # email
    text = re.sub(r"\+?\d[\d\-\s]{8,}\d", " ", text)    # phone number
    text = re.sub(r"[^a-z\s+#]", " ", text)             # sirf letters (c++, c# ke liye + aur #)
    text = re.sub(r"\s+", " ", text).strip()            # extra spaces
    return text


def predict(resume_text, top=3):
    cleaned = clean_text(resume_text)
    proba = model.predict_proba([cleaned])[0]
    order = proba.argsort()[::-1][:top]
    return [
        {"role": model.classes_[i], "percent": round(float(proba[i]) * 100, 1)}
        for i in order
    ]