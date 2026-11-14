import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

# Settings choose the deployed LOGGING config only when "test" is not in
# sys.argv, so load it in a separate interpreter to exercise the real config.
PROGRAM = r"""
import logging
import os
from unittest.mock import Mock, patch

os.environ["DJANGO_SETTINGS_MODULE"] = "bloom_nofos.settings"

import django

from django.test import override_settings

from bloom_nofos.utils import generate_docx_download_response

django.setup()

utils_logger = logging.getLogger("bloom_nofos.utils")
utils_logger.info("bloom_nofos info should be filtered")
utils_logger.warning("GrabzIt Word export blocked for unconfigured host")
host = "example.test"
request = Mock(COOKIES={"sessionid": "fake-session", "csrftoken": "fake-csrf"})
request.get_host.return_value = host
with (
    override_settings(
        GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=[host],
        GRABZIT_APPLICATION_KEY="fake-key",
        GRABZIT_APPLICATION_SECRET="fake-secret",
    ),
    patch("bloom_nofos.utils.GrabzItClient.GrabzItClient") as client,
):
    client.return_value.SaveTo.side_effect = RuntimeError("provider-secret-sentinel")
    generate_docx_download_response(
        request=request,
        export_url=f"https://{host}/export",
        target_element="main",
        filename_base="example",
        tmp_name="logging-config-test",
    )
utils_logger.error("GrabzIt returned an invalid or empty DOCX")
"""


class DeployedLoggingConfigTests(SimpleTestCase):
    """Word export logs must reach the console outside tests (#1353)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-B", "-c", PROGRAM],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        cls.returncode = result.returncode
        cls.output = result.stdout + result.stderr
        cls.records = []
        for line in result.stderr.splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and "message" in record:
                cls.records.append(record)

    def _messages(self):
        return [record["message"] for record in self.records]

    def test_program_runs(self):
        self.assertEqual(self.returncode, 0, self.output)

    def test_word_export_warnings_and_errors_reach_console(self):
        messages = self._messages()
        self.assertIn("GrabzIt Word export blocked for unconfigured host", messages)
        self.assertIn("GrabzIt Word export request failed", messages)
        self.assertIn("GrabzIt returned an invalid or empty DOCX", messages)

    def test_records_are_json_with_level(self):
        levels = {record["message"]: record.get("levelname") for record in self.records}
        self.assertEqual(
            levels["GrabzIt Word export blocked for unconfigured host"], "WARNING"
        )
        self.assertEqual(levels["GrabzIt Word export request failed"], "ERROR")

    def test_provider_exception_logs_only_safe_fields(self):
        failed = next(
            record
            for record in self.records
            if record["message"] == "GrabzIt Word export request failed"
        )
        self.assertEqual(failed["error_type"], "RuntimeError")
        self.assertEqual(failed["export_host"], "example.test")
        self.assertNotIn("exc_info", failed)
        self.assertNotIn("provider-secret-sentinel", self.output)

    def test_info_is_not_emitted(self):
        self.assertNotIn("bloom_nofos info should be filtered", self.output)
