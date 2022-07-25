from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core import mail
from django.test import override_settings
from django.utils import translation
from django_webtest import TestCase, WebTest
from model_bakery import baker
from unittest.mock import patch
from django.urls import reverse

from evap.evaluation.models import UserProfile
from evap.evaluation.tests.tools import WebTestWith200Check, create_evaluation_with_responsible_and_editor


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TestIndexView(WebTest):
    url = "/"

    @override_settings(ACTIVATE_OPEN_ID_LOGIN=False)
    def test_passworduser_login(self):
        """Tests whether a user can login with an incorrect and a correct password."""
        baker.make(UserProfile, email="password.user", password=make_password("evap"))
        response = self.app.get(self.url)
        password_form = response.forms["email-login-form"]
        password_form["email"] = "password.user"
        password_form["password"] = "asd"  # nosec
        password_form.submit(status=200)
        password_form["password"] = "evap"  # nosec
        password_form.submit(status=302)

    @override_settings(ACTIVATE_OPEN_ID_LOGIN=False)
    def test_login_for_staff_users_correctly_redirects(self):
        """Regression test for #1523: Access denied on manager login"""
        internal_email = (
            "manager@institution.example.com"  # external users don't necessarily have a proper redirect page
        )
        baker.make(
            UserProfile,
            email=internal_email,
            password=make_password("evap"),
            groups=[Group.objects.get(name="Manager")],
        )

        response = self.app.get(self.url)
        password_form = response.forms["email-login-form"]
        password_form["email"] = internal_email
        password_form["password"] = "evap"
        response = password_form.submit()
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertRedirects(response.follow(), "/results/")

    @override_settings(ACTIVATE_OPEN_ID_LOGIN=False)
    def test_login_view_respects_redirect_parameter(self):
        """Regression test for #1658: redirect after login"""
        internal_email = "manager@institution.example.com"
        baker.make(
            UserProfile,
            email=internal_email,
            password=make_password("evap"),
        )

        response = self.app.get(self.url + "?next=/test42/")
        password_form = response.forms["email-login-form"]
        password_form["email"] = internal_email
        password_form["password"] = "evap"
        response = password_form.submit()
        self.assertRedirects(response.follow(), "/test42/", fetch_redirect_response=False)

    def test_send_new_login_key(self):
        """Tests whether requesting a new login key is only possible for existing users,
        shows the expected success message and sends only one email to the requesting
        user without people in cc even if the user has delegates and cc users."""
        baker.make(UserProfile, email="asdf@example.com")
        response = self.app.get(self.url)
        email_form = response.forms["request-login-form"]
        email_form["email"] = "doesnotexist@example.com"
        self.assertIn("No user with this email address was found", email_form.submit())
        email = "asdf@example.com"
        email_form["email"] = email
        self.assertIn("We sent you", email_form.submit().follow())
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].to == [email])
        self.assertEqual(len(mail.outbox[0].cc), 0)


class TestLegalNoticeView(WebTestWith200Check):
    url = "/legal_notice"
    test_users = [""]


class TestFAQView(WebTestWith200Check):
    url = "/faq"
    test_users = [""]


class TestContactEmail(WebTest):
    csrf_checks = False

    def test_sends_mail(self):
        user = baker.make(UserProfile, email="user@institution.example.com")
        self.app.post(
            "/contact",
            params={"message": "feedback message", "title": "some title", "sender_email": "unique@mail.de"},
            user=user,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].reply_to == ["user@institution.example.com"])


class TestChangeLanguageView(WebTest):
    url = "/set_lang"
    csrf_checks = False

    def test_changes_language(self):
        user = baker.make(UserProfile, email="tester@institution.example.com", language="de")

        self.app.post(self.url, params={"language": "en"}, user=user)

        user.refresh_from_db()
        self.assertEqual(user.language, "en")

        translation.activate("en")  # for following tests


class TestProfileView(WebTest):
    url = "/profile"

    @classmethod
    def setUpTestData(cls):
        result = create_evaluation_with_responsible_and_editor()
        cls.responsible = result["responsible"]

    def test_save_settings(self):
        user = baker.make(UserProfile)
        page = self.app.get(self.url, user=self.responsible, status=200)
        form = page.forms["settings-form"]
        form["delegates"] = [user.pk]
        form.submit()

        self.responsible.refresh_from_db()
        self.assertEqual(list(self.responsible.delegates.all()), [user])

    def test_view_settings_as_non_editor(self):
        user = baker.make(UserProfile, email="testuser@example.com")
        page = self.app.get(self.url, user=user, status=200)
        self.assertIn("Personal information", page)
        self.assertNotIn("Delegates", page)
        self.assertIn(user.email, page)


class TestNotebookView(TestCase):
    url = reverse("notebook")
    csrf_checks = True
    note = "Data is so beautiful"

    def test_notebook(self):
        user = baker.make(UserProfile)
        self.client.force_login(user, backend=None)

        response = self.client.post(
            self.url,
            data={"notes": self.note},
            user=user,
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(user.notes, self.note)

    def test_notebook_invalid_request(self):
        user = baker.make(UserProfile)
        self.client.force_login(user, backend=None)

        response = self.client.get(
            self.url,
            data={"notes": self.note},
            user=user,
        )
        self.assertEqual(response.status_code, 405)

    def test_notebook_invalid_form(self):
        user = baker.make(UserProfile)
        self.client.force_login(user, backend=None)

        with patch('evap.evaluation.forms.NotebookForm.is_valid') as mock_profile_form:
            mock_profile_form.return_value = False
            response = self.client.post(
                self.url,
                data={"notes": 42},
                user=user,
            )

            self.assertEqual(response.status_code, 400)