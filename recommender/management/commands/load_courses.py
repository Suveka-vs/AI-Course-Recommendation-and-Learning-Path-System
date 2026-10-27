"""
Loads dataset/courses.csv into the Course table.

Run with:
    python manage.py load_courses

Safe to re-run: existing rows (matched by course_name + platform + skill)
are updated in place rather than duplicated.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from recommender.models import Course


class Command(BaseCommand):
    help = 'Load the curated course dataset from dataset/courses.csv into the database.'

    def handle(self, *args, **options):
        csv_path = Path(settings.BASE_DIR) / 'dataset' / 'courses.csv'

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {csv_path}'))
            return

        created_count = 0
        updated_count = 0

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                course, created = Course.objects.update_or_create(
                    course_name=row['course_name'].strip(),
                    platform=row['platform'].strip(),
                    skill=row['skill'].strip(),
                    defaults={
                        'level': row['level'].strip(),
                        'price_type': row['price_type'].strip(),
                        'rating': float(row['rating']),
                        'duration': row['duration'].strip(),
                        'url': row['url'].strip(),
                        'description': row['description'].strip(),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created_count} course(s), updated {updated_count} course(s).'
        ))