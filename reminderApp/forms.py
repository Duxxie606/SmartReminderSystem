from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    UserCreationForm,
)
from .models import Reminder


class StudentRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class StudentLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email address',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    def clean(self):
        identifier = self.cleaned_data.get('username', '').strip()
        matched_user = User.objects.filter(email__iexact=identifier).first()
        if matched_user is not None:
            self.cleaned_data['username'] = matched_user.username
        return super().clean()


class AdminLoginForm(AuthenticationForm):
    """Email-only sign-in form for authorised administrator accounts."""

    ADMIN_SUFFIX = '@admin.co.za'

    username = forms.EmailField(
        label='Administrator email address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your administrator email address',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )

    def clean(self):
        email = self.cleaned_data.get('username', '').strip()
        user = User.objects.filter(
            email__iexact=email,
            is_staff=True,
        ).first()
        if user is None or not email.lower().endswith(self.ADMIN_SUFFIX):
            raise ValidationError('Enter a valid administrator email address and password.')

        self.cleaned_data['username'] = user.username
        return super().clean()


class UserPasswordResetForm(PasswordResetForm):
    """Password reset form limited to ordinary user accounts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

    def get_users(self, email):
        return (user for user in super().get_users(email) if not user.is_staff)


class AdminPasswordResetForm(PasswordResetForm):
    """Password reset form limited to valid administrator accounts."""

    ADMIN_SUFFIX = '@admin.co.za'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

    def get_users(self, email):
        return (
            user for user in super().get_users(email)
            if user.is_staff and user.email.lower().endswith(self.ADMIN_SUFFIX)
        )


class ReminderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_time'].required = True
        self.fields['due_time'].input_formats = ['%H:%M']

    class Meta:
        model = Reminder
        fields = ['task_name', 'subject', 'due_date', 'due_time', 'importance']
        widgets = {
            'task_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Database Assignment 2'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Database Systems'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'due_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }, format='%H:%M'),
            'importance': forms.Select(
                attrs={'class': 'form-select'}
            ),
        }
        labels = {
            'task_name': 'Task Name',
            'subject': 'Subject',
            'due_date': 'Due Date',
            'due_time': 'Due Time',
            'importance': 'Importance',
        }


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AdminCreateForm(StudentRegisterForm):
    ADMIN_SUFFIX = '@admin.co.za'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith(self.ADMIN_SUFFIX):
            raise ValidationError('Administrator email addresses must end with @admin.co.za.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
        return user


class AccountPasswordChangeForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
