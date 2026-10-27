import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Resume, Skill, UserSkill, TargetRole, Course, PersonalizedExplanation, LearningPath, LearningPathItem, AssessmentAttempt
from .resume_parser import extract_text
from .skill_extractor import extract_skills_from_text, normalize_manual_skills
from .forms import LoginForm,RegisterForm, ResumeUploadForm, ManualSkillForm, TargetRoleForm
from .role_predictor import predict_role, is_model_available
from .skill_gap import analyze_skill_gap
from .course_recommender import recommend_courses
from . import rag
from . import llm
from .learning_path import generate_learning_path
from django.utils import timezone
from .progress import calculate_progress
from django.contrib.auth.models import User


def home(request):
    return render(request, 'home.html')

def _save_skills_for_user(user, skill_names, source='manual'):
    for skill_name in skill_names:
        skill_name = skill_name.strip()

        if not skill_name:
            continue

        skill, _ = Skill.objects.get_or_create(
            name=skill_name
        )

        UserSkill.objects.update_or_create(
            user=user,
            skill=skill,
            defaults={
                'source': source
            }
        )
        
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip().lower()
            email = form.cleaned_data['email'].strip().lower()
            user = User.objects.create_user(
                username=username,
                email=email,
                password=form.cleaned_data['password1'],
            )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or 'dashboard')
    else:
        form = LoginForm(request)

    return render(request, 'registration/login.html', {'form': form})
    
@login_required
def dashboard(request):
    latest_resume = Resume.objects.filter(user=request.user).first()
    current_skills = Skill.objects.filter(userskill__user=request.user)
    target_role_obj = TargetRole.objects.filter(user=request.user).first()

    skill_match = 0
    if target_role_obj:
        gap_result = analyze_skill_gap(
            [s.name for s in current_skills],
            target_role_obj.role_name
        )
        skill_match = gap_result['match_percentage']

    learning_path = LearningPath.objects.filter(user=request.user).first()
    progress_stats = None
    if learning_path:
        progress_stats = calculate_progress(learning_path.items.all())

    context = {
        'target_role': target_role_obj.role_name if target_role_obj else None,
        'skill_match': skill_match,
        'skill_match_remaining': 100 - skill_match,
        'latest_resume': latest_resume,
        'current_skills': current_skills,
        'progress_stats': progress_stats,
    }
    return render(request, 'recommender/dashboard.html', context)

