from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('payment_successful/', views.payment_successful, name='payment_successful'),
    path('payment_cancelled/', views.payment_cancel, name='payment_cancelled'),
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('create/', views.create_subscription, name='create_subscription'),
    path('cancel_subs/<subscription_id>/', views.cancel_subscription, name='cancel_subscription'),\
    path('pricing/', views.pricing, name='pricing'),
]