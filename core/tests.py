from django.test import TestCase, override_settings
from django.urls import reverse

BANNER_TEXT = "PROTOTYPE – sample data"


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")

    @override_settings(PROTOTYPE_MODE=True)
    def test_banner_shown_in_prototype_mode(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, BANNER_TEXT)

    @override_settings(PROTOTYPE_MODE=False)
    def test_banner_hidden_outside_prototype_mode(self):
        # Real users must never see the prototype banner in production.
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, BANNER_TEXT)