@login_required
def upload_resume(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.original_filename = request.FILES['file'].name
            resume.save()

            resume.extracted_text = extract_text(resume.file.path)
            resume.save()

            if resume.extracted_text.strip():
                found_skills = extract_skills_from_text(resume.extracted_text)
                _save_skills_for_user(request.user, found_skills, source='resume')

                if found_skills:
                    messages.success(
                        request,
                        f'Resume uploaded! {len(found_skills)} skill(s) detected.'
                    )
                else:
                    messages.warning(
                        request,
                        'Resume text was extracted, but no known skills were detected. '
                        'You can add skills manually.'
                    )
                return redirect('skill_analysis')
            else:
                messages.warning(
                    request,
                    'Resume uploaded, but no readable text could be extracted. '
                    'Try a different file, or enter your skills manually.'
                )
            return redirect('upload_resume')
    else:
        form = ResumeUploadForm()

    resumes = Resume.objects.filter(user=request.user)
    return render(request, 'recommender/upload_resume.html', {
        'form': form,
        'resumes': resumes,
    })


@login_required
def manual_skills(request):
    if request.method == 'POST':
        form = ManualSkillForm(request.POST)
        if form.is_valid():
            raw_text = form.cleaned_data['skills_text']
            skill_names = normalize_manual_skills(raw_text)
            _save_skills_for_user(request.user, skill_names, source='manual')
            messages.success(request, f'{len(skill_names)} skill(s) added.')
            return redirect('skill_analysis')
    else:
        form = ManualSkillForm()

    return render(request, 'recommender/manual_skills.html', {'form': form})


@login_required
def skill_analysis(request):
    current_skills = Skill.objects.filter(userskill__user=request.user).distinct()
    resume_skills = current_skills.filter(userskill__source='resume', userskill__user=request.user)
    manual_skills_qs = current_skills.filter(userskill__source='manual', userskill__user=request.user)

    return render(request, 'recommender/skill_analysis.html', {
        'current_skills': current_skills,
        'resume_skills': resume_skills,
        'manual_skills_qs': manual_skills_qs,
    })


@login_required
def remove_skill(request, skill_id):
    if request.method == 'POST':
        user_skill = get_object_or_404(UserSkill, user=request.user, skill_id=skill_id)
        user_skill.delete()
        messages.info(request, 'Skill removed.')
    return redirect('skill_analysis')

@login_required
def target_role(request):
    # Build text for ML prediction from the user's current skills
    # (falls back gracefully if the user has no skills yet)
    user_skills = Skill.objects.filter(userskill__user=request.user)
    skills_text = ', '.join(skill.name for skill in user_skills)

    prediction = None
    if is_model_available():
        prediction = predict_role(skills_text)

    existing = TargetRole.objects.filter(user=request.user).first()

    if request.method == 'POST':
        form = TargetRoleForm(request.POST)
        if form.is_valid():
            role_choice = form.cleaned_data['role_choice']
            custom_role = form.cleaned_data['custom_role'].strip()

            if role_choice == 'other':
                final_role_name = custom_role
                is_custom = True
            else:
                final_role_name = role_choice
                is_custom = False

            TargetRole.objects.update_or_create(
                user=request.user,
                defaults={
                    'role_name': final_role_name,
                    'is_custom': is_custom,
                    'predicted_role': prediction['role'] if prediction else '',
                    'predicted_confidence': prediction['confidence'] if prediction else None,
                }
            )
            messages.success(request, f'Target role set to "{final_role_name}".')
            return redirect('skill_gap')
    else:
        initial = {}
        if existing:
            if existing.is_custom:
                initial = {'role_choice': 'other', 'custom_role': existing.role_name}
            else:
                initial = {'role_choice': existing.role_name}
        form = TargetRoleForm(initial=initial)

    return render(request, 'recommender/target_role.html', {
        'form': form,
        'prediction': prediction,
        'user_skills': user_skills,
    })

@login_required
def skill_gap_view(request):
    target_role_obj = TargetRole.objects.filter(user=request.user).first()

    if not target_role_obj:
        messages.info(request, 'Please set your target role first.')
        return redirect('target_role')

    current_skills = Skill.objects.filter(userskill__user=request.user)
    gap_result = analyze_skill_gap(
        [s.name for s in current_skills],
        target_role_obj.role_name
    )

    return render(request, 'recommender/skill_gap.html', {
        'target_role': target_role_obj.role_name,
        'gap_result': gap_result,
    })

@login_required
def recommendations_view(request):
    target_role_obj = TargetRole.objects.filter(user=request.user).first()

    if not target_role_obj:
        messages.info(request, 'Please set your target role first.')
        return redirect('target_role')

    current_skills = Skill.objects.filter(userskill__user=request.user)
    gap_result = analyze_skill_gap(
        [s.name for s in current_skills],
        target_role_obj.role_name
    )

    grouped_courses = {}
    if gap_result['available'] and gap_result['missing']:
        grouped_courses = recommend_courses(gap_result['missing'])

    return render(request, 'recommender/recommendations.html', {
        'target_role': target_role_obj.role_name,
        'gap_result': gap_result,
        'grouped_courses': grouped_courses,
    })


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'recommender/course_detail.html', {'course': course})

