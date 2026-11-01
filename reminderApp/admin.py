from django.contrib import admin
from .forms import AdminLoginForm
from .models import Reminder, StudyPlan


# Apply the same suffix and staff validation to Django's built-in admin login.
admin.site.login_form = AdminLoginForm


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        'task_name',
        'subject',
        'user',
        'due_date',
        'importance',
        'priority',
        'is_completed',
        'completed_at',
        'is_deleted',
        'deleted_at',
        'created_at',
    )
    list_filter = ('priority', 'is_completed', 'is_deleted', 'subject', 'due_date')
    search_fields = ('task_name', 'subject', 'user__username')
    ordering = ('due_date',)
    list_per_page = 25
    readonly_fields = ('created_at', 'priority', 'completed_at', 'deleted_at')

    fieldsets = (
        ('Task Information', {
            'fields': ('user', 'task_name', 'subject')
        }),
        ('Scheduling', {
            'fields': ('due_date', 'importance', 'priority')
        }),
        ('Metadata', {
            'fields': ('created_at', 'is_completed', 'completed_at', 'is_deleted', 'deleted_at')
        }),
    )


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('reminder', 'study_date', 'duration', 'recommendation')
    list_filter = ('study_date',)
    search_fields = ('reminder__task_name', 'reminder__subject')
    ordering = ('study_date',)
    list_per_page = 25

