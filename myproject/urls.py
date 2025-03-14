from django.contrib import admin
from django.urls import path, include  # Import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ai_humanizer.urls')),  # Replace 'ai_humanizer' with 'core' if that's your app name
]

