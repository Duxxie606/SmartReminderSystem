from .models import UserProfile


def theme_context(request):
    if not request.user.is_authenticated:
        return {'dark_mode': False}

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {'dark_mode': profile.dark_mode}
