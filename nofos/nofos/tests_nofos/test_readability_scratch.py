import os
import selectors
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from nofos.readability_scratch import request_workspace, scratch_root, sweep_abandoned


class ReadabilityScratchTests(SimpleTestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(
            patch(
                "nofos.readability_scratch.tempfile.gettempdir", return_value=directory
            )
        )
        self.base = Path(directory)

    def test_sweep_preserves_active_and_unrelated_paths(self):
        root = scratch_root()
        unrelated = self.base / "ordinary-upload"
        unrelated.write_bytes(b"unrelated")
        (root / "request-aaaaaaaa").symlink_to(unrelated)
        unrelated_dir = root / "other-work"
        unrelated_dir.mkdir()
        with request_workspace() as workspace:
            pdf = workspace / "input.pdf"
            pdf.write_bytes(b"active")
            sweep_abandoned()
            self.assertEqual(pdf.read_bytes(), b"active")
        self.assertFalse(workspace.exists())
        self.assertEqual(unrelated.read_bytes(), b"unrelated")
        self.assertTrue(unrelated_dir.is_dir())

    def test_sweep_reclaims_crashed_process_workspace_and_all_copies(self):
        code = """
from pathlib import Path
from nofos.readability_scratch import request_workspace
import os
import sys

with request_workspace() as directory:
    (directory / 'buffer.upload').write_bytes(b'synthetic')
    (directory / 'input.pdf').write_bytes(b'synthetic')
    nested = directory / 'metrics'
    nested.mkdir()
    (nested / 'primary.pdf').write_bytes(b'synthetic')
    print(directory, flush=True)
    sys.stdin.read(1)
    os._exit(0)
"""
        with subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "TMPDIR": str(self.base)},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        ) as child:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=5), "workspace not ready")
                    line = child.stdout.readline().strip()
                    self.assertTrue(line)
                workspace = Path(line)
                self.assertEqual(workspace.parent, scratch_root())
                sweep_abandoned()
                self.assertEqual(len(list(workspace.rglob("*.pdf"))), 2)
                child.communicate(input="x", timeout=5)
                self.assertEqual(child.returncode, 0)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        self.assertTrue(workspace.exists())
        sweep_abandoned()
        self.assertFalse(workspace.exists())

    def test_normal_cleanup_failure_is_content_free_and_retried(self):
        with self.assertLogs(
            "django.request.pdf_readability.scratch", "WARNING"
        ) as logs:
            with patch(
                "nofos.readability_scratch.shutil.rmtree",
                side_effect=PermissionError("synthetic filename"),
            ):
                with request_workspace() as workspace:
                    (workspace / "input.pdf").write_bytes(b"synthetic")
        self.assertNotIn("synthetic", " ".join(logs.output))
        self.assertTrue(workspace.exists())
        sweep_abandoned()
        self.assertFalse(workspace.exists())
