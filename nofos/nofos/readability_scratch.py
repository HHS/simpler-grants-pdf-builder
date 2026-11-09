"""Task-local scratch space for the standalone checker, not saved reports."""

import fcntl
import logging
import os
import re
import shutil
import stat
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from threading import Event

from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile
from django.core.files.uploadhandler import (
    FileUploadHandler,
    TemporaryFileUploadHandler,
)

SWEEP_SECONDS = 30
_REQUEST_NAME = re.compile(r"request-[a-z0-9_]{8}")
logger = logging.getLogger("django.request.pdf_readability.scratch")


def _remove_workspace(path):
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Readability scratch cleanup failed; will retry.")


def scratch_root():
    root = Path(tempfile.gettempdir()) / f"builder-readability-{os.getuid()}"
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise OSError("Readability scratch root is not a private directory")
    return root


@contextmanager
def _lease(path, *, wait=False):
    # The directory itself is the lease. Do not follow a symlink or inherit the
    # descriptor in the parser. An abandoned request no longer has a live lease.
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        if not os.path.samestat(os.fstat(descriptor), path.lstat()):
            raise FileNotFoundError("Readability scratch directory was replaced")
        yield
    finally:
        os.close(descriptor)


@contextmanager
def request_workspace():
    root = scratch_root()
    with ExitStack() as stack:
        # Serialize publication with the sweep's directory snapshot. Hold
        # only the per-request lease during upload and analysis.
        with _lease(root, wait=True):
            path = Path(tempfile.mkdtemp(prefix="request-", dir=root))
            stack.enter_context(_lease(path))
        try:
            yield path
        finally:
            _remove_workspace(path)


def sweep_abandoned():
    """Remove only inactive request directories in the private checker root."""
    root = scratch_root()
    with _lease(root, wait=True):
        paths = list(root.iterdir())
    for path in paths:
        if not _REQUEST_NAME.fullmatch(path.name) or path.is_symlink():
            continue
        try:
            with _lease(path):
                _remove_workspace(path)
        except (BlockingIOError, FileNotFoundError, NotADirectoryError):
            continue
        except OSError:
            logger.warning("Readability scratch cleanup failed; will retry.")


def run_sweeper():
    # The Gunicorn worker starts this after fork. A surviving worker can clean
    # up even when no new requests arrive; replacements sweep at startup.
    wait = Event()
    while True:
        try:
            sweep_abandoned()
        except OSError:
            logger.warning("Readability scratch scan failed; will retry.")
        wait.wait(SWEEP_SECONDS)


class _CheckerTemporaryUpload(TemporaryUploadedFile):
    def __init__(self, handler):
        # Django's default disk upload uses a process-wide directory. Override
        # only the file creation; keep its close and interruption behavior.
        temporary = tempfile.NamedTemporaryFile(suffix=".upload", dir=handler.workspace)
        UploadedFile.__init__(
            self,
            temporary,
            handler.file_name,
            handler.content_type,
            0,
            handler.charset,
            handler.content_type_extra,
        )


class CheckerDiskUploadHandler(TemporaryFileUploadHandler):
    def __init__(self, request, workspace):
        super().__init__(request)
        self.workspace = workspace

    def new_file(self, *args, **kwargs):
        FileUploadHandler.new_file(self, *args, **kwargs)
        self.file = _CheckerTemporaryUpload(self)
