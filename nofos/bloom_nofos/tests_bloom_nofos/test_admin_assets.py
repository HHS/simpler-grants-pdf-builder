"""Admin templates and assets must come from the same Django installation."""

from pathlib import Path

from django.contrib import admin
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import SimpleTestCase


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
