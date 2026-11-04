from .models import UserProfile


def theme_context(request):
    if not request.user.is_authenticated:
        return {'dark_mode': False, 'is_admin': False}

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {
        'dark_mode': profile.dark_mode,
        'is_admin': request.user.is_staff and request.user.email.lower().endswith('@admin.co.za'),
    }
