# ai_humanizer/views.py
import openai
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import HumanizeForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
import stripe
from .models import Profile
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse






# Set the API key from settings
openai.api_key = settings.OPENAI_API_KEY

stripe.api_key = settings.STRIPE_SECRET_KEY  # Set your secret key

def test_humanize(ai_text, iterations=3, n=4):
    """
    Uses OpenAI's ChatCompletion API to 'humanize' AI-generated text while maintaining
    the original topic, style, and context.
    """
    import statistics
    import random
    from string import punctuation

    current_text = ai_text
    base_temperature = random.uniform(0.85, 0.95)

    # Prompt templates focused on maintaining topic while adding human elements
    prompt_templates = [
        (
            "Rewrite this text to sound more naturally human while keeping the exact same topic, "
            "meaning, and level of expertise. Make these subtle changes:\n"
            "1. Keep all technical terms and key concepts exactly as they are\n"
            "2. Add natural language patterns like:\n"
            "   - Occasional contractions (e.g., 'it's', 'don't')\n"
            "   - Varied sentence lengths\n"
            "   - A few transition words ('however', 'basically', 'in other words')\n"
            "3. Include 1-2 minor human quirks like:\n"
            "   - A thoughtful pause ('...')\n"
            "   - A parenthetical aside\n"
            "   - Starting a sentence with 'And' or 'But'\n\n"
            "{input_text}"
        ),
        (
            "Maintain the exact same topic and information, but rewrite it as if a knowledgeable "
            "human expert wrote it in a slightly casual setting. Include:\n"
            "1. Keep all subject matter and technical accuracy\n"
            "2. Add subtle human elements:\n"
            "   - Mix of formal terms and natural phrasing\n"
            "   - Occasional first-person perspective ('I think', 'in my experience')\n"
            "   - One or two conversational asides\n"
            "3. Vary the writing flow with:\n"
            "   - Different sentence structures\n"
            "   - Natural transitions\n"
            "   - Occasional emphasis (italics or important points)\n\n"
            "{input_text}"
        ),
        (
            "Rewrite this text to sound like an expert wrote it casually, while keeping "
            "all information and meaning identical. Make these changes:\n"
            "1. Preserve all technical content and accuracy\n"
            "2. Add natural writing elements:\n"
            "   - Brief explanatory asides\n"
            "   - Varied punctuation (including some informal usage)\n"
            "   - Occasional rhetorical questions\n"
            "3. Include subtle human touches:\n"
            "   - A personal example or anecdote\n"
            "   - Natural word repetition\n"
            "   - Conversational transitions\n\n"
            "{input_text}"
        ),
    ]

    def score_candidate(text):
        words = text.split()
        word_count = len(words)
        
        # Split into sentences
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        
        # Calculate metrics
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        
        # Scoring factors
        diversity_score = statistics.stdev(sentence_lengths) if len(sentences) > 1 else 0
        contraction_count = sum(1 for word in words if "'" in word)
        punctuation_variety = len(set(c for c in text if c in punctuation))
        
        # Look for natural language patterns
        transition_words = {'however', 'therefore', 'moreover', 'basically', 'actually', 'essentially'}
        transition_count = sum(1 for word in words if word.lower() in transition_words)
        
        # Combine scores with weights
        return (
            word_count * 1.0 +
            diversity_score * 2.5 +
            contraction_count * 2.0 +
            punctuation_variety * 1.5 +
            transition_count * 3.0 -
            (abs(avg_word_length - 5.2) * 4.0)  # Allow slightly higher word length for technical content
        )

    for i in range(iterations):
        temp = base_temperature - (0.08 * i)
        prompt_template = random.choice(prompt_templates)
        prompt = prompt_template.format(input_text=current_text)
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert writer who maintains technical accuracy while writing in a natural, "
                          "human style. Keep the exact same topic, meaning, and expertise level while making the "
                          "writing style more natural and human-like."
            },
            {"role": "user", "content": prompt}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=2000,
            temperature=temp,
            presence_penalty=0.4,
            frequency_penalty=0.6,
            n=n
        )
        
        completions = [choice.message.content.strip() for choice in response.choices]
        scores = [score_candidate(candidate) for candidate in completions]
        current_text = completions[scores.index(max(scores))]

    return current_text

