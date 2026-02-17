from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        # Allow auto signup
        return True

    def get_login_redirect_url(self, request):
        # ALWAYS redirect to dashboard
        return "/dashboard/"
