import json
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetView
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    AdminLoginForm,
    AdminPasswordResetForm,
    AdminCreateForm,
    AccountPasswordChangeForm,
    ReminderForm,
    StudentLoginForm,
    StudentRegisterForm,
    UserSettingsForm,
    UserPasswordResetForm,
)
from .models import Reminder, StudyPlan, UserProfile


ADMIN_SUFFIX = '@admin.co.za'


def is_valid_admin(user):
    return (
        user.is_authenticated
        and user.is_staff
        and user.username.lower().endswith(ADMIN_SUFFIX)
    )


admin_required = user_passes_test(is_valid_admin, login_url='admin_login')


def active_reminders_for(user):
    """Tasks visible to users: incomplete, not deleted, and not overdue."""
    return Reminder.objects.filter(
        user=user,
        is_deleted=False,
        is_completed=False,
        due_date__gte=timezone.localdate(),
    )


def filter_reminders_by_status(reminders, selected_status):
    """Filter a reminder queryset using the shared visible task states."""
    today = timezone.localdate()
    active_reminders = reminders.filter(
        is_deleted=False,
        is_completed=False,
        due_date__gte=today,
    )

    if selected_status == 'cancelled':
        return reminders.filter(is_deleted=True)
    if selected_status == 'completed':
        return reminders.filter(is_deleted=False, is_completed=True)
    if selected_status == 'missed':
        return reminders.filter(
            is_deleted=False,
            is_completed=False,
            due_date__lt=today,
        )
    if selected_status == 'active':
        return active_reminders
    if selected_status == 'upcoming':
        return active_reminders.filter(due_date__lte=today + timedelta(days=3))
    return reminders


def generate_study_plan(reminder):
    """Rebuild the user's plan after a task is added or changed."""
    regenerate_study_plans_for(reminder.user)


def regenerate_study_plans_for(user):
    """Schedule active tasks by priority with a 30-minute break between sessions."""
    StudyPlan.objects.filter(reminder__user=user).delete()
    active_reminders = list(active_reminders_for(user))
    if not active_reminders:
        return

    priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
    active_reminders.sort(key=lambda reminder: (
        priority_order[reminder.priority],
        reminder.due_date,
        reminder.created_at,
    ))

    today = timezone.localdate()
    last_due_date = max(reminder.due_date for reminder in active_reminders)
    study_date = today
    while study_date <= last_due_date:
        sessions = [
            reminder for reminder in active_reminders
            if reminder.due_date >= study_date
        ]
        session_start = datetime.combine(study_date, time(8, 0))
        for reminder in sessions:
            duration_minutes = _get_duration_minutes(reminder.priority)
            session_end = session_start + timedelta(minutes=duration_minutes)
            StudyPlan.objects.create(
                reminder=reminder,
                study_date=study_date,
                start_time=session_start.time(),
                end_time=session_end.time(),
                duration=_get_duration_for_priority(reminder.priority),
                recommendation=_get_recommendation_text(reminder, _get_duration_for_priority(reminder.priority)),
            )
            session_start = session_end + timedelta(minutes=30)
        study_date += timedelta(days=1)


def _get_duration_for_priority(priority):
    if priority == 'High':
        return '2 hours'
    if priority == 'Medium':
        return '1 hour'
    return '30 minutes'


def _get_duration_minutes(priority):
    if priority == 'High':
        return 120
    if priority == 'Medium':
        return 60
    return 30


def _get_recommendation_text(reminder, duration_text):
    return (
        f"Spend {duration_text} studying/working on '{reminder.task_name}' "
        f"({reminder.subject}). Priority: {reminder.priority}."
    )


