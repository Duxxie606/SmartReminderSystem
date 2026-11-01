from django.urls import path
from . import views

urlpatterns = [
    # Role selection and authentication
    path('', views.role_selection_view, name='role_selection'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('forgot-password/', views.UserPasswordResetView.as_view(), name='password_reset'),
    path('admin-forgot-password/', views.AdminPasswordResetView.as_view(), name='admin_password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),

    # User dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Reminders
    path('reminders/', views.reminder_list_view, name='reminder_list'),
    path('reminders/<int:pk>/', views.reminder_detail_view, name='reminder_detail'),
    path('reminders/add/', views.add_reminder_view, name='add_reminder'),
    path('reminders/<int:pk>/edit/', views.edit_reminder_view, name='edit_reminder'),
    path('reminders/<int:pk>/complete/', views.complete_reminder_view, name='complete_reminder'),
    path('reminders/<int:pk>/delete/', views.delete_reminder_view, name='delete_reminder'),

    # Study Plan
    path('study-plan/', views.study_plan_view, name='study_plan'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),

    # Calendar and Reports
    path('calendar/', views.calendar_view, name='calendar'),
    path('reports/', views.reports_view, name='reports'),

    # Staff-only administration overview
    path('admin-portal/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-portal/users/', views.admin_users_view, name='admin_users'),
    path('admin-portal/admins/add/', views.admin_create_view, name='admin_create'),
    path('admin-portal/reports/', views.admin_reports_view, name='admin_reports'),
]
