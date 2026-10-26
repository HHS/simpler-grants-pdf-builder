"""Admin templates and assets must come from the same Django installation."""

from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class AdminAssetTests(SimpleTestCase):
    def test_admin_assets_resolve_to_installed_django(self):
        asset_root = Path(admin.__file__).parent / "static" / "admin"
        for asset in asset_root.rglob("*"):
            if not asset.is_file():
                continue
            name = "admin/" + asset.relative_to(asset_root).as_posix()
            with self.subTest(asset=name):
                resolved = finders.find(name)
                self.assertIsNotNone(resolved)
                self.assertEqual(Path(resolved).resolve(), asset.resolve())

    def test_custom_admin_template_preserves_django_styles(self):
        html = render_to_string("admin/base_site.html", {"is_popup": False})
        self.assertIn("admin/css/base.css", html)
        self.assertIn("admin/css/responsive.css", html)
        self.assertIn("admin/css/dark_mode.css", html)
        self.assertIn(".change-list .constance", html)


class ConstanceBreadcrumbTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            email="admin@example.gov", password=None
        )

    def test_constance_pages_use_django_breadcrumb_markup(self):
        self.client.force_login(self.user)
        for url, labels in (
            (reverse("admin:app_list", args=["constance"]), ["Home", "Constance"]),
            (
                reverse("admin:constance_config_changelist"),
                ["Home", "Constance", "Config"],
            ),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                breadcrumbs = soup.select_one(
                    'nav[aria-label="Breadcrumbs"] > ol.breadcrumbs'
                )
                self.assertIsNotNone(breadcrumbs)
                items = breadcrumbs.find_all("li", recursive=False)
                self.assertEqual([item.get_text(strip=True) for item in items], labels)
                self.assertEqual(items[-1].get("aria-current"), "page")
                self.assertIsNone(items[-1].find("a"))
                self.assertEqual(items[0].a["href"], reverse("admin:index"))
                if len(items) == 3:
                    self.assertEqual(
                        items[1].a["href"],
                        reverse("admin:app_list", args=["constance"]),
                    )
                    self.assertIsNotNone(soup.select_one("#changelist-form"))
                    self.assertIsNotNone(soup.select_one('input[name="_save"]'))
