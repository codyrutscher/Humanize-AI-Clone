# ai_humanizer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.humanize_content, name='humanize_content'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('purchase/', views.purchase_subscription, name='purchase_subscription'),
    path('purchase-success/', views.purchase_success, name='purchase_success'),
    path('manage/', views.manage_view, name='manage'),
    path('change-subscription/', views.change_subscription, name='change_subscription'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