@login_required
def rag_recommendations(request):
    target_role_obj = TargetRole.objects.filter(user=request.user).first()

    if not target_role_obj:
        messages.info(request, 'Please set your target role first.')
        return redirect('target_role')

    current_skills = Skill.objects.filter(userskill__user=request.user)
    current_skill_names = [s.name for s in current_skills]
    gap_result = analyze_skill_gap(current_skill_names, target_role_obj.role_name)

    retrieved_courses = []
    query_used = None

    if rag.is_index_available():
        missing = gap_result['missing'] if gap_result['available'] else []
        query_used = rag.build_rag_query(missing, target_role_obj.role_name)
        retrieved_courses = rag.retrieve(query_used, top_k=8, only_type='course')

    # Reuse a cached explanation if it already matches the current target role,
    # to avoid calling the LLM API on every page load. Regenerate if the role
    # changed or none exists yet.
    explanation_obj = PersonalizedExplanation.objects.filter(user=request.user).first()
    needs_regeneration = (
        explanation_obj is None or explanation_obj.target_role != target_role_obj.role_name
    )

    if needs_regeneration:
        result = llm.generate_explanation(
            current_skill_names,
            target_role_obj.role_name,
            gap_result['matched'] if gap_result['available'] else [],
            gap_result['missing'] if gap_result['available'] else [],
            retrieved_courses,
        )
        explanation_obj, _ = PersonalizedExplanation.objects.update_or_create(
            user=request.user,
            defaults={
                'target_role': target_role_obj.role_name,
                'explanation_text': result['explanation'],
                'source': result['source'],
            }
        )

    return render(request, 'recommender/rag_recommendations.html', {
        'target_role': target_role_obj.role_name,
        'gap_result': gap_result,
        'retrieved_courses': retrieved_courses,
        'query_used': query_used,
        'index_available': rag.is_index_available(),
        'explanation': explanation_obj,
    })

@login_required
def regenerate_explanation(request):
    PersonalizedExplanation.objects.filter(user=request.user).delete()
    messages.info(request, 'Your personalized explanation will be regenerated.')
    return redirect('rag_recommendations')

@login_required
def learning_path_view(request):
    target_role_obj = TargetRole.objects.filter(user=request.user).first()

    if not target_role_obj:
        messages.info(request, 'Please set your target role first.')
        return redirect('target_role')

    current_skills = Skill.objects.filter(userskill__user=request.user)
    gap_result = analyze_skill_gap(
        [s.name for s in current_skills],
        target_role_obj.role_name
    )

    missing = gap_result['missing'] if gap_result['available'] else []

    existing_path = LearningPath.objects.filter(user=request.user).first()
    needs_regeneration = existing_path is None or existing_path.target_role != target_role_obj.role_name

    if needs_regeneration:
        steps = generate_learning_path(missing, target_role_obj.role_name)

        learning_path, _ = LearningPath.objects.update_or_create(
            user=request.user,
            defaults={'target_role': target_role_obj.role_name}
        )
        learning_path.items.all().delete()

        for step in steps:
            LearningPathItem.objects.create(
                learning_path=learning_path,
                step_number=step['step_number'],
                title=step['title'],
                level=step['level'],
                estimated_duration=step['estimated_duration'],
                is_project_step=step['is_project_step'],
            )
    else:
        learning_path = existing_path

    items = learning_path.items.all()

    step_data = []
    for item in items:
        latest_attempt = AssessmentAttempt.objects.filter(
            user=request.user, learning_path_item=item, status='submitted'
        ).first()
        step_data.append({'item': item, 'latest_attempt': latest_attempt})

    progress_stats = calculate_progress(items)

    return render(request, 'recommender/learning_path.html', {
        'target_role': target_role_obj.role_name,
        'learning_path': learning_path,
        'items': items,
        'step_data': step_data,
        'progress_stats': progress_stats,
    })


@login_required
def regenerate_learning_path(request):
    LearningPath.objects.filter(user=request.user).delete()
    messages.info(request, 'Your learning path will be regenerated.')
    return redirect('learning_path')

@login_required
def start_step(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LearningPathItem, id=item_id, learning_path__user=request.user)
        if item.status == 'not_started':
            item.status = 'in_progress'
            item.save()
            messages.success(request, f'"{item.title}" marked as In Progress.')
    return redirect('learning_path')


@login_required
def complete_step(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LearningPathItem, id=item_id, learning_path__user=request.user)
        item.status = 'completed'
        item.completed_at = timezone.now()
        item.save()
        messages.success(request, f'"{item.title}" marked as Completed!')
    return redirect('learning_path')


@login_required
def reset_step(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LearningPathItem, id=item_id, learning_path__user=request.user)
        item.status = 'not_started'
        item.completed_at = None
        item.save()
        messages.info(request, f'"{item.title}" reset to Not Started.')
    return redirect('learning_path')


