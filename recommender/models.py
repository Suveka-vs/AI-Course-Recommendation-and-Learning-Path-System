from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/')
    original_filename = models.CharField(max_length=255, blank=True)
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.original_filename or self.file.name}"

    class Meta:
        ordering = ['-uploaded_at']


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class UserSkill(models.Model):
    SOURCE_CHOICES = [
        ('resume', 'Resume'),
        ('manual', 'Manual'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.skill.name}"

    class Meta:
        unique_together = ('user', 'skill')
        ordering = ['skill__name']

ROLE_CHOICES = [
    ('Python Developer', 'Python Developer'),
    ('Python Full Stack Developer', 'Python Full Stack Developer'),
    ('Web Developer', 'Web Developer'),
    ('Data Analyst', 'Data Analyst'),
    ('Data Scientist', 'Data Scientist'),
    ('Machine Learning Engineer', 'Machine Learning Engineer'),
    ('Java Developer', 'Java Developer'),
    ('DevOps Engineer', 'DevOps Engineer'),
    ('Software Developer', 'Software Developer'),
    ('other', 'Other / Enter your own role'),
]


class TargetRole(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='target_role')
    role_name = models.CharField(max_length=150)
    is_custom = models.BooleanField(default=False)
    predicted_role = models.CharField(max_length=150, blank=True)
    predicted_confidence = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} -> {self.role_name}"

LEVEL_CHOICES = [
    ('Beginner', 'Beginner'),
    ('Intermediate', 'Intermediate'),
    ('Advanced', 'Advanced'),
]

PRICE_TYPE_CHOICES = [
    ('Free', 'Free'),
    ('Paid', 'Paid'),
]


class Course(models.Model):
    course_name = models.CharField(max_length=200)
    platform = models.CharField(max_length=100)
    skill = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='Beginner')
    price_type = models.CharField(max_length=10, choices=PRICE_TYPE_CHOICES, default='Free')
    rating = models.FloatField(default=0)
    duration = models.CharField(max_length=50, blank=True)
    url = models.URLField(max_length=500)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.course_name} ({self.platform})"

    class Meta:
        ordering = ['-rating']
        unique_together = ('course_name', 'platform', 'skill')

class PersonalizedExplanation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='explanation')
    target_role = models.CharField(max_length=150)
    explanation_text = models.TextField()
    source = models.CharField(max_length=10, default='fallback')  # 'llm' or 'fallback'
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.target_role} ({self.source})"

class LearningPath(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_path')
    target_role = models.CharField(max_length=150)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.target_role}"


class LearningPathItem(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='items')
    step_number = models.PositiveIntegerField()
    title = models.CharField(max_length=150)
    level = models.CharField(max_length=20)
    estimated_duration = models.CharField(max_length=50)
    is_project_step = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"

    class Meta:
        ordering = ['step_number']

ASSESSMENT_STATUS_CHOICES = [
    ('in_progress', 'In Progress'),
    ('submitted', 'Submitted'),
]


class AssessmentAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessment_attempts')
    learning_path_item = models.ForeignKey(
        LearningPathItem, on_delete=models.CASCADE, related_name='assessment_attempts'
    )
    skill_name = models.CharField(max_length=150)
    level = models.CharField(max_length=20)

    # Store the generated question set (with correct answers) as JSON so the
    # exact same questions can be graded on submit, and so retries can
    # regenerate a fresh set independently.
    questions_json = models.TextField()
    selected_answers_json = models.TextField(blank=True)

    total_questions = models.PositiveIntegerField(default=5)
    score = models.PositiveIntegerField(null=True, blank=True)
    percentage = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    source = models.CharField(max_length=10, default='fallback')  # 'llm' or 'fallback'
    status = models.CharField(max_length=15, choices=ASSESSMENT_STATUS_CHOICES, default='in_progress')

    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.skill_name} ({self.status})"

    class Meta:
        ordering = ['-created_at']