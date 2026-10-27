import logging
import re
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def generate_valid_username(base_text):
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', base_text or '').strip().lower()
    first_alpha_index = next((i for i, ch in enumerate(cleaned) if ch.isalpha()), None)
    if first_alpha_index is None:
        cleaned = 'user' + cleaned
        first_alpha_index = 0
    cleaned = cleaned[first_alpha_index:]
    if not cleaned:
        cleaned = 'user'

    cleaned = cleaned[:25]
    candidate = cleaned
    suffix = 0
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{cleaned[:25]}{suffix}"
    return candidate.lower()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        base_source = (
            data.get('first_name')
            or data.get('name')
            or (data.get('email', '').split('@')[0] if data.get('email') else 'user')
        )
        user.username = generate_valid_username(base_source)
        if user.email:
            user.email = user.email.strip().lower()
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Handle social login pipeline securely:
        - If already connected (subsequent Google sign-ins), allow login to access the account.
        - If first-time Google sign-in and a local user exists with the same email,
          connect the social account only if the email is verified by Google.
        - Never automatically link accounts based on unverified email addresses.
        - If no local account exists, let Allauth proceed with auto-signup to create the account.
        """
        if sociallogin.is_existing:
            return

        email = None
        is_verified = False

        if sociallogin.email_addresses:
            for ea in sociallogin.email_addresses:
                if ea.email:
                    email = ea.email.strip().lower()
                    is_verified = bool(ea.verified)
                    break

        if not email and sociallogin.account.extra_data:
            extra = sociallogin.account.extra_data
            raw_email = extra.get('email')
            if raw_email:
                email = raw_email.strip().lower()
                is_verified = bool(extra.get('email_verified') or extra.get('verified_email'))

        if not email:
            return

        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            if is_verified:
                sociallogin.connect(request, existing_user)
                EmailAddress.objects.get_or_create(
                    user=existing_user,
                    email=email,
                    defaults={'verified': True, 'primary': True}
                )
            else:
                logger.warning(
                    f"Refusing to auto-link unverified social email {email} to existing user {existing_user.id}"
                )