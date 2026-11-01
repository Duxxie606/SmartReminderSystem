from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Reminder(models.Model):
    PRIORITY_CHOICES = (
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    )

    IMPORTANCE_CHOICES = (
        (1, '1 - Low Importance'),
        (2, '2 - Low Importance'),
        (3, '3 - Low Importance'),
        (4, '4 - Medium Importance'),
        (5, '5 - High Importance'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    task_name = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    due_date = models.DateField()
    due_time = models.TimeField(null=True, blank=True)
    importance = models.PositiveSmallIntegerField(
        choices=IMPORTANCE_CHOICES,
        default=3,
        help_text='Select importance from 1 (low) to 5 (high).',
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f'{self.task_name} ({self.subject}) - {self.priority}'

    def calculate_priority(self):
        """
        Priority is based only on the selected importance:
        5 = High, 4 = Medium, 1-3 = Low.
        """
        if self.importance == 5:
            return 'High'
        if self.importance == 4:
            return 'Medium'
        return 'Low'

    def days_until_due(self):
        today = timezone.localdate()
        return (self.due_date - today).days

    @property
    def status(self):
        """Current task state used consistently across user and admin pages."""
        if self.is_deleted:
            return 'Cancelled'
        if self.is_completed:
            return 'Completed'
        if self.due_date < timezone.localdate():
            return 'Missed'
        return 'Active'

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'priority'])

    def mark_complete(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at', 'priority'])

    def save(self, *args, **kwargs):
        self.priority = self.calculate_priority()
        super().save(*args, **kwargs)


class StudyPlan(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='study_plans')
    study_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration = models.CharField(max_length=50)
    recommendation = models.CharField(max_length=255)

    class Meta:
        ordering = ['study_date', 'start_time']

    def __str__(self):
        return f'Study Plan for {self.reminder.task_name} on {self.study_date}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    dark_mode = models.BooleanField(default=False)

    def __str__(self):
        return f'Preferences for {self.user.username}'
