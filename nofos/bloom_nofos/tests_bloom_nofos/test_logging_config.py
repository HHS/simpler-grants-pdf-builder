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

os.environ["DJANGO_SETTINGS_MODULE"] = "bloom_nofos.settings"

import django

django.setup()

utils_logger = logging.getLogger("bloom_nofos.utils")
utils_logger.info("bloom_nofos info should be filtered")
utils_logger.warning("GrabzIt Word export blocked for unconfigured host")
try:
    raise RuntimeError("synthetic provider failure")
except RuntimeError:
    utils_logger.exception("GrabzIt Word export request failed")
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

    def test_exception_includes_traceback(self):
        failed = next(
            record
            for record in self.records
            if record["message"] == "GrabzIt Word export request failed"
        )
        self.assertIn("synthetic provider failure", json.dumps(failed))

    def test_info_is_not_emitted(self):
        self.assertNotIn("bloom_nofos info should be filtered", self.output)
