"""
RAG (Retrieval-Augmented Generation) — retrieval layer.

Builds a knowledge base from two sources:
    1. The curated Course dataset (course_name, skill, platform, level,
       price_type, duration, description)
    2. Role -> required skills knowledge (dataset/role_skills.csv)

Each item is embedded with a sentence-transformer model and indexed in
FAISS for semantic similarity search. At query time, we embed a query
built from the user's missing skills + target role and retrieve the
most semantically relevant chunks — not just exact skill-name filtering
(that's what course_recommender.py already does). This lets RAG surface
genuinely related resources even when wording differs (e.g. a course
about "API development" for a "REST API" gap).

The LLM step in Phase 9 will consume this retrieved context to generate
personalized explanations.
"""

import csv
import pickle
from pathlib import Path

import numpy as np
from django.conf import settings

_INDEX_DIR = Path(settings.BASE_DIR) / 'rag_index'
_INDEX_PATH = _INDEX_DIR / 'course_index.faiss'
_METADATA_PATH = _INDEX_DIR / 'metadata.pkl'

_MODEL_NAME = 'all-MiniLM-L6-v2'

_model_cache = None
_index_cache = None
_metadata_cache = None


def _get_model():
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer
        _model_cache = SentenceTransformer(_MODEL_NAME)
    return _model_cache


def _build_course_documents():
    """Build knowledge-base text chunks from the Course table."""
    from .models import Course

    documents = []
    metadata = []

    for course in Course.objects.all():
        text = (
            f"{course.course_name} on {course.platform}. "
            f"Skill: {course.skill}. Level: {course.level}. "
            f"Price: {course.price_type}. Duration: {course.duration}. "
            f"{course.description}"
        )
        documents.append(text)
        metadata.append({
            'type': 'course',
            'id': course.id,
            'course_name': course.course_name,
            'platform': course.platform,
            'skill': course.skill,
            'level': course.level,
            'price_type': course.price_type,
            'rating': course.rating,
            'duration': course.duration,
            'url': course.url,
            'description': course.description,
        })

    return documents, metadata


def _build_role_documents():
    """Build knowledge-base text chunks from dataset/role_skills.csv."""
    role_skills_path = Path(settings.BASE_DIR) / 'dataset' / 'role_skills.csv'
    documents = []
    metadata = []

    if not role_skills_path.exists():
        return documents, metadata

    with open(role_skills_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            role_name = row['role_name'].strip()
            skills = [s.strip() for s in row['required_skills'].split('|') if s.strip()]
            text = f"{role_name} typically requires these skills: {', '.join(skills)}."
            documents.append(text)
            metadata.append({
                'type': 'role_info',
                'role_name': role_name,
                'skills': skills,
            })

    return documents, metadata


def build_index():
    """
    Build the FAISS index from the current Course table + role skill data,
    and persist it (plus metadata) to disk. Returns the number of items indexed.
    """
    import faiss

    course_docs, course_meta = _build_course_documents()
    role_docs, role_meta = _build_role_documents()

    documents = course_docs + role_docs
    metadata = course_meta + role_meta

    if not documents:
        return 0

    model = _get_model()
    embeddings = model.encode(documents, show_progress_bar=False, convert_to_numpy=True)

    # Normalize so inner product == cosine similarity
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(_INDEX_PATH))
    with open(_METADATA_PATH, 'wb') as f:
        pickle.dump(metadata, f)

    return len(documents)


def is_index_available():
    return _INDEX_PATH.exists() and _METADATA_PATH.exists()


def _load_index():
    global _index_cache, _metadata_cache
    if _index_cache is not None:
        return _index_cache, _metadata_cache

    import faiss

    if not is_index_available():
        return None, None

    _index_cache = faiss.read_index(str(_INDEX_PATH))
    with open(_METADATA_PATH, 'rb') as f:
        _metadata_cache = pickle.load(f)

    return _index_cache, _metadata_cache


def retrieve(query_text, top_k=8, only_type=None):
    """
    Retrieve the top_k most semantically relevant knowledge-base chunks
    for query_text.

    Returns a list of dicts: {**metadata, 'score': float}, sorted by
    descending similarity score. Returns [] if the index isn't built yet
    or the query is empty.

    only_type: optionally restrict results to 'course' or 'role_info'.
    """
    if not query_text or not query_text.strip():
        return []

    index, metadata = _load_index()
    if index is None:
        return []

    import faiss

    model = _get_model()
    query_embedding = model.encode([query_text], convert_to_numpy=True)
    faiss.normalize_L2(query_embedding)

    # Over-fetch a bit so filtering by only_type still leaves enough results
    fetch_k = top_k * 3 if only_type else top_k
    fetch_k = min(fetch_k, index.ntotal)

    scores, indices = index.search(query_embedding, fetch_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        item = dict(metadata[idx])
        if only_type and item['type'] != only_type:
            continue
        item['score'] = round(float(score) * 100, 1)  # as a 0-100 relevance %
        results.append(item)
        if len(results) >= top_k:
            break

    return results


def build_rag_query(missing_skills, target_role):
    """Build a natural-language query string from skill gaps + target role."""
    if not missing_skills:
        return f"Learning resources and courses relevant to becoming a {target_role}."
    skills_text = ', '.join(missing_skills)
    return (
        f"Courses and learning resources to help someone become a {target_role}, "
        f"focused on these missing skills: {skills_text}."
    )