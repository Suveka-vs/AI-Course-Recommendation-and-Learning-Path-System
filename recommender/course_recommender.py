"""
Course recommendation engine.

Takes the user's missing skills (from skill_gap.py) and retrieves relevant
courses from the Course table, ranked by rating, ensuring a mix of Free
and Paid options is surfaced for each skill where available.
"""

from .models import Course


def recommend_courses(missing_skills, courses_per_skill=4):
    """
    For each missing skill, return up to `courses_per_skill` best-rated
    courses (highest rating first), trying to include at least one Free
    and one Paid course when both exist for that skill.

    Returns a dict: {skill_name: [Course, ...]}
    Skills with no matching courses in the dataset are simply omitted
    (not included as empty lists), so templates can loop cleanly.
    """
    recommendations = {}

    for skill in missing_skills:
        skill_courses = list(
            Course.objects.filter(skill__iexact=skill).order_by('-rating')
        )
        if not skill_courses:
            continue

        free_courses = [c for c in skill_courses if c.price_type == 'Free']
        paid_courses = [c for c in skill_courses if c.price_type == 'Paid']

        selected = []
        if free_courses:
            selected.append(free_courses[0])
        if paid_courses:
            selected.append(paid_courses[0])

        # Fill remaining slots with the next best-rated courses not already selected
        for course in skill_courses:
            if len(selected) >= courses_per_skill:
                break
            if course not in selected:
                selected.append(course)

        recommendations[skill] = selected[:courses_per_skill]

    return recommendations


def recommend_courses_flat(missing_skills, limit=12):
    """
    Same as recommend_courses(), but returns a single flat list of unique
    courses sorted by rating — useful for a simple "Top Recommended" view.
    """
    grouped = recommend_courses(missing_skills)
    seen_ids = set()
    flat = []

    for skill, courses in grouped.items():
        for course in courses:
            if course.id not in seen_ids:
                seen_ids.add(course.id)
                flat.append(course)

    flat.sort(key=lambda c: c.rating, reverse=True)
    return flat[:limit]