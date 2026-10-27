from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from recommender.adapters import CustomSocialAccountAdapter, generate_valid_username


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='testuser_1',
            email='testuser@example.com',
            password='ValidPassword123!'
        )

    def test_login_page_renders_elements(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('SkillPath AI', content)
        self.assertIn('Welcome Back', content)
        self.assertIn('Continue your learning journey', content)
        self.assertNotIn('Continue with Google', content)
        self.assertIn('password-toggle-btn', content)
        self.assertIn('fa-solid fa-user', content)
        self.assertIn('fa-solid fa-lock', content)

    def test_login_empty_fields_validation(self):
        response = self.client.post(reverse('login'), {'username': '', 'password': ''})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Username is required.', content)
        self.assertIn('Password is required.', content)

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {'username': 'testuser_1', 'password': 'WrongPassword123!'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Invalid username or password.', content)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {'username': 'testuser_1', 'password': 'ValidPassword123!'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_case_insensitivity_with_uppercase_input(self):
        # User in DB is 'testuser_1', input is 'Testuser_1'
        response = self.client.post(reverse('login'), {'username': 'Testuser_1', 'password': 'ValidPassword123!'})
        self.assertRedirects(response, reverse('dashboard'))

        # Input in ALL CAPS 'TESTUSER_1'
        response_caps = self.client.post(reverse('login'), {'username': 'TESTUSER_1', 'password': 'ValidPassword123!'})
        self.assertRedirects(response_caps, reverse('dashboard'))

    def test_login_fallback_with_legacy_uppercase_user_in_db(self):
        # Create legacy user with uppercase in username
        User.objects.create_user(
            username='LegacyUser_9',
            email='legacy@example.com',
            password='LegacyPass123!'
        )
        # Login with lowercase input
        res1 = self.client.post(reverse('login'), {'username': 'legacyuser_9', 'password': 'LegacyPass123!'})
        self.assertRedirects(res1, reverse('dashboard'))

        # Login with mixed case input
        res2 = self.client.post(reverse('login'), {'username': 'LegacyUser_9', 'password': 'LegacyPass123!'})
        self.assertRedirects(res2, reverse('dashboard'))

    def test_register_page_renders_elements(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('SkillPath AI', content)
        self.assertIn('Create Your Account', content)
        self.assertIn('Start your personalized learning journey', content)
        self.assertNotIn('Continue with Google', content)
        self.assertIn('data-target="id_password1"', content)
        self.assertIn('data-target="id_password2"', content)
        self.assertIn('fa-solid fa-user', content)
        self.assertIn('fa-solid fa-envelope', content)
        self.assertIn('fa-solid fa-lock', content)

    def test_register_username_validation(self):
        # Case 1: starts with a number
        res1 = self.client.post(reverse('register'), {
            'username': '1suveka', 'email': 'suveka1@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('Username cannot start with a number.', res1.content.decode('utf-8'))

        # Case 2: starts with a symbol
        res2 = self.client.post(reverse('register'), {
            'username': '@suveka', 'email': 'suveka2@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('Username cannot start with a symbol.', res2.content.decode('utf-8'))

        # Case 3: contains invalid characters
        res3 = self.client.post(reverse('register'), {
            'username': 'Suveka-Dev', 'email': 'suveka3@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('Username can contain only letters, numbers, and underscore.', res3.content.decode('utf-8'))

        # Case 4: too short
        res4 = self.client.post(reverse('register'), {
            'username': 'Su', 'email': 'suveka4@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('Username must be at least 3 characters long.', res4.content.decode('utf-8'))

    def test_register_username_automatically_normalized_to_lowercase(self):
        # User registers with uppercase letters in username
        res = self.client.post(reverse('register'), {
            'username': 'SuVeKa_DeV', 'email': 'suveka_dev@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertRedirects(res, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='suveka_dev').exists())
        self.assertFalse(User.objects.filter(username='SuVeKa_DeV').exclude(username='suveka_dev').exists())

    def test_register_duplicate_username_case_insensitive(self):
        # 'testuser_1' is already in DB; registering with 'Testuser_1' or 'TESTUSER_1' should be rejected
        res_dup_user = self.client.post(reverse('register'), {
            'username': 'Testuser_1', 'email': 'other@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('This username is already taken. Please choose another username.', res_dup_user.content.decode('utf-8'))

        res_dup_email = self.client.post(reverse('register'), {
            'username': 'newuser_1', 'email': 'TESTUSER@example.com',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!'
        })
        self.assertIn('An account with this email already exists.', res_dup_email.content.decode('utf-8'))

    def test_register_password_mismatch(self):
        res = self.client.post(reverse('register'), {
            'username': 'newuser_1', 'email': 'newuser@example.com',
            'password1': 'StrongPass123!', 'password2': 'DifferentPass123!'
        })
        self.assertIn('Passwords do not match.', res.content.decode('utf-8'))

    def test_register_success(self):
        res = self.client.post(reverse('register'), {
            'username': 'Validuser_1', 'email': 'validuser@example.com',
            'password1': 'SuperSecurePass123!', 'password2': 'SuperSecurePass123!'
        })
        self.assertRedirects(res, reverse('dashboard'))
        # Username must be normalized to lowercase
        self.assertTrue(User.objects.filter(username='validuser_1').exists())


class SocialAccountAdapterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = CustomSocialAccountAdapter()
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='StrongPassword123!'
        )

    def test_generate_valid_username(self):
        self.assertEqual(generate_valid_username('John Doe'), 'johndoe')
        self.assertEqual(generate_valid_username('12345'), 'user12345')
        self.assertEqual(generate_valid_username(''), 'user')
        self.assertTrue(generate_valid_username('existinguser').startswith('existinguser'))
        self.assertNotEqual(generate_valid_username('existinguser'), 'existinguser')

    def test_pre_social_login_connects_verified_existing_user(self):
        request = self.factory.get('/accounts/google/login/callback/')
        account = SocialAccount(provider='google', uid='123456789')
        email_address = EmailAddress(email='existing@example.com', verified=True, primary=True)
        sociallogin = SocialLogin(account=account, email_addresses=[email_address])

        self.assertFalse(sociallogin.is_existing)
        self.adapter.pre_social_login(request, sociallogin)

        # Should be linked to existing_user
        self.assertTrue(sociallogin.is_existing)
        self.assertEqual(sociallogin.user, self.existing_user)
        # Verify password is preserved and intact
        self.assertTrue(self.existing_user.has_usable_password())
        self.assertTrue(self.existing_user.check_password('StrongPassword123!'))

    def test_pre_social_login_refuses_unverified_email_linking(self):
        request = self.factory.get('/accounts/google/login/callback/')
        account = SocialAccount(provider='google', uid='987654321')
        email_address = EmailAddress(email='existing@example.com', verified=False, primary=True)
        sociallogin = SocialLogin(account=account, email_addresses=[email_address])

        self.assertFalse(sociallogin.is_existing)
        self.adapter.pre_social_login(request, sociallogin)

        # Must NOT auto-connect unverified email
        self.assertFalse(sociallogin.is_existing)
        self.assertNotEqual(sociallogin.user, self.existing_user)

    def test_pre_social_login_skips_when_already_existing(self):
        request = self.factory.get('/accounts/google/login/callback/')
        account = SocialAccount.objects.create(
            user=self.existing_user, provider='google', uid='55555'
        )
        sociallogin = SocialLogin(account=account, user=self.existing_user)
        self.assertTrue(sociallogin.is_existing)

        # Should return without modifying anything
        self.adapter.pre_social_login(request, sociallogin)
        self.assertTrue(sociallogin.is_existing)
        self.assertEqual(sociallogin.user, self.existing_user)

    def test_populate_user_normalizes_username_and_email(self):
        request = self.factory.get('/accounts/google/login/callback/')
        account = SocialAccount(provider='google', uid='99999')
        sociallogin = SocialLogin(account=account)
        sociallogin.user = User()

        data = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'Alice.Smith@Example.COM',
        }
        populated_user = self.adapter.populate_user(request, sociallogin, data)
        self.assertEqual(populated_user.username, 'alice')
        self.assertEqual(populated_user.email, 'alice.smith@example.com')


