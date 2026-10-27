"""
Personalized learning path generation.

Orders the user's missing skills using a curated prerequisite ordering
(dataset/skill_metadata.csv: lower order_weight = learn earlier), attaches
a level and estimated duration to each, and appends a final capstone-project
step so the path always ends with practical application — matching the
spec's example output.
"""

import csv
from pathlib import Path
from django.conf import settings

_METADATA_CSV_PATH = Path(settings.BASE_DIR) / 'dataset' / 'skill_metadata.csv'

_metadata_cache = None

_DEFAULT_METADATA = {
    'level': 'Intermediate',
    'estimated_duration': '1 week',
    'order_weight': 999,  # unknown skills sort to the end, before the capstone step
}


def _load_skill_metadata():
    global _metadata_cache
    if _metadata_cache is not None:
        return _metadata_cache

    mapping = {}
    with open(_METADATA_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['skill_name'].strip()
            mapping[name.lower()] = {
                'level': row['level'].strip(),
                'estimated_duration': row['estimated_duration'].strip(),
                'order_weight': int(row['order_weight']),
            }

    _metadata_cache = mapping
    return mapping


def get_skill_metadata(skill_name):
    """Return {'level', 'estimated_duration', 'order_weight'} for a skill, with a safe default."""
    return _load_skill_metadata().get(skill_name.lower(), _DEFAULT_METADATA)


def generate_learning_path(missing_skills, target_role):
    """
    Build an ordered learning path from the list of missing skill names.

    Returns a list of step dicts:
        {
            'step_number': int,
            'title': str,
            'level': str,
            'estimated_duration': str,
            'is_project_step': bool,
        }

    Steps are sorted by order_weight (prerequisite skills first), and a
    final "Build a <role> Project" step is always appended so the path
    ends in hands-on application.
    """
    if not missing_skills:
        # No gaps — still offer a capstone project step to reinforce existing skills
        return [{
            'step_number': 1,
            'title': f'Build a {target_role} Project',
            'level': 'Advanced',
            'estimated_duration': '2 weeks',
            'is_project_step': True,
        }]

    enriched = []
    for skill_name in missing_skills:
        meta = get_skill_metadata(skill_name)
        enriched.append({
            'title': skill_name,
            'level': meta['level'],
            'estimated_duration': meta['estimated_duration'],
            'order_weight': meta['order_weight'],
            'is_project_step': False,
        })

    enriched.sort(key=lambda s: s['order_weight'])

    steps = []
    for i, item in enumerate(enriched, start=1):
        steps.append({
            'step_number': i,
            'title': item['title'],
            'level': item['level'],
            'estimated_duration': item['estimated_duration'],
            'is_project_step': False,
        })

    # Final capstone step
    steps.append({
        'step_number': len(steps) + 1,
        'title': f'Build a {target_role} Project',
        'level': 'Advanced',
        'estimated_duration': '2 weeks',
        'is_project_step': True,
    })

    return steps