def role_selection_view(request):
    if request.user.is_authenticated:
        if is_valid_admin(request.user):
            return redirect('admin_dashboard')
        return redirect('dashboard')
    return render(request, 'role_selection.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect('dashboard')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                messages.error(request, 'Use the administrator sign-in page for this account.')
            else:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = StudentLoginForm()
    return render(request, 'login.html', {'form': form})


def admin_login_view(request):
    if request.user.is_authenticated:
        if is_valid_admin(request.user):
            return redirect('admin_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Administrator sign-in successful.')
            return redirect('admin_dashboard')
        messages.error(request, 'Administrator sign-in failed. Check your account details.')
    else:
        form = AdminLoginForm()
    return render(request, 'admin_login.html', {'form': form})


class UserPasswordResetView(PasswordResetView):
    form_class = UserPasswordResetForm
    template_name = 'password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')
    extra_context = {
        'account_type': 'User',
        'login_url_name': 'login',
    }


class AdminPasswordResetView(PasswordResetView):
    form_class = AdminPasswordResetForm
    template_name = 'password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')
    extra_context = {
        'account_type': 'Administrator',
        'login_url_name': 'admin_login',
    }


def password_reset_done_view(request):
    return render(request, 'password_reset_done.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('role_selection')


@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    details_form = UserSettingsForm(instance=request.user)
    password_form = AccountPasswordChangeForm(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'details':
            details_form = UserSettingsForm(request.POST, instance=request.user)
            if details_form.is_valid():
                details_form.save()
                messages.success(request, 'Your account details have been updated.')
                return redirect('settings')
        elif action == 'theme':
            profile.dark_mode = request.POST.get('dark_mode') == 'on'
            profile.save(update_fields=['dark_mode'])
            messages.success(request, 'Theme preference updated.')
            return redirect('settings')
        elif action == 'password':
            password_form = AccountPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed.')
                return redirect('settings')

    return render(request, 'settings.html', {
        'details_form': details_form,
        'password_form': password_form,
        'dark_mode': profile.dark_mode,
    })


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    upcoming_limit = today + timedelta(days=7)
    user_reminders = active_reminders_for(request.user)
    upcoming_reminders = user_reminders.filter(due_date__lte=upcoming_limit).order_by('due_date')
    return render(request, 'dashboard.html', {
        'total_reminders': user_reminders.count(),
        'high_priority_count': user_reminders.filter(priority='High').count(),
        'upcoming_reminders_count': upcoming_reminders.count(),
        'notifications_preview': upcoming_reminders[:5],
    })


@login_required
def reminder_list_view(request):
    return render(request, 'reminder_list.html', {
        'reminders': active_reminders_for(request.user).order_by('due_date'),
    })


@login_required
def reminder_detail_view(request, pk):
    reminder = get_object_or_404(active_reminders_for(request.user), pk=pk)
    study_plans = StudyPlan.objects.filter(reminder=reminder).order_by('study_date')
    return render(request, 'reminder_detail.html', {
        'reminder': reminder,
        'study_plans': study_plans,
    })


@login_required
def add_reminder_view(request):
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            generate_study_plan(reminder)
            messages.success(request, f"Reminder '{reminder.task_name}' added successfully!")
            return redirect('reminder_detail', pk=reminder.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ReminderForm()
    return render(request, 'add_reminder.html', {'form': form})


@login_required
def edit_reminder_view(request, pk):
    reminder = get_object_or_404(active_reminders_for(request.user), pk=pk)
    if request.method == 'POST':
        form = ReminderForm(request.POST, instance=reminder)
        if form.is_valid():
            updated_reminder = form.save()
            generate_study_plan(updated_reminder)
            messages.success(request, f"Reminder '{updated_reminder.task_name}' updated successfully!")
            return redirect('reminder_detail', pk=updated_reminder.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ReminderForm(instance=reminder)
    return render(request, 'edit_reminder.html', {'form': form, 'reminder': reminder})


@login_required
def complete_reminder_view(request, pk):
    reminder = get_object_or_404(active_reminders_for(request.user), pk=pk)
    if request.method == 'POST':
        reminder.mark_complete()
        regenerate_study_plans_for(request.user)
        messages.success(request, f"Task '{reminder.task_name}' was marked as done.")
    return redirect('reminder_list')


@login_required
def delete_reminder_view(request, pk):
    reminder = get_object_or_404(active_reminders_for(request.user), pk=pk)
    if request.method == 'POST':
        task_name = reminder.task_name
        reminder.soft_delete()
        regenerate_study_plans_for(request.user)
        messages.success(request, f"Reminder '{task_name}' was moved to Reports.")
        return redirect('reminder_list')
    return render(request, 'delete_reminder.html', {'reminder': reminder})


@login_required
def study_plan_view(request):
    study_plans = StudyPlan.objects.filter(
        reminder__in=active_reminders_for(request.user),
    ).select_related('reminder').order_by('study_date')
    return render(request, 'study_plan.html', {'study_plans': study_plans})


@login_required
def notifications_view(request):
    today = timezone.localdate()
    notifications = active_reminders_for(request.user).filter(
        due_date__lte=today + timedelta(days=3),
    ).order_by('due_date')
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
def calendar_view(request):
    reminders = active_reminders_for(request.user).order_by('due_date')
    priority_colours = {'High': '#dc3545', 'Medium': '#fd7e14', 'Low': '#198754'}
    events = [
        {
            'id': reminder.pk,
            'title': reminder.task_name,
            'start': (
                datetime.combine(reminder.due_date, reminder.due_time).isoformat()
                if reminder.due_time else reminder.due_date.isoformat()
            ),
            'url': request.build_absolute_uri(f'/reminders/{reminder.pk}/'),
            'backgroundColor': priority_colours.get(reminder.priority, '#6c757d'),
            'borderColor': priority_colours.get(reminder.priority, '#6c757d'),
            'extendedProps': {'subject': reminder.subject, 'priority': reminder.priority},
        }
        for reminder in reminders
    ]
    return render(request, 'calendar.html', {'calendar_events': json.dumps(events)})


@login_required
def reports_view(request):
    reminders = Reminder.objects.filter(user=request.user)
    selected_status = request.GET.get('status', 'all')
    valid_statuses = {'all', 'cancelled', 'completed', 'missed', 'active', 'upcoming'}
    if selected_status not in valid_statuses:
        selected_status = 'all'
    report_reminders = filter_reminders_by_status(reminders, selected_status).order_by('due_date')
    return render(request, 'reports.html', {
        'report_reminders': report_reminders,
        'selected_status': selected_status,
    })


@admin_required
def admin_dashboard_view(request):
    today = timezone.localdate()
    reminders = Reminder.objects.all()
    return render(request, 'admin_dashboard.html', {
        'user_count': User.objects.filter(is_staff=False).count(),
        'active_reminder_count': reminders.filter(
            is_deleted=False,
            is_completed=False,
            due_date__gte=today,
        ).count(),
        'overdue_count': reminders.filter(
            is_deleted=False,
            is_completed=False,
            due_date__lt=today,
        ).count(),
        'recent_reminders': reminders.select_related('user').order_by('-created_at')[:10],
    })


@admin_required
def admin_users_view(request):
    users = User.objects.filter(is_staff=False).annotate(
        reminder_count=Count('reminders'),
    ).order_by('username')
    return render(request, 'admin_users.html', {'users': users})


@admin_required
def admin_create_view(request):
    if request.method == 'POST':
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            admin_user = form.save()
            messages.success(request, f"Administrator '{admin_user.username}' was created.")
            return redirect('admin_users')
    else:
        form = AdminCreateForm()
    return render(request, 'admin_create.html', {'form': form})


@admin_required
def admin_reports_view(request):
    reminders = Reminder.objects.select_related('user')
    selected_status = request.GET.get('status', 'all')
    valid_statuses = {'all', 'cancelled', 'completed', 'missed', 'active', 'upcoming'}
    if selected_status not in valid_statuses:
        selected_status = 'all'
    report_reminders = filter_reminders_by_status(reminders, selected_status).order_by('due_date')
    return render(request, 'admin_reports.html', {
        'report_reminders': report_reminders,
        'selected_status': selected_status,
    })
