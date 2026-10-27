"""
Custom management command to train the job-role prediction model.

Run with:
    python manage.py train_role_model
"""

import csv
from pathlib import Path

import joblib
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


class Command(BaseCommand):
    help = 'Train the TF-IDF + Logistic Regression job role prediction model.'

    def handle(self, *args, **options):
        dataset_path = Path(settings.BASE_DIR) / 'dataset' / 'job_roles.csv'
        model_dir = Path(settings.BASE_DIR) / 'ml_models'
        model_path = model_dir / 'role_model.pkl'

        if not dataset_path.exists():
            self.stderr.write(self.style.ERROR(f'Dataset not found at {dataset_path}'))
            return

        texts, labels = [], []
        with open(dataset_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                texts.append(row['resume_text'])
                labels.append(row['job_role'])

        self.stdout.write(f'Loaded {len(texts)} training samples across {len(set(labels))} roles.')

        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', LogisticRegression(max_iter=1000)),
        ])

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        self.stdout.write(f'Validation accuracy: {accuracy * 100:.1f}% (on {len(y_test)} held-out samples)')

        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, model_path)

        self.stdout.write(self.style.SUCCESS(f'Model saved to {model_path}'))