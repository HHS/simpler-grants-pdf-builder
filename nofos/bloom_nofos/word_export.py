"""Gated, local basic DOCX conversion. No vendor calls or credential forwarding."""

import base64
import binascii
import fcntl
import io
import os
import signal
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from copy import copy
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse, QueryDict
from django.urls import resolve
from django.utils.http import content_disposition_header

ASSETS = Path(__file__).parent / "word_export_assets"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_INPUT = 2 * 1024 * 1024
MAX_OUTPUT = 20 * 1024 * 1024
MAX_IMAGE = 5 * 1024 * 1024


class ExportError(Exception):
    pass


def embed_image(source, host):
    """Allow bounded inline raster images or public bundled static files only."""
    if source.startswith("data:"):
        header, separator, encoded = source.partition(",")
        if (
            header
            not in {
                "data:image/png;base64",
                "data:image/jpeg;base64",
                "data:image/gif;base64",
            }
            or not separator
            or len(encoded) > (MAX_IMAGE * 4 // 3 + 4)
        ):
            raise ExportError("Unsupported or oversized embedded Word export image.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ExportError("Invalid embedded Word export image.") from exc
    else:
        url = urlsplit(source)
        prefix = "/" + urlsplit(settings.STATIC_URL).path.strip("/") + "/"
        path = unquote(url.path)
        if (
            (url.netloc and url.netloc != host)
            or url.scheme not in ("", "http", "https")
            or not path.startswith(prefix)
            or "\\" in path
            or "\x00" in path
            or any(part in (".", "..") for part in path.split("/"))
        ):
            raise ExportError(
                "Word export supports embedded or bundled images only, not remote images."
            )
        relative = path[len(prefix) :]
        if not relative or relative.startswith("/"):
            raise ExportError("Invalid bundled Word export image path.")
        filename = finders.find(relative)
        if not filename and settings.STATIC_ROOT:
            root = Path(settings.STATIC_ROOT).resolve()
            candidate = (root / relative).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                filename = candidate
        if not filename:
            raise ExportError("A bundled Word export image could not be found.")
        try:
            with open(filename, "rb") as image:
                data = image.read(MAX_IMAGE + 1)
        except OSError as exc:
            raise ExportError("A bundled Word export image could not be read.") from exc
    if len(data) > MAX_IMAGE:
        raise ExportError("Word export image exceeds the 5 MiB limit.")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    else:
        raise ExportError("Word export images must be PNG, JPEG, or GIF.")
    return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")


@contextmanager
def conversion_slot():
    """One active export per container, shared across Gunicorn workers."""
    directory = Path(tempfile.gettempdir()) / "builder-word-export-locks"
    directory.mkdir(mode=0o700, exist_ok=True)
    handles = []
    try:
        for index in range(1):
            handle = (directory / str(index)).open("a")
            handles.append(handle)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            yield True
            return
        yield False
    finally:
        for handle in handles:
            handle.close()


def render_export_html(request, export_url, target_element):
    url = urlsplit(export_url)
    if url.netloc != request.get_host():
        raise ExportError("Invalid Word export destination.")
    match = resolve(url.path)
    if match.url_name not in {
        "nofo_export",
        "composer_export",
        "writer_instance_export",
    }:
        raise ExportError("Unsupported Word export view.")
    # Reuse the real GET view's permission checks and current export-time policy
    # evaluation. Only the document target is passed to the converter.
    get_request = copy(request)
    get_request.method = "GET"
    get_request.path = get_request.path_info = url.path
    get_request.GET = QueryDict(url.query)
    get_request.POST = QueryDict()
    get_request.META = request.META.copy()
    get_request.META["QUERY_STRING"] = url.query
    get_request.user = request.user
    response = match.func(get_request, *match.args, **match.kwargs)
    if response.status_code != 200:
        raise ExportError("Unable to render the Word export.")
    if hasattr(response, "render"):
        response.render()
    # Bound parsing work before constructing a BeautifulSoup tree. The view has
    # already rendered; this is not a limit on Django's rendering memory.
    if len(response.content) > MAX_INPUT:
        raise ExportError(
            "This document exceeds the experimental Word export size limit."
        )
    soup = BeautifulSoup(response.content, "html.parser")
    target = soup.select_one(target_element)
    if target is None or not target.get_text(strip=True):
        raise ExportError("The Word export contains no document content.")
    for element in target.select("script, style, form, input, button, iframe, object"):
        element.decompose()
    image_budget = MAX_INPUT
    for image in target.select("img"):
        embedded = embed_image(image.get("src", ""), request.get_host())
        image_budget -= len(embedded)
        if image_budget < 0:
            raise ExportError(
                "This document exceeds the experimental Word export size limit."
            )
        image["src"] = embedded
        image.attrs.pop("srcset", None)
    html = "<!doctype html><html><body>" + str(target) + "</body></html>"
    if len(html.encode()) > MAX_INPUT:
        raise ExportError(
            "This document exceeds the experimental Word export size limit."
        )
    return html


def normalize_docx(data):
    """Map Pandoc styles to existing import styles without changing numbering."""
    if len(data) > MAX_OUTPUT:
        raise ExportError("Word export exceeded the output size limit.")
    try:
        with ZipFile(io.BytesIO(data)) as source:
            if sum(item.file_size for item in source.infolist()) > 50 * 1024 * 1024:
                raise ExportError("Word export exceeded the expanded size limit.")
            xml = ET.fromstring(source.read("word/document.xml"))
            if not any((node.text or "").strip() for node in xml.iter(W + "t")):
                raise ExportError("Word conversion returned an empty document.")
            for style in xml.iter(W + "pStyle"):
                if style.get(W + "val") in ("FirstParagraph", "Compact"):
                    style.set(W + "val", "BodyText")
            # Move otherwise empty break paragraphs onto following paragraphs to
            # avoid blank pages. Never discard drawings, fields, or text.
            for parent in xml.iter():
                children = list(parent)
                for index, paragraph in enumerate(children):
                    if paragraph.tag != W + "p" or not any(
                        br.get(W + "type") == "page" for br in paragraph.iter(W + "br")
                    ):
                        continue
                    meaningful = {
                        W + tag
                        for tag in (
                            "t",
                            "drawing",
                            "object",
                            "pict",
                            "tab",
                            "fldChar",
                            "instrText",
                        )
                    }
                    if any(node.tag in meaningful for node in paragraph.iter()):
                        continue
                    following = next(
                        (
                            node
                            for node in children[index + 1 :]
                            if node.tag not in (W + "bookmarkStart", W + "bookmarkEnd")
                        ),
                        None,
                    )
                    if following is not None and following.tag == W + "p":
                        props = following.find(W + "pPr")
                        if props is None:
                            props = ET.Element(W + "pPr")
                            following.insert(0, props)
                        if props.find(W + "pageBreakBefore") is None:
                            ET.SubElement(props, W + "pageBreakBefore")
                        parent.remove(paragraph)
            output = io.BytesIO()
            with ZipFile(output, "w", ZIP_DEFLATED) as result:
                for item in source.infolist():
                    result.writestr(
                        item,
                        (
                            ET.tostring(xml)
                            if item.filename == "word/document.xml"
                            else source.read(item.filename)
                        ),
                    )
            return output.getvalue()
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ExportError("Word conversion returned an invalid document.") from exc


def convert_html(html):
    if len(html.encode("utf-8")) > MAX_INPUT:
        raise ExportError(
            "This document exceeds the experimental Word export size limit."
        )
    with tempfile.TemporaryDirectory(prefix="builder-word-") as directory:
        source = Path(directory) / "input.html"
        output = Path(directory) / "output.docx"
        source.write_text(html, encoding="utf-8")
        command = [
            getattr(settings, "PANDOC_BINARY", "pandoc"),
            # Supported by the pinned official GHC-built binary. This bounds the
            # managed heap, NOT total RSS or Django's memory. No unbounded retry.
            "+RTS",
            "-M192m",
            "-K16m",
            "-RTS",
            "--sandbox",
            "-f",
            "html",
            "-t",
            "docx",
            "--standalone",
            "--reference-doc=" + str(ASSETS / "reference.docx"),
            "--lua-filter=" + str(ASSETS / "adapter.lua"),
            str(source),
            "-o",
            str(output),
        ]
        try:
            process = subprocess.Popen(
                command,
                cwd=directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as exc:
            raise ExportError("The local Word converter is unavailable.") from exc
        try:
            _, errors = process.communicate(timeout=45)
        except subprocess.TimeoutExpired as exc:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # It exited between the timeout and process-group cleanup.
            process.communicate()
            raise ExportError(
                "Word export timed out. Please retry with a smaller document."
            ) from exc
        # Do not log stderr: converter diagnostics may contain document content.
        if process.returncode or errors.strip() or not output.exists():
            raise ExportError(
                "Word conversion failed or exceeded resource limits. "
                "No document was downloaded. Try a smaller document."
            )
        if output.stat().st_size > MAX_OUTPUT:
            raise ExportError("Word export exceeded the output size limit.")
        return normalize_docx(output.read_bytes())


def pandoc_download_response(request, export_url, target_element, filename_base):
    if not request.user.is_authenticated:
        return HttpResponse("Please sign in to export Word documents.", status=403)
    with conversion_slot() as admitted:
        if not admitted:
            return JsonResponse(
                {"word_export_error": "Word export is busy. Please retry shortly."},
                status=503,
                headers={"Retry-After": "5"},
            )
        try:
            data = convert_html(render_export_html(request, export_url, target_element))
        except ExportError as exc:
            return JsonResponse({"word_export_error": str(exc)}, status=422)
    return HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": content_disposition_header(
                True, filename_base + ".docx"
            )
        },
    )
