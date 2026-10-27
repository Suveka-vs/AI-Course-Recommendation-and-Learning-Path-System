import re

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email

from .models import Resume, ROLE_CHOICES

USERNAME_REGEX = re.compile(r'^[a-z][a-z0-9_]{2,29}$')


class RegisterForm(forms.Form):
    username = forms.CharField(
        label='Username', max_length=30, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username', 'placeholder': 'Username'}),
    )
    email = forms.CharField(
        label='Email', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'Email'}),
    )
    password1 = forms.CharField(
        label='Password', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password', 'placeholder': '••••••••••••'}),
    )
    password2 = forms.CharField(
        label='Confirm Password', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password', 'placeholder': '••••••••••••'}),
    )

    def clean_username(self):
        raw_username = self.cleaned_data.get('username', '')
        username = raw_username.strip().lower()
        if not username:
            raise forms.ValidationError('Username is required.')
        if username[0].isdigit():
            raise forms.ValidationError('Username cannot start with a number.')
        if not username[0].isalpha():
            raise forms.ValidationError('Username cannot start with a symbol.')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        if not USERNAME_REGEX.match(username):
            raise forms.ValidationError('Username can contain only letters, numbers, and underscore.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken. Please choose another username.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Email is required.')
        try:
            validate_email(email)
        except forms.ValidationError:
            raise forms.ValidationError('Enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1', '')
        if not password1:
            raise forms.ValidationError('Password is required.')
        raw_username = self.cleaned_data.get('username') or self.data.get('username', '')
        norm_username = raw_username.strip().lower() if raw_username else ''
        raw_email = self.cleaned_data.get('email') or self.data.get('email', '')
        norm_email = raw_email.strip().lower() if raw_email else ''
        temp_user = User(username=norm_username, email=norm_email)
        try:
            password_validation.validate_password(password1, user=temp_user)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2', '')
        if not password2:
            self.add_error('password2', 'Confirm Password is required.')
        elif password1 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username', 'placeholder': 'Username', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Password', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password', 'placeholder': '••••••••••••'}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Invalid username or password.',
        'inactive': 'This account is inactive.',
    }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username is required.')
        return username.lower()

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise forms.ValidationError('Password is required.')
        return password

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            # If standard authentication with normalized lowercase username failed,
            # fallback to check if a user exists with case-insensitive match (for existing legacy uppercase usernames)
            if self.user_cache is None:
                existing_user = User.objects.filter(username__iexact=username).first()
                if existing_user and existing_user.username != username:
                    self.user_cache = authenticate(
                        self.request, username=existing_user.username, password=password
                    )

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']
        widgets = {'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.docx'})}

    def clean_file(self):
        file = self.cleaned_data['file']
        name = file.name.lower()
        if not (name.endswith('.pdf') or name.endswith('.docx')):
            raise forms.ValidationError('Only PDF or DOCX files are allowed.')
        max_size_mb = 5
        if file.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f'File size must be under {max_size_mb} MB.')
        return file


class ManualSkillForm(forms.Form):
    skills_text = forms.CharField(
        label='Your Skills',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'e.g. Python, Django, SQL, HTML, CSS, Git'}),
        help_text='Separate skills with commas.',
    )


class TargetRoleForm(forms.Form):
    role_choice = forms.ChoiceField(
        label='Target Job Role', choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    custom_role = forms.CharField(
        label='Custom Role', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cloud Security Engineer'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        role_choice = cleaned_data.get('role_choice')
        custom_role = cleaned_data.get('custom_role', '').strip()
        if role_choice == 'other' and not custom_role:
            self.add_error('custom_role', 'Please enter your custom role.')
        return cleaned_data