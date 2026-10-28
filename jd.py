from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ml import clean_text

# Aise common words jo skill nahi hote, unhe ignore karte hain
GENERIC = {
    "experience", "work", "team", "ability", "skills", "skill", "strong", "knowledge",
    "years", "year", "good", "required", "preferred", "candidate", "role", "job",
    "responsibilities", "requirements", "looking", "join", "company", "including",
    "etc", "will", "must", "excellent", "understanding", "opportunity", "working",
    "using", "related", "across", "well", "new", "least", "plus", "ideal", "based",
}


def match(resume_text: str, jd_text: str, top_n: int = 25) -> dict:
    resume = clean_text(resume_text)
    jd = clean_text(jd_text)

    if len(jd.split()) < 15:
        raise ValueError("Job description is too short. Paste the full description.")

    # 1) JD ke sabse important words nikalo (TF-IDF weight ke hisaab se)
    vec = TfidfVectorizer(stop_words="english")
    weights = vec.fit_transform([jd]).toarray()[0]
    terms = vec.get_feature_names_out()

    ranked = sorted(
        (t for t in zip(terms, weights) if t[0] not in GENERIC and len(t[0]) > 2),
        key=lambda x: x[1],
        reverse=True,
    )[:top_n]

    # 2) Dekho ki kaunse words resume me hain
    resume_words = set(resume.split())
    matched = [t for t, _ in ranked if t in resume_words]
    missing = [t for t, _ in ranked if t not in resume_words]

    total = sum(w for _, w in ranked) or 1
    got = sum(w for t, w in ranked if t in resume_words)
    keyword_match = round(got / total * 100)

    # 3) Poore text ki similarity (TF-IDF + cosine)
    vec2 = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    m = vec2.fit_transform([resume, jd])
    similarity = round(float(cosine_similarity(m[0], m[1])[0][0]) * 100)

    if keyword_match >= 70:
        verdict = "Strong match"
    elif keyword_match >= 40:
        verdict = "Decent match, can be improved"
    else:
        verdict = "Low match"

    return {
        "match": keyword_match,
        "similarity": similarity,
        "verdict": verdict,
        "matched": matched,
        "missing": missing,
    }