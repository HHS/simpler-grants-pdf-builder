"""Connected synthetic host contracts, including unchanged existing Builder paths."""

import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos import design_pilot_host as host
from nofos.design_candidate import DesignRequestError
from nofos.models import DesignPilotCandidate, Nofo
from nofos.tests_nofos.test_editable_introduction import fy27_docx
from nofos.word_readability import word_html


class LocalProfileConfigurationTests(SimpleTestCase):
    def run_profile(self, root, **environment):
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=settings.BASE_DIR,
            env={
                "PATH": "/usr/bin:/bin",
                "DJANGO_SETTINGS_MODULE": "bloom_nofos.design_pilot_settings",
                "DESIGN_PILOT_ROOT": str(root),
                **environment,
            },
            capture_output=True,
            timeout=30,
        )

    def test_clean_private_profile_starts_and_rejects_ambient_credentials(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.run_profile(root).returncode, 0)
            rejected = self.run_profile(root, AWS_ACCESS_KEY_ID="invented-test-only")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"clean environment", rejected.stderr)

    def test_public_root_and_linked_database_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            path.chmod(0o755)
            self.assertNotEqual(self.run_profile(root).returncode, 0)
            path.chmod(0o700)
            (path / "candidate.sqlite3").symlink_to(path / "outside.sqlite3")
            self.assertNotEqual(self.run_profile(root).returncode, 0)


class ConnectedDesignPilotTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.profile = override_settings(
            DESIGN_PILOT_ENABLED=True,
            DESIGN_PILOT_ROOT=self.directory.name,
            DEBUG=False,
            DOCRAPTOR_API_KEY="",
        )
        self.profile.enable()
        self.addCleanup(self.profile.disable)
        self.inputs = patch.object(
            host, "_render_inputs", return_value="synthetic-render-v1"
        )
        self.inputs.start()
        self.addCleanup(self.inputs.stop)
        self.user = BloomUser.objects.create_user(
            email="owner@example.com", password="synthetic", group="bloom"
        )
        self.other = BloomUser.objects.create_user(
            email="other@example.com", password="synthetic", group="bloom"
        )
        self.client.force_login(self.user)
        stream = BytesIO()
        with ZipFile(BytesIO(fy27_docx())) as original, ZipFile(stream, "w") as archive:
            for item in original.infolist():
                data = original.read(item.filename)
                if item.filename == "word/document.xml":
                    data = data.replace(
                        b"Distinctive source text",
                        b"Notice of funding opportunity. Assistance listing: 93.123. HHS. Distinctive source text",
                    )
                archive.writestr(item, data)
        self.source = stream.getvalue()

    def upload(self):
        return SimpleUploadedFile(
            "synthetic.docx", self.source, content_type=host.WORD_TYPE
        )

    def candidate(self):
        return host.import_candidate(self.user, self.upload())

    def command(self, run):
        return {
            "candidate_id": str(run.pk),
            "expected_revision": host.review_artifact(run)[0],
            "operation": "set_table_width",
            "section_id": str(run.nofo.sections.first().pk),
            "value": True,
            "reason": "Make the synthetic table easier to read.",
        }

    def test_real_import_retry_and_revision_bound_html(self):
        run = self.candidate()
        self.assertEqual(bytes(run.source_bytes), self.source)
        self.assertEqual(self.candidate().pk, run.pk)
        self.assertEqual(Nofo.objects.count(), 1)
        revision, html = host.review_artifact(run)
        self.assertIn("Distinctive source text", html)
        self.assertNotIn("<script", html)
        response = self.client.get(
            reverse("design_pilot:document", args=[run.pk]), {"revision": revision}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertEqual(
            self.client.get(reverse("design_pilot:review", args=[run.pk])).status_code,
            200,
        )

    def test_update_preserves_content_and_rejects_old_html_and_retry(self):
        run = self.candidate()
        command = self.command(run)
        old_content = run.content_json
        updated = host.update_candidate(self.user, run.pk, command)
        self.assertEqual(updated.sequence, 1)
        self.assertEqual(updated.content_json, old_content)
        self.assertEqual(host.snapshot(updated).sequence, 1)
        self.assertEqual(
            self.client.get(
                reverse("design_pilot:document", args=[run.pk]),
                {"revision": command["expected_revision"]},
            ).status_code,
            409,
        )
        with self.assertRaises(DesignRequestError):
            host.update_candidate(self.user, run.pk, command)

    def theme_command(self, run, theme):
        command = self.command(run)
        command.pop("section_id")
        command.update(operation="set_theme", value=theme)
        return command

    def test_group_policy_uses_authenticated_owner_not_imported_opdiv(self):
        self.user.group = "cdc"
        self.user.save(update_fields=["group"])
        run = self.candidate()  # Source metadata still describes HRSA.
        choices = host.candidate_capabilities(self.user, run)["choices"]["theme"]
        self.assertIn("portrait-cdc-blue", choices)
        self.assertNotIn("portrait-hrsa-white", choices)
        self.assertNotIn("portrait-nih-white", choices)
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertEqual(response.context["choices"]["theme"], choices)
        self.assertContains(response, "Choose a permitted theme")
        before = (run.revision, run.presentation_json, run.content_json)
        with self.assertRaises(DesignRequestError):
            host.update_candidate(
                self.user, run.pk, self.theme_command(run, "portrait-hrsa-white")
            )
        run.refresh_from_db()
        self.assertEqual(
            before, (run.revision, run.presentation_json, run.content_json)
        )
        updated = host.update_candidate(
            self.user, run.pk, self.theme_command(run, "portrait-cdc-blue")
        )
        self.assertEqual(updated.nofo.theme, "portrait-cdc-blue")
        self.assertEqual(updated.content_json, before[2])

    def test_nih_theme_policy_and_stale_membership_fail_closed(self):
        self.user.group = "nih"
        self.user.save(update_fields=["group"])
        run = self.candidate()
        self.assertEqual(
            host.candidate_capabilities(self.user, run)["choices"]["theme"],
            ["portrait-nih-white"],
        )
        command = self.theme_command(run, "portrait-cdc-blue")
        with self.assertRaises(DesignRequestError):
            host.update_candidate(self.user, run.pk, command)
        BloomUser.objects.filter(pk=self.user.pk).update(group="bloom")
        with self.assertRaises(Http404):
            host.candidate_capabilities(self.user, run)
        with self.assertRaises(Http404):
            host.update_candidate(self.user, run.pk, command)

    def test_retired_theme_can_be_kept_but_not_reselected(self):
        suggest = host.suggest_all_nofo_fields

        def legacy_import(nofo, *args, **kwargs):
            suggest(nofo, *args, **kwargs)
            nofo.theme = "portrait-hrsa-blue"

        with patch.object(host, "suggest_all_nofo_fields", side_effect=legacy_import):
            run = self.candidate()
        self.assertEqual(run.nofo.theme, "portrait-hrsa-blue")
        choices = host.candidate_capabilities(self.user, run)["choices"]["theme"]
        self.assertIn(run.nofo.theme, choices)
        self.assertNotIn("landscape-cdc-blue", choices)
        self.assertNotIn("landscape-cdc-white", choices)
        kept = host.update_candidate(
            self.user, run.pk, self.theme_command(run, run.nofo.theme)
        )
        self.assertEqual(kept.sequence, 0)
        changed = host.update_candidate(
            self.user, run.pk, self.theme_command(run, "portrait-hrsa-white")
        )
        self.assertNotIn(
            "portrait-hrsa-blue",
            host.candidate_capabilities(self.user, changed)["choices"]["theme"],
        )
        with self.assertRaises(DesignRequestError):
            host.update_candidate(
                self.user, run.pk, self.theme_command(changed, "portrait-hrsa-blue")
            )

    def test_resulting_theme_cover_policy_is_reused_without_mutating_document(self):
        run = self.candidate()
        original_theme = run.nofo.theme
        real_form = host.NofoThemeOptionsForm

        def restricted_form(*args, **kwargs):
            form = real_form(*args, **kwargs)
            if kwargs["data"]["theme"] == "portrait-cdc-blue":
                form.fields["cover"].choices = [("unavailable-cover", "Unavailable")]
            return form

        with patch.object(host, "NofoThemeOptionsForm", side_effect=restricted_form):
            self.assertNotIn(
                "portrait-cdc-blue",
                host.candidate_capabilities(self.user, run)["choices"]["theme"],
            )
            with self.assertRaises(DesignRequestError):
                host.update_candidate(
                    self.user, run.pk, self.theme_command(run, "portrait-cdc-blue")
                )
        run.nofo.refresh_from_db()
        self.assertEqual(run.nofo.theme, original_theme)
        host.snapshot(run)

    def test_same_group_other_owner_cannot_read_or_change(self):
        run = self.candidate()
        with self.assertRaises(Http404):
            host.owned_candidate(self.other, run.pk)
        with self.assertRaises(Http404):
            host.update_candidate(self.other, run.pk, self.command(run))
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("design_pilot:review", args=[run.pk])).status_code,
            404,
        )

    def test_group_revocation_and_external_content_changes_fail_closed(self):
        run = self.candidate()
        self.assertEqual(run.nofo.group, "bloom")  # Not the Word file's HRSA metadata.
        BloomUser.objects.filter(pk=self.user.pk).update(group="hrsa")
        with self.assertRaises(Http404):
            host.owned_candidate(self.user, run.pk)
        Nofo.objects.filter(pk=run.nofo.pk).update(title="Outside edit")
        run.refresh_from_db()
        with self.assertRaises(DesignRequestError):
            host.review_artifact(run)

    def test_render_inputs_changes_invalidate_design_request(self):
        run = self.candidate()
        command = self.command(run)
        with patch.object(host, "_render_inputs", return_value="synthetic-render-v2"):
            with self.assertRaises(DesignRequestError):
                host.update_candidate(self.user, run.pk, command)

    def test_render_failure_rolls_back_import_and_update(self):
        with patch.object(
            host, "_safe_document", side_effect=DesignRequestError("Synthetic failure")
        ):
            with self.assertRaises(DesignRequestError):
                self.candidate()
        self.assertEqual(Nofo.objects.count(), 0)
        self.assertEqual(DesignPilotCandidate.objects.count(), 0)
        run = self.candidate()
        command = self.command(run)
        real_render = host._safe_document
        count = 0

        def fail_second(nofo):
            nonlocal count
            count += 1
            if count == 2:
                raise DesignRequestError("Synthetic failure")
            return real_render(nofo)

        with patch.object(host, "_safe_document", side_effect=fail_second):
            with self.assertRaises(DesignRequestError):
                host.update_candidate(self.user, run.pk, command)
        run.refresh_from_db()
        self.assertEqual(run.sequence, 0)
        host.snapshot(run)

    def test_disabled_by_default_and_rejects_pdf_or_acceptance(self):
        with override_settings(DESIGN_PILOT_ENABLED=False):
            self.assertEqual(
                self.client.get(reverse("design_pilot:index")).status_code, 404
            )
        run = self.candidate()
        for op in ("render_pdf", "accept", "fetch", "set_cover"):
            command = self.command(run)
            command["operation"] = op
            with self.assertRaises(DesignRequestError):
                host.update_candidate(self.user, run.pk, command)
        run.refresh_from_db()
        self.assertEqual(run.sequence, 0)

    def test_invalid_upload_and_csrf(self):
        with self.assertRaises(ValidationError):
            host.import_candidate(
                self.user, SimpleUploadedFile("fake.docx", b"Not a Word file")
            )
        self.assertEqual(Nofo.objects.count(), 0)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(
            client.post(
                reverse("design_pilot:index"),
                {"synthetic": "yes", "source": self.upload()},
            ).status_code,
            403,
        )

    def test_form_round_trip_and_local_route_boundary(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        from nofos.design_pilot_views import LocalPilotBoundary

        response = self.client.post(
            reverse("design_pilot:index"), {"synthetic": "yes", "source": self.upload()}
        )
        self.assertEqual(response.status_code, 302)
        run = DesignPilotCandidate.objects.get()
        command = self.command(run)
        command["value"] = "true"
        self.assertEqual(
            self.client.post(
                reverse("design_pilot:operation", args=[run.pk]), command
            ).status_code,
            302,
        )
        boundary = LocalPilotBoundary(lambda request: HttpResponse("allowed"))
        factory = RequestFactory()
        self.assertEqual(
            boundary(factory.get("/nofos/", REMOTE_ADDR="127.0.0.1")).status_code, 404
        )
        self.assertEqual(
            boundary(
                factory.get("/design-pilot/", REMOTE_ADDR="192.0.2.1")
            ).status_code,
            404,
        )
        self.assertEqual(
            boundary(
                factory.get("/design-pilot/", REMOTE_ADDR="127.0.0.1")
            ).status_code,
            200,
        )

    def test_bound_source_and_failed_compare_and_swap(self):
        run = self.candidate()
        command = self.command(run)
        from django.db.models.query import QuerySet

        with patch.object(QuerySet, "update", return_value=0):
            with self.assertRaises(DesignRequestError):
                host.update_candidate(self.user, run.pk, command)
        run.refresh_from_db()
        self.assertEqual(run.sequence, 0)
        host.snapshot(run)
        DesignPilotCandidate.objects.filter(pk=run.pk).update(source_bytes=b"changed")
        run.refresh_from_db()
        with self.assertRaises(DesignRequestError):
            host.snapshot(run)

    def test_container_guard_reuse_preserves_readability_recognition_policy(self):
        path = Path(self.directory.name) / "template.docx"
        # Test fixture bytes, not user document material.
        with path.open("wb") as stream:
            stream.write(fy27_docx())
        with self.assertRaisesRegex(ValueError, "word_format_unsupported"):
            word_html(path)
        html, _ = word_html(path, require_nofo_recognition=False)
        self.assertIn("Distinctive source text", html)
        with path.open("wb") as stream:
            stream.write(b"Not a Word container")
        with self.assertRaises(ValueError):
            word_html(path, require_nofo_recognition=False)

    def test_cross_candidate_body_and_repeated_fields_are_rejected(self):
        run = self.candidate()
        command = self.command(run)
        command["candidate_id"] = "other-candidate"
        with self.assertRaises(DesignRequestError):
            host.update_candidate(self.user, run.pk, command)
        command = self.command(run)
        command["reason"] = ["first", "second"]
        command["value"] = "true"
        self.assertEqual(
            self.client.post(
                reverse("design_pilot:operation", args=[run.pk]), command
            ).status_code,
            400,
        )

    def test_import_render_and_changes_never_call_pdf_or_external_cover(self):
        with patch(
            "docraptor.DocApi.create_doc", side_effect=AssertionError("PDF forbidden")
        ), patch(
            "nofos.nofo.get_image_url_from_s3",
            side_effect=AssertionError("S3 forbidden"),
        ):
            run = self.candidate()
            host.review_artifact(run)
            host.update_candidate(self.user, run.pk, self.command(run))
