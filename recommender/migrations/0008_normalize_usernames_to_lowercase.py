from collections import defaultdict
from django.db import migrations


def normalize_usernames_to_lowercase(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    users = list(User.objects.all())

    # Check for case-insensitive duplicate usernames before making changes
    username_map = defaultdict(list)
    for user in users:
        norm_name = user.username.strip().lower()
        username_map[norm_name].append(user)

    duplicates = {norm: u_list for norm, u_list in username_map.items() if len(u_list) > 1}
    if duplicates:
        conflict_info = ", ".join(
            f"'{norm}': user IDs {[u.id for u in u_list]}" for norm, u_list in duplicates.items()
        )
        print(f"Warning: Case-insensitive duplicate usernames detected: {conflict_info}. Preserving records without overwriting.")

    for user in users:
        norm_name = user.username.strip().lower()
        if norm_name in duplicates:
            continue
        if user.username != norm_name:
            user.username = norm_name
            user.save(update_fields=['username'])


def reverse_normalize(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('recommender', '0007_assessmentattempt'),
    ]

    operations = [
        migrations.RunPython(normalize_usernames_to_lowercase, reverse_normalize),
    ]
