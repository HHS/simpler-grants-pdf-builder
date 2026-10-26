"""HTTP credential/authority boundaries with invented Word content only."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.db import connections
from django.http import HttpResponse
from django.test import (
    Client,
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos import design_pilot_host as host
from nofos import design_pilot_tools as tools
from nofos.design_candidate import DesignRequestError
from nofos.design_pilot_views import LocalPilotBoundary
from nofos.models import DesignPilotCandidate
from nofos.tests_nofos import test_design_pilot_host as fixtures


class CandidateToolTests(TestCase):
    upload = fixtures.ConnectedDesignPilotTests.upload
    candidate = fixtures.ConnectedDesignPilotTests.candidate
    command = fixtures.ConnectedDesignPilotTests.command

    def setUp(self):
        fixtures.ConnectedDesignPilotTests.setUp(self)
        self.run = self.candidate()
        self.token, self.expires = tools.issue_access(self.user, self.run.pk)
        self.agent = Client(enforce_csrf_checks=True)

    def call(
        self,
        action="read",
        *,
        candidate_id=None,
        token=None,
        method="get",
        body=None,
        **extra,
    ):
        return getattr(self.agent, method)(
            reverse(f"design_pilot:tool_{action}", args=[candidate_id or self.run.pk]),
            **(
                {"data": body, "content_type": "application/json"}
                if body is not None
                else {}
            ),
            HTTP_AUTHORIZATION="Bearer " + (token or self.token),
            **extra,
        )

    def test_read_capabilities_and_revision_checked_operation(self):
        data = self.call().json()
        self.assertEqual(data["candidate_id"], str(self.run.pk))
        self.assertEqual(data["revision"], host.review_artifact(self.run)[0])
        catalog = self.call("capabilities").json()
        self.assertEqual(
            set(catalog["operations"]),
            {"read", "set_theme", "set_table_width", "html_review"},
        )
        self.assertFalse(catalog["pdf"]["supported"])
        self.assertFalse(catalog["acceptance"]["supported"])
        command = self.command(self.run)
        response = self.call("operation", method="post", body=json.dumps(command))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["revision"], data["revision"])
        self.assertEqual(
            self.call("operation", method="post", body=json.dumps(command)).status_code,
            409,
        )
        self.run.refresh_from_db()
        self.assertEqual(self.run.sequence, 1)
        host.snapshot(self.run)

    def test_raw_key_not_persisted_or_echoed_by_tools_and_no_store(self):
        self.run.refresh_from_db()
        self.assertEqual(
            self.run.tool_token_digest, hashlib.sha256(self.token.encode()).hexdigest()
        )
        self.assertNotIn(self.token, repr(self.run.__dict__))
        response = self.call()
        self.assertNotIn(self.token.encode(), response.content)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_capabilities_and_writes_follow_owner_not_cookies_or_source_opdiv(self):
        self.other.group = "cdc"
        self.other.save(update_fields=["group"])
        self.run = host.import_candidate(self.other, self.upload())
        self.token, _ = tools.issue_access(self.other, self.run.pk)
        # A broader human session cannot expand this CDC-bound credential.
        self.agent.force_login(self.user)
        catalog = self.call("capabilities").json()
        self.assertIn("portrait-cdc-blue", catalog["choices"]["theme"])
        self.assertNotIn("portrait-hrsa-white", catalog["choices"]["theme"])
        self.assertNotIn("cover", catalog["choices"])
        command = self.command(self.run)
        command.pop("section_id")
        command.update(operation="set_theme", value="portrait-hrsa-white")
        before = self.run.content_json
        self.assertEqual(
            self.call("operation", method="post", body=json.dumps(command)).status_code,
            409,
        )
        command["value"] = "portrait-cdc-blue"
        self.assertEqual(
            self.call("operation", method="post", body=json.dumps(command)).status_code,
            200,
        )
        self.run.refresh_from_db()
        self.assertEqual(self.run.nofo.theme, "portrait-cdc-blue")
        self.assertEqual(self.run.content_json, before)

    def test_cookie_alone_never_grants_tool_access(self):
        self.agent.force_login(self.user)
        self.assertEqual(
            self.agent.get(
                reverse("design_pilot:tool_read", args=[self.run.pk])
            ).status_code,
            401,
        )
        self.assertEqual(self.call(token="invented-wrong-key").status_code, 401)
        # Even a different human cookie cannot broaden the bearer scope.
        self.agent.force_login(self.other)
        self.assertEqual(self.call().status_code, 200)

    def test_no_cross_candidate_access_even_with_same_group_or_cookie(self):
        other = host.import_candidate(self.other, self.upload())
        self.assertEqual(self.call(candidate_id=other.pk).status_code, 401)
        command = self.command(other)
        self.assertEqual(
            self.call("operation", method="post", body=json.dumps(command)).status_code,
            409,
        )
        self.run.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.run.sequence, 0)
        self.assertEqual(other.sequence, 0)

    def test_expiration_rotation_revocation_and_request_limit(self):
        DesignPilotCandidate.objects.filter(pk=self.run.pk).update(
            tool_expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.call().status_code, 401)
        rotated, _ = tools.issue_access(self.user, self.run.pk)
        self.assertEqual(self.call().status_code, 401)
        self.assertEqual(self.call(token=rotated).status_code, 200)
        DesignPilotCandidate.objects.filter(pk=self.run.pk).update(
            tool_requests=tools.MAX_REQUESTS - 1
        )
        self.assertEqual(self.call("capabilities", token=rotated).status_code, 200)
        self.assertEqual(self.call(token=rotated).status_code, 401)
        fresh, _ = tools.issue_access(self.user, self.run.pk)
        tools.revoke_access(self.user, self.run.pk)
        self.assertEqual(self.call(token=fresh).status_code, 401)

    def test_inactive_owner_or_membership_change_revokes_current_access(self):
        BloomUser.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.call().status_code, 401)
        BloomUser.objects.filter(pk=self.user.pk).update(is_active=True, group="hrsa")
        self.assertEqual(self.call().status_code, 401)
        # Changing only the candidate group also cannot expand access.
        BloomUser.objects.filter(pk=self.user.pk).update(group="bloom")
        self.run.nofo.group = "hrsa"
        self.run.nofo.save()
        self.assertEqual(self.call().status_code, 401)

    def test_review_status_matches_key_lifecycle_and_client_access(self):
        url = reverse("design_pilot:review", args=[self.run.pk])

        def check_status(heading, *, active):
            response = self.client.get(url)
            self.assertContains(response, f'text-bold">{heading}</h3>')
            self.assertEqual(response.context["tool_access_active"], active)
            self.assertNotContains(response, self.token)
            soup = BeautifulSoup(response.content, "html.parser")
            revoke = soup.find(
                "form", action=reverse("design_pilot:revoke_access", args=[self.run.pk])
            )
            self.assertEqual(revoke.button.has_attr("disabled"), not active)
            return response

        check_status("Active", active=True)
        self.assertEqual(self.call().status_code, 200)
        # The displayed boundary agrees with the transport at the exact expiry.
        now = timezone.now()
        DesignPilotCandidate.objects.filter(pk=self.run.pk).update(tool_expires_at=now)
        with patch("django.utils.timezone.now", return_value=now):
            check_status("Expired", active=False)
            self.assertEqual(self.call().status_code, 401)
        self.token, _ = tools.issue_access(self.user, self.run.pk)
        check_status("Active", active=True)
        DesignPilotCandidate.objects.filter(pk=self.run.pk).update(
            tool_requests=tools.MAX_REQUESTS
        )
        response = check_status("Request limit reached", active=False)
        self.assertContains(response, "100 of 100 requests used")
        self.assertEqual(self.call().status_code, 401)
        tools.revoke_access(self.user, self.run.pk)
        check_status("No active access", active=False)
        self.assertEqual(self.call().status_code, 401)
        self.token, _ = tools.issue_access(self.user, self.run.pk)
        check_status("Active", active=True)
        self.assertEqual(self.call().status_code, 200)

    def test_human_issuance_requires_owner_post_and_csrf(self):
        url = reverse("design_pilot:issue_access", args=[self.run.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.agent.force_login(self.user)
        self.assertEqual(self.agent.post(url).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(
            self.call().status_code, 401
        )  # New response replaced the old key.
        self.assertNotContains(
            self.client.get(reverse("design_pilot:review", args=[self.run.pk])),
            self.token,
        )

    def test_bearer_cannot_reach_human_or_broader_routes(self):
        boundary = LocalPilotBoundary(lambda request: HttpResponse("unexpected"))
        factory = RequestFactory()
        for path in (
            "/design-pilot/",
            reverse("design_pilot:review", args=[self.run.pk]),
            reverse("design_pilot:issue_access", args=[self.run.pk]),
            reverse("design_pilot:revoke_access", args=[self.run.pk]),
            "/users/login/",
            "/nofos/",
            "/api/nofos",
            "/admin/",
            "/static/shared.css",
        ):
            response = boundary(
                factory.get(
                    path,
                    HTTP_AUTHORIZATION="Bearer " + self.token,
                    REMOTE_ADDR="127.0.0.1",
                )
            )
            self.assertEqual(response.status_code, 404)

    def test_unknown_authority_operations_and_malformed_json_fail_closed(self):
        for operation in (
            "accept",
            "promote",
            "publish",
            "discard",
            "fetch",
            "shell",
            "set_cover",
        ):
            command = self.command(self.run)
            command["operation"] = operation
            self.assertEqual(
                self.call(
                    "operation", method="post", body=json.dumps(command)
                ).status_code,
                409,
            )
        for body in (
            "[]",
            '{"operation":"set_theme","operation":"accept"}',
            '{"value":NaN}',
            "{",
            b"\xff",
            " " * 4097,
        ):
            self.assertIn(
                self.call("operation", method="post", body=body).status_code, (400, 409)
            )
        self.run.refresh_from_db()
        self.assertEqual(self.run.sequence, 0)
        self.assertGreater(self.run.tool_requests, 0)

    def test_html_requires_exact_revision_and_disables_active_content(self):
        revision = self.call().json()["revision"]
        response = self.call("html", QUERY_STRING="revision=" + revision)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertNotIn(b"<script", response.content)
        self.assertEqual(
            self.call("html", QUERY_STRING="revision=old").status_code, 409
        )
        self.assertEqual(self.call(QUERY_STRING="token=not-supported").status_code, 400)

    def test_render_failure_rolls_back_mutation_but_consumes_request(self):
        command = self.command(self.run)
        real_render = host._safe_document
        count = 0

        def fail_second(nofo):
            nonlocal count
            count += 1
            if count > 1:
                raise DesignRequestError("Synthetic render failure")
            return real_render(nofo)

        with patch.object(host, "_safe_document", side_effect=fail_second):
            response = self.call("operation", method="post", body=json.dumps(command))
        self.assertEqual(response.status_code, 409)
        self.run.refresh_from_db()
        self.assertEqual(self.run.sequence, 0)
        self.assertEqual(self.run.tool_requests, 1)
        host.snapshot(self.run)

    def test_disabled_normal_profile_and_no_pdf_or_s3_paths(self):
        with override_settings(DESIGN_PILOT_ENABLED=False):
            self.assertEqual(self.call().status_code, 404)
        with patch(
            "docraptor.DocApi.create_doc", side_effect=AssertionError("PDF forbidden")
        ), patch(
            "nofos.nofo.get_image_url_from_s3",
            side_effect=AssertionError("S3 forbidden"),
        ):
            self.assertEqual(self.call().status_code, 200)
            self.assertEqual(
                self.call(
                    "operation", method="post", body=json.dumps(self.command(self.run))
                ).status_code,
                200,
            )


class CandidateToolConcurrencyTests(TransactionTestCase):
    """Actual concurrent SQLite transactions, not a mocked CAS result."""

    setUp = CandidateToolTests.setUp
    upload = CandidateToolTests.upload
    candidate = CandidateToolTests.candidate
    command = CandidateToolTests.command
    call = CandidateToolTests.call

    def parallel_calls(self, action, command=None):
        barrier = Barrier(2)
        url = reverse(f"design_pilot:tool_{action}", args=[self.run.pk])

        def request():
            try:
                client = Client(enforce_csrf_checks=True)
                barrier.wait(timeout=10)
                headers = {"HTTP_AUTHORIZATION": "Bearer " + self.token}
                response = (
                    client.post(
                        url,
                        json.dumps(command),
                        content_type="application/json",
                        **headers,
                    )
                    if command
                    else client.get(url, **headers)
                )
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda _index: request(), range(2)))

    def test_competing_requests_do_not_lose_revision_or_exceed_quota(self):
        command = self.command(self.run)
        statuses = self.parallel_calls("operation", command)
        self.assertTrue(all(status in (200, 409) for status in statuses))
        self.assertLessEqual(statuses.count(200), 1)
        if 200 not in statuses:
            self.assertEqual(
                self.call(
                    "operation", method="post", body=json.dumps(command)
                ).status_code,
                200,
            )
        self.run.refresh_from_db()
        self.assertEqual(self.run.sequence, 1)
        host.snapshot(self.run)
        self.assertEqual(
            self.call("operation", method="post", body=json.dumps(command)).status_code,
            409,
        )

        DesignPilotCandidate.objects.filter(pk=self.run.pk).update(
            tool_requests=tools.MAX_REQUESTS - 1
        )
        statuses = self.parallel_calls("capabilities")
        self.assertTrue(all(status in (200, 401, 409) for status in statuses))
        self.assertLessEqual(statuses.count(200), 1)
        if 200 not in statuses:
            self.assertEqual(self.call("capabilities").status_code, 200)
        self.run.refresh_from_db()
        self.assertEqual(self.run.tool_requests, tools.MAX_REQUESTS)
        self.assertEqual(self.call().status_code, 401)