def humanize_content(request):
    """
    View for the home page that accepts AI-generated text, returns a humanized version,
    updates the user's word tally (if logged in), and displays word counts.
    """
    output = None
    original_word_count = 0
    humanized_word_count = 0
    form = HumanizeForm(request.POST or None)
    
    if request.method == "POST" and form.is_valid():
        ai_text = form.cleaned_data.get("ai_text")
        input_word_count = len(ai_text.split())
        original_word_count = input_word_count
        
        # If the user is logged in, enforce word limit
        if request.user.is_authenticated:
            profile, created = Profile.objects.get_or_create(user=request.user)
            # Define maximum words allowed per plan
            plan_max_words = {
                "plan_10": 50000,
                "plan_15": 100000,
                "plan_20": 300000,
            }
            max_allowed = plan_max_words.get(profile.plan, 0)
            if max_allowed and profile.total_words_generated + input_word_count > max_allowed:
                messages.error(request, "You have exceeded your allowed word limit. Please upgrade your subscription.")
                return redirect("humanize_content")
        
        # Process the text with the AI model
        try:
            output = test_humanize(ai_text)
            if output:
                humanized_word_count = len(output.split())
            # If logged in, update the total word count
            if request.user.is_authenticated:
                profile.total_words_generated += input_word_count
                profile.save()
        except Exception as e:
            output = f"An error occurred: {str(e)}"
    
    context = {
        "form": form,
        "output": output,
        "original_word_count": original_word_count,
        "humanized_word_count": humanized_word_count,
    }
    return render(request, "ai_humanizer/index.html", context)


def pricing_view(request):
    
    
    
    return render(request, "ai_humanizer/pricing.html")





def purchase_subscription(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method == "POST":
        plan_id = request.POST.get("plan_id")

        price_mapping = {
            "plan_10": "price_1QTeQOKxKjsfO43l9gqDBkyu",
            "plan_15": "price_1QTeQOKxKjsfO43l9gqDBkyu",
            "plan_20": "price_1QTeQOKxKjsfO43l9gqDBkyu",
        }

        if plan_id not in price_mapping:
            messages.error(request, "Invalid plan selected.")
            return redirect("pricing")

        # Store the internal plan id in the session
        request.session["plan_id"] = plan_id

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{
                    "price": price_mapping[plan_id],
                    "quantity": 1,
                }],
                success_url=request.build_absolute_uri(
                    reverse("purchase_success")
                ) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("pricing")),
                customer_email=request.user.email,
            )
        except Exception as e:
            messages.error(request, f"Error creating checkout session: {str(e)}")
            return redirect("pricing")

        return redirect(checkout_session.url)
    else:
        messages.error(request, "Please select a plan to purchase.")
        return redirect("pricing")


def purchase_success(request):
    if not request.user.is_authenticated:
        return redirect("login")

    session_id = request.GET.get("session_id", "")
    # Optionally retrieve session details:
    # session = stripe.checkout.Session.retrieve(session_id)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.subscription_active = True
    # Retrieve the plan id from the session (default to "plan_10" if not found)
    profile.plan = request.session.get("plan_id", "plan_10")
    # Optionally, clear the plan id from the session after use:
    if "plan_id" in request.session:
        del request.session["plan_id"]
    profile.save()

    messages.success(request, "Your subscription is now active!")
    return redirect("manage")



