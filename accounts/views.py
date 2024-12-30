from django.shortcuts import render, redirect, reverse
from core.models import Subscription
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings


def profile(request):
    if not request.user.is_authenticated:
        return redirect(f'{settings.BASE_URL}{reverse("account_login")}?next={request.get_full_path()}')

    subscriptions = Subscription.objects.filter(user=request.user).first()

    return render(request, 'account/profile.html', {
        'subscriptions': subscriptions,
    })

def check_username(request):
    username = request.GET.get('username')
    user = User.objects.filter(username=username).first()
    if user is not None:
        return HttpResponse('<span class="text-red-500">Username is taken</span>', status=200)
    else:
        return HttpResponse('<span class="text-green-600">Username is available</span>', status=200)