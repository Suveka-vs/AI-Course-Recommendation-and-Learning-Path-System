"""
Custom management command to build the RAG (retrieval) index over the
Course dataset and role-skill knowledge base.

Run with:
    python manage.py build_rag_index

Re-run this any time you reload courses (python manage.py load_courses)
or edit dataset/role_skills.csv, so the index stays in sync.
"""

from django.core.management.base import BaseCommand
from recommender.models import Course
from recommender import rag


class Command(BaseCommand):
    help = 'Build the FAISS RAG index from the Course table and role-skill dataset.'

    def handle(self, *args, **options):
        course_count = Course.objects.count()
        if course_count == 0:
            self.stderr.write(self.style.ERROR(
                'No courses found in the database. Run "python manage.py load_courses" first.'
            ))
            return

        self.stdout.write(f'Building RAG index from {course_count} course(s)...')
        self.stdout.write('Downloading/loading embedding model (first run may take a moment)...')

        total_indexed = rag.build_index()

        self.stdout.write(self.style.SUCCESS(
            f'RAG index built successfully. {total_indexed} knowledge chunk(s) indexed.'
        ))