def manage_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    plan_max_words = {
        "plan_10": 50000,
        "plan_15": 100000,
        "plan_20": 300000,
    }
    max_allowed = plan_max_words.get(profile.plan, 0)
    words_used = profile.total_words_generated
    words_remaining = max_allowed - words_used if max_allowed > words_used else 0
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "change_plan":
            new_plan = request.POST.get("plan")
            profile.plan = new_plan
            profile.subscription_active = True
            profile.save()
            messages.success(request, "Your plan has been changed successfully.")
        elif action == "cancel_subscription":
            profile.subscription_active = False
            profile.save()
            messages.success(request, "Your subscription has been cancelled.")
        return redirect("manage")
    
    available_plans = [
        {"name": "$10/month", "words": "Up to 50,000 words", "plan_id": "plan_10"},
        {"name": "$15/month", "words": "Up to 100,000 words", "plan_id": "plan_15"},
        {"name": "$20/month", "words": "Up to 300,000 words", "plan_id": "plan_20"},
    ]
    
    context = {
        "current_plan": profile.plan,
        "total_words_generated": profile.total_words_generated,
        "subscription_active": profile.subscription_active,
        "available_plans": available_plans,
        "max_allowed": max_allowed,
        "words_used": words_used,
        "words_remaining": words_remaining,
    }
    return render(request, "ai_humanizer/manage.html", context)




def change_subscription(request):
    """
    Change the user's subscription plan using their current Stripe subscription.
    Expects a POST request with a 'plan' field corresponding to an internal plan id
    (e.g., "plan_10", "plan_15", or "plan_20").
    """
    if not request.user.is_authenticated:
        return redirect("login")
    
    if request.method == "POST":
        new_plan = request.POST.get("plan")
        # Map internal plan ids to Stripe Price IDs
        price_mapping = {
            "plan_10": "price_1QTeQOKxKjsfO43l9gqDBkyu",  # Replace with actual Stripe Price ID for $10/month
            "plan_15": "price_1QTeQOKxKjsfO43l9gqDBkyu",  # Replace with actual Stripe Price ID for $15/month
            "plan_20": "price_1QTeQOKxKjsfO43l9gqDBkyu",  # Replace with actual Stripe Price ID for $20/month
        }
        
        if new_plan not in price_mapping:
            messages.error(request, "Invalid plan selected.")
            return redirect("manage")
        
        # Retrieve or create the user's profile
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        if not profile.stripe_subscription_id:
            messages.error(request, "No active subscription found. Please purchase a subscription first.")
            return redirect("pricing")
        
        try:
            # Retrieve the current subscription from Stripe
            subscription = stripe.Subscription.retrieve(profile.stripe_subscription_id)
            # Assume there is at least one subscription item in the subscription
            if subscription["items"]["data"]:
                subscription_item_id = subscription["items"]["data"][0]["id"]
                # Update the subscription item with the new price
                stripe.Subscription.modify(
                    profile.stripe_subscription_id,
                    items=[{
                        "id": subscription_item_id,
                        "price": price_mapping[new_plan],
                    }]
                )
                # Update the local profile to reflect the new plan
                profile.plan = new_plan
                profile.save()
                messages.success(request, "Your subscription plan has been updated successfully.")
            else:
                messages.error(request, "Unable to retrieve subscription details.")
        except Exception as e:
            messages.error(request, f"Error updating subscription: {str(e)}")
        
        return redirect("manage")
    else:
        return redirect("manage")

    
    
def signup_view(request):
    """
    View for user signup using CustomUserCreationForm.
    """
    from .forms import CustomUserCreationForm  # Import the custom form
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("humanize_content")
        else:
            messages.error(request, "Signup failed. Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, "ai_humanizer/signup.html", {"form": form})


def login_view(request):
    """
    View for user login using Django's AuthenticationForm.
    """
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("humanize_content")
        else:
            messages.error(request, "Login failed. Please check your username and password.")
    else:
        form = AuthenticationForm()
    return render(request, "ai_humanizer/login.html", {"form": form})

def logout_view(request):
    """
    View to log the user out.
    """
    logout(request)
    return redirect("humanize_content")



