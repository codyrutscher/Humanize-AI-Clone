# ai_humanizer/models.py
from django.db import models
from django.contrib.auth.models import User

class HumanizedText(models.Model):
    original_text = models.TextField()
    humanized_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription_active = models.BooleanField(default=False)
    plan = models.CharField(max_length=100, blank=True, null=True)
    total_words_generated = models.PositiveIntegerField(default=0)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)  # NEW FIELD

    def __str__(self):
        return f"{self.user.username}'s profile"