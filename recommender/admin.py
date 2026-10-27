from django.contrib import admin
from .models import Resume, Skill, UserSkill, TargetRole, Course, PersonalizedExplanation, LearningPath, LearningPathItem, AssessmentAttempt


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_filename', 'uploaded_at')
    readonly_fields = ('extracted_text',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'source', 'added_at')
    list_filter = ('source',)

@admin.register(TargetRole)
class TargetRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_name', 'is_custom', 'predicted_role', 'predicted_confidence', 'updated_at')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'platform', 'skill', 'level', 'price_type', 'rating')
    list_filter = ('price_type', 'level', 'skill')
    search_fields = ('course_name', 'platform', 'skill')

@admin.register(PersonalizedExplanation)
class PersonalizedExplanationAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_role', 'source', 'generated_at')
    readonly_fields = ('explanation_text',)


class LearningPathItemInline(admin.TabularInline):
    model = LearningPathItem
    extra = 0


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_role', 'generated_at')
    inlines = [LearningPathItemInline]

@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill_name', 'score', 'percentage', 'passed', 'source', 'status', 'created_at')
    list_filter = ('passed', 'source', 'status')
    readonly_fields = ('questions_json', 'selected_answers_json')