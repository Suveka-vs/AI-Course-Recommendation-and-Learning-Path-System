"""
NLP-based skill extraction.

Pipeline:
1. Load a curated skills vocabulary (dataset/skills.csv) — skill name + aliases.
2. Preprocess resume/manual text (lowercase, whitespace normalization).
3. Match vocabulary terms against the text using word/phrase-boundary matching
   (handles both single-word skills like "Python" and multi-word skills like
   "Machine Learning" or "REST API").
4. Normalize matches back to their canonical skill name and de-duplicate.
"""

import csv
import re
from pathlib import Path
from django.conf import settings

_SKILLS_CSV_PATH = Path(settings.BASE_DIR) / 'dataset' / 'skills.csv'

_skills_cache = None  # populated lazily by _load_skills()


def _load_skills():
    """
    Load and cache the skills dataset as a list of
    (canonical_name, category, [search_terms]) tuples.
    Search terms include the skill name itself plus all its aliases,
    all lowercased for case-insensitive matching.
    """
    global _skills_cache
    if _skills_cache is not None:
        return _skills_cache

    skills = []
    with open(_SKILLS_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['skill_name'].strip()
            category = row.get('category', '').strip()
            aliases_raw = row.get('aliases', '') or ''
            aliases = [a.strip() for a in aliases_raw.split('|') if a.strip()]
            search_terms = list({name.lower(), *[a.lower() for a in aliases]})
            skills.append((name, category, search_terms))

    _skills_cache = skills
    return skills


def _term_pattern(term):
    """
    Build a case-insensitive regex for a skill term that matches it as a
    whole word/phrase (so 'R' doesn't match inside 'Rest' or 'Learning').
    Handles terms containing '.', '+', '#' safely via re.escape.
    """
    escaped = re.escape(term)
    return re.compile(rf'(?<![\w+#.]){escaped}(?![\w+#.])', re.IGNORECASE)


def preprocess_text(text):
    """Basic text preprocessing: normalize whitespace, strip control chars."""
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_skills_from_text(text):
    """
    Extract skills from raw resume/free text.
    Returns a sorted list of canonical skill names found in the text.
    """
    text = preprocess_text(text)
    if not text:
        return []

    found = set()
    for canonical_name, category, search_terms in _load_skills():
        for term in search_terms:
            if _term_pattern(term).search(text):
                found.add(canonical_name)
                break  # no need to check other aliases for this skill

    return sorted(found)


def normalize_manual_skills(raw_input):
    """
    Take a raw comma/semicolon/newline-separated string of user-entered
    skills, normalize each entry, match it against the known vocabulary for
    canonical casing where possible, and remove duplicates while preserving
    order of first appearance.
    """
    if not raw_input:
        return []

    # Split on comma, semicolon, or newline
    raw_parts = re.split(r'[,\n;]+', raw_input)

    # Build a lookup: lowercased search term -> canonical name
    lookup = {}
    for canonical_name, category, search_terms in _load_skills():
        for term in search_terms:
            lookup[term] = canonical_name

    seen = set()
    result = []
    for part in raw_parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        canonical = lookup.get(key, cleaned.title())
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            result.append(canonical)

    return result