from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User



class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address."
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
        
        
class HumanizeForm(forms.Form):
    ai_text = forms.CharField(
        label="AI Text",
        widget=forms.Textarea(attrs={
            'rows': 15,
            'cols': 80,
            'placeholder': 'Enter your AI-generated text here...'
        }),
        help_text='Enter the text you want to humanize. Be patient with load times please.'
    )
