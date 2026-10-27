"""
Progress tracking calculations.

Computes overall learning progress stats from a user's LearningPathItem
rows — counts by status and an overall completion percentage.
"""


def calculate_progress(items):
    """
    items: an iterable/queryset of LearningPathItem.

    Returns a dict:
        {
            'total': int,
            'completed': int,
            'in_progress': int,
            'not_started': int,
            'progress_percentage': int,
        }
    """
    items = list(items)
    total = len(items)

    completed = sum(1 for i in items if i.status == 'completed')
    in_progress = sum(1 for i in items if i.status == 'in_progress')
    not_started = sum(1 for i in items if i.status == 'not_started')

    progress_percentage = round((completed / total) * 100) if total else 0

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'not_started': not_started,
        'progress_percentage': progress_percentage,
    }