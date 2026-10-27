"""
ML-based job role prediction.

Trains a TF-IDF + Logistic Regression pipeline on dataset/job_roles.csv
(resume_text -> job_role), saved to ml_models/role_model.pkl via joblib.

Used when the user does not manually select a target role: we predict
the most likely role from their resume/skill text, with a confidence score.
"""

from pathlib import Path
import joblib
from django.conf import settings

_MODEL_PATH = Path(settings.BASE_DIR) / 'ml_models' / 'role_model.pkl'

_model_cache = None  # lazily loaded sklearn Pipeline


def _load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    if not _MODEL_PATH.exists():
        return None

    _model_cache = joblib.load(_MODEL_PATH)
    return _model_cache


def is_model_available():
    """True if a trained model file exists on disk."""
    return _MODEL_PATH.exists()


def predict_role(text):
    """
    Predict the most likely job role from free text (e.g. resume text or
    a comma-joined list of the user's skills).

    Returns a dict: {'role': str, 'confidence': float} or None if no
    trained model is available or the input text is empty.
    """
    if not text or not text.strip():
        return None

    model = _load_model()
    if model is None:
        return None

    probabilities = model.predict_proba([text])[0]
    classes = model.classes_
    best_index = probabilities.argmax()

    return {
        'role': classes[best_index],
        'confidence': round(float(probabilities[best_index]) * 100, 1),
    }