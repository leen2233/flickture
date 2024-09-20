from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from .models import User


class SignUpViewTestCase(APITestCase):
    def test_user_signup(self):
        url = reverse('sign_up')
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')

        # Check if the response status is 201 (Created)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if a token is returned in the response
        self.assertIn('token', response.data)

        # Verify that the user was actually created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'testuser@example.com')

        # Check if the token is created for the user
        token = Token.objects.get(user=user)
        self.assertEqual(response.data['token'], token.key)

    def test_signup_without_email(self):
        url = reverse('sign_up')
        data = {
            'username': 'testuser2',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')

        # Check if the response status is 400 (Bad Request) since email is required
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify that no user is created
        self.assertFalse(User.objects.filter(username='testuser2').exists())


class LoginViewTestCase(APITestCase):
    def setUp(self):
        # Create a user for testing login
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )

    def test_login(self):
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')

        # Check if the response status is 200 (OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if a token is returned in the response
        self.assertIn('token', response.data)

        # Verify the token matches the one associated with the user
        token = Token.objects.get(user=self.user)
        self.assertEqual(response.data['token'], token.key)

    def test_login_invalid_credentials(self):
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')

        # Check if the response status is 400 (Bad Request) for invalid credentials
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check that no token is returned
        self.assertNotIn('token', response.data)