@login_required
def progress_view(request):
    learning_path = LearningPath.objects.filter(user=request.user).first()

    if not learning_path:
        messages.info(request, 'Generate your learning path first to start tracking progress.')
        return redirect('learning_path')

    items = learning_path.items.all()
    progress_stats = calculate_progress(items)

    return render(request, 'recommender/progress.html', {
        'target_role': learning_path.target_role,
        'items': items,
        'progress_stats': progress_stats,
    })

@login_required
def profile(request):
    target_role_obj = TargetRole.objects.filter(user=request.user).first()
    current_skills = Skill.objects.filter(userskill__user=request.user)
    resumes = Resume.objects.filter(user=request.user)
    learning_path = LearningPath.objects.filter(user=request.user).first()

    progress_stats = None
    if learning_path:
        progress_stats = calculate_progress(learning_path.items.all())

    return render(request, 'recommender/profile.html', {
        'target_role_obj': target_role_obj,
        'current_skills': current_skills,
        'resumes': resumes,
        'progress_stats': progress_stats,
    })

@login_required
def take_assessment(request, item_id):
    item = get_object_or_404(LearningPathItem, id=item_id, learning_path__user=request.user)

    if item.status == 'completed':
        messages.info(request, f'"{item.title}" is already completed.')
        return redirect('learning_path')

    # Reuse an unfinished attempt if one exists; otherwise generate a fresh set
    # (this also covers retries, since a failed attempt's status is 'submitted',
    # not 'in_progress', so a brand-new set is generated each retry).
    attempt = AssessmentAttempt.objects.filter(
        user=request.user, learning_path_item=item, status='in_progress'
    ).first()

    if not attempt:
        target_role_obj = TargetRole.objects.filter(user=request.user).first()
        target_role_name = target_role_obj.role_name if target_role_obj else ''

        result = llm.generate_questions(item.title, item.level, target_role_name)

        attempt = AssessmentAttempt.objects.create(
            user=request.user,
            learning_path_item=item,
            skill_name=item.title,
            level=item.level,
            questions_json=json.dumps(result['questions']),
            total_questions=len(result['questions']),
            source=result['source'],
        )

        if item.status == 'not_started':
            item.status = 'in_progress'
            item.save()

    all_questions = json.loads(attempt.questions_json)
    # Strip correct_index before handing questions to the template context
    # so the answer key is never rendered into the page.
    safe_questions = [
        {'question': q['question'], 'options': q['options']} for q in all_questions
    ]

    return render(request, 'recommender/assessment.html', {
        'item': item,
        'attempt': attempt,
        'questions': safe_questions,
    })


@login_required
def submit_assessment(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt, id=attempt_id, user=request.user, status='in_progress'
    )

    if request.method != 'POST':
        return redirect('take_assessment', item_id=attempt.learning_path_item.id)

    questions = json.loads(attempt.questions_json)

    selected_answers = []
    score = 0
    for i, q in enumerate(questions):
        raw_answer = request.POST.get(f'question_{i}')
        selected_index = int(raw_answer) if raw_answer is not None else -1
        selected_answers.append(selected_index)
        if selected_index == q['correct_index']:
            score += 1

    total = len(questions)
    percentage = round((score / total) * 100) if total else 0
    passed = percentage >= 70

    attempt.selected_answers_json = json.dumps(selected_answers)
    attempt.score = score
    attempt.percentage = percentage
    attempt.passed = passed
    attempt.status = 'submitted'
    attempt.submitted_at = timezone.now()
    attempt.save()

    if passed:
        item = attempt.learning_path_item
        item.status = 'completed'
        item.completed_at = timezone.now()
        item.save()
        messages.success(request, f'Assessment passed! "{item.title}" marked as completed.')
    else:
        messages.warning(request, 'Assessment not passed — you can retry anytime.')

    return redirect('assessment_result', attempt_id=attempt.id)


@login_required
def assessment_result(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt, id=attempt_id, user=request.user, status='submitted'
    )
    return render(request, 'recommender/assessment_result.html', {'attempt': attempt})