from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('resume/upload/', views.upload_resume, name='upload_resume'),
    path('skills/manual/', views.manual_skills, name='manual_skills'),
    path('skills/analysis/', views.skill_analysis, name='skill_analysis'),
    path('skills/remove/<int:skill_id>/', views.remove_skill, name='remove_skill'),
    path('target-role/', views.target_role, name='target_role'),
    path('skill-gap/', views.skill_gap_view, name='skill_gap'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('recommendations/ai/', views.rag_recommendations, name='rag_recommendations'),
    path('recommendations/ai/regenerate/', views.regenerate_explanation, name='regenerate_explanation'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('learning-path/', views.learning_path_view, name='learning_path'),
    path('learning-path/regenerate/', views.regenerate_learning_path, name='regenerate_learning_path'),
    path('learning-path/step/<int:item_id>/start/', views.start_step, name='start_step'),
    path('learning-path/step/<int:item_id>/complete/', views.complete_step, name='complete_step'),
    path('learning-path/step/<int:item_id>/reset/', views.reset_step, name='reset_step'),
    path('progress/', views.progress_view, name='progress'),
    path('learning-path/step/<int:item_id>/assessment/', views.take_assessment, name='take_assessment'),
    path('assessment/<int:attempt_id>/submit/', views.submit_assessment, name='submit_assessment'),
    path('assessment/<int:attempt_id>/result/', views.assessment_result, name='assessment_result'),
]