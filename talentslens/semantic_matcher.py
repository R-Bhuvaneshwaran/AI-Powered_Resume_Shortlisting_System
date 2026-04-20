from sentence_transformers import SentenceTransformer, util

# Load model once (very important)
model = SentenceTransformer('all-MiniLM-L6-v2')


def semantic_score(candidate_skills, job_skills):

    if not candidate_skills or not job_skills:
        return 0

    candidate_text = " ".join(candidate_skills)
    job_text = " ".join(job_skills)

    emb1 = model.encode(candidate_text, convert_to_tensor=True)
    emb2 = model.encode(job_text, convert_to_tensor=True)

    score = util.cos_sim(emb1, emb2)

    return float(score) * 100