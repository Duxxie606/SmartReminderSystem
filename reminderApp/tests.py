from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Reminder, StudyPlan
from .views import generate_study_plan


class ReminderStatusTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user('student', password='Testpass123!')
        self.today = timezone.localdate()

    def create_reminder(self, name, due_date):
        return Reminder.objects.create(
            user=self.student,
            task_name=name,
            subject='Testing',
            due_date=due_date,
            importance=3,
        )

    def test_overdue_task_is_hidden_from_active_list_and_shown_in_reports(self):
        overdue = self.create_reminder('Overdue task', self.today - timedelta(days=1))
        active = self.create_reminder('Active task', self.today)
        self.client.force_login(self.student)

        response = self.client.get(reverse('reminder_list'))
        self.assertContains(response, active.task_name)
        self.assertNotContains(response, overdue.task_name)

        response = self.client.get(reverse('reports'))
        self.assertContains(response, overdue.task_name)
        self.assertContains(response, 'Missed')

    def test_mark_done_hides_task_from_active_list_and_records_completion(self):
        reminder = self.create_reminder('Finish assignment', self.today)
        self.client.force_login(self.student)

        response = self.client.post(reverse('complete_reminder', args=[reminder.pk]))
        self.assertRedirects(response, reverse('reminder_list'))

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_completed)
        self.assertIsNotNone(reminder.completed_at)
        self.assertNotContains(self.client.get(reverse('reminder_list')), reminder.task_name)
        self.assertContains(self.client.get(reverse('reports')), reminder.task_name)

    def test_reports_filter_missed_excludes_active_tasks(self):
        missed = self.create_reminder('Missed task', self.today - timedelta(days=1))
        active = self.create_reminder('Active task', self.today + timedelta(days=2))
        self.client.force_login(self.student)

        response = self.client.get(reverse('reports'), {'status': 'missed'})
        self.assertContains(response, missed.task_name)
        self.assertNotContains(response, active.task_name)
        self.assertEqual(missed.status, 'Missed')
        self.assertEqual(active.status, 'Active')

    def test_study_sessions_have_a_thirty_minute_break_between_them(self):
        high_priority = Reminder.objects.create(
            user=self.student,
            task_name='High priority task',
            subject='Testing',
            due_date=self.today,
            importance=5,
        )
        low_priority = Reminder.objects.create(
            user=self.student,
            task_name='Low priority task',
            subject='Testing',
            due_date=self.today,
            importance=1,
        )
        generate_study_plan(high_priority)
        plans = list(StudyPlan.objects.filter(study_date=self.today))
        self.assertEqual(len(plans), 2)
        first_end = datetime.combine(self.today, plans[0].end_time)
        second_start = datetime.combine(self.today, plans[1].start_time)
        self.assertEqual(second_start - first_end, timedelta(minutes=30))

    def test_user_can_sign_in_with_their_email_address(self):
        self.student.email = 'student@example.com'
        self.student.save()
        response = self.client.post(reverse('login'), {
            'username': 'student@example.com',
            'password': 'Testpass123!',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_settings_save_dark_mode_preference(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('settings'), {
            'action': 'theme',
            'dark_mode': 'on',
        })
        self.assertRedirects(response, reverse('settings'))
        self.student.profile.refresh_from_db()
        self.assertTrue(self.student.profile.dark_mode)


class AdministratorAccessTests(TestCase):
    def test_role_selection_is_public(self):
        response = self.client.get(reverse('role_selection'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator')

    def test_non_staff_account_cannot_sign_in_as_administrator(self):
        user = User.objects.create_user('student@admin.co.za', password='Testpass123!')
        response = self.client.post(reverse('admin_login'), {
            'username': user.username,
            'password': 'Testpass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator sign-in failed')

    def test_staff_account_with_required_suffix_can_access_admin_portal(self):
        admin_user = User.objects.create_user(
            'principal@admin.co.za',
            password='Testpass123!',
            is_staff=True,
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator Portal')

    def test_admin_can_view_users_and_filter_missed_reports(self):
        admin_user = User.objects.create_user(
            'principal@admin.co.za',
            password='Testpass123!',
            is_staff=True,
        )
        user = User.objects.create_user('ordinary_user', password='Testpass123!')
        Reminder.objects.create(
            user=user,
            task_name='Past due task',
            subject='Testing',
            due_date=timezone.localdate() - timedelta(days=1),
            importance=3,
        )
        self.client.force_login(admin_user)

        self.assertContains(self.client.get(reverse('admin_users')), 'ordinary_user')
        response = self.client.get(reverse('admin_reports'), {'status': 'missed'})
        self.assertContains(response, 'Past due task')
        self.assertContains(response, 'Missed')

    def test_admin_can_create_an_administrator_from_the_admin_portal(self):
        admin_user = User.objects.create_user(
            'principal@admin.co.za',
            password='Testpass123!',
            is_staff=True,
        )
        self.client.force_login(admin_user)
        response = self.client.post(reverse('admin_create'), {
            'username': 'coordinator@admin.co.za',
            'email': 'coordinator@example.com',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!',
        })
        self.assertRedirects(response, reverse('admin_users'))
        self.assertTrue(User.objects.get(username='coordinator@admin.co.za').is_staff)

    def test_user_and_admin_password_reset_pages_are_available(self):
        self.assertEqual(self.client.get(reverse('password_reset')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin_password_reset')).status_code, 200)

    def test_password_reset_email_is_limited_to_the_matching_account_type(self):
        user = User.objects.create_user(
            'ordinary_user',
            email='user@example.com',
            password='Testpass123!',
        )
        admin_user = User.objects.create_user(
            'principal@admin.co.za',
            email='admin@example.com',
            password='Testpass123!',
            is_staff=True,
        )

        self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertEqual(len(mail.outbox), 1)

        mail.outbox.clear()
        self.client.post(reverse('password_reset'), {'email': admin_user.email})
        self.assertEqual(len(mail.outbox), 0)

        self.client.post(reverse('admin_password_reset'), {'email': admin_user.email})
        self.assertEqual(len(mail.outbox), 1)
