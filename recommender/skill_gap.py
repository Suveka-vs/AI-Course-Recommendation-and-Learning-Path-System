"""
Skill gap analysis.

Compares a user's current skills against the required skills for their
target job role (loaded from dataset/role_skills.csv) and computes:
    - matched skills
    - missing skills
    - a skill match percentage
"""

import csv
from pathlib import Path
from django.conf import settings

_ROLE_SKILLS_CSV_PATH = Path(settings.BASE_DIR) / 'dataset' / 'role_skills.csv'

_role_skills_cache = None  # dict: role_name -> list[str]


def _load_role_skills():
    global _role_skills_cache
    if _role_skills_cache is not None:
        return _role_skills_cache

    mapping = {}
    with open(_ROLE_SKILLS_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            role_name = row['role_name'].strip()
            skills = [s.strip() for s in row['required_skills'].split('|') if s.strip()]
            mapping[role_name] = skills

    _role_skills_cache = mapping
    return mapping


def get_required_skills(role_name):
    """
    Return the list of required skills for a role, or None if the role
    isn't in our curated dataset (e.g. a free-typed custom role).
    """
    return _load_role_skills().get(role_name)


def analyze_skill_gap(user_skill_names, role_name):
    """
    Compare the user's skills against the required skills for role_name.

    Returns a dict:
        {
            'available': bool,          # False if role isn't in our dataset
            'matched': [str],
            'missing': [str],
            'required_count': int,
            'matched_count': int,
            'match_percentage': int,
        }
    """
    required_skills = get_required_skills(role_name)

    if required_skills is None:
        return {
            'available': False,
            'matched': [],
            'missing': [],
            'required_count': 0,
            'matched_count': 0,
            'match_percentage': 0,
        }

    user_skills_lower = {s.lower() for s in user_skill_names}

    matched = [s for s in required_skills if s.lower() in user_skills_lower]
    missing = [s for s in required_skills if s.lower() not in user_skills_lower]

    required_count = len(required_skills)
    matched_count = len(matched)
    match_percentage = round((matched_count / required_count) * 100) if required_count else 0

    return {
        'available': True,
        'matched': matched,
        'missing': missing,
        'required_count': required_count,
        'matched_count': matched_count,
        'match_percentage': match_percentage,
    }