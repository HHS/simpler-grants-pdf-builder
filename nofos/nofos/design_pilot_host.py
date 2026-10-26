"""Trusted local synthetic host. No agent credentials or production transport."""

import hashlib
import json
import tempfile
from pathlib import Path

from bloom_nofos.context_processors import template_context
from bs4 import BeautifulSoup
from constance import config
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.http import Http404
from django.template.loader import render_to_string
from users.models import BloomUser

from .design_candidate import DesignCandidate, DesignRequestError, apply_design_request
from .design_candidate_choices import design_capabilities
from .document_processing import process_document_content
from .forms import NofoThemeOptionsForm
from .models import DesignPilotCandidate
from .nofo import (
    add_headings_to_document,
    create_nofo,
    parse_uploaded_file_as_html_string,
    suggest_all_nofo_fields,
    suggest_nofo_opdiv,
)
from .nofo_document_context import get_nofo_document_context
from .word_readability import word_html

WIDTH_CLASS = "section--tables-full-width"
WORD_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def require_profile():
    if (
        not getattr(settings, "DESIGN_PILOT_ENABLED", False)
        or settings.DEBUG
        or settings.DOCRAPTOR_API_KEY
        or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3"
    ):
        raise Http404


def current_owner(user):
    require_profile()
    if not user.is_authenticated:
        raise PermissionDenied
    owner = BloomUser.objects.filter(pk=user.pk, is_active=True).first()
    if owner is None:
        raise PermissionDenied
    return owner


def owned_candidate(user, candidate_id):
    owner = current_owner(user)
    try:
        return DesignPilotCandidate.objects.select_related("nofo").get(
            pk=candidate_id,
            owner=owner,
            owner_group=owner.group,
            nofo__group=owner.group,
        )
    except DesignPilotCandidate.DoesNotExist:
        raise Http404 from None


def candidate_capabilities(user, run):
    """Rebuild choices from current membership and Builder's existing form policy."""
    run = owned_candidate(user, run.pk)
    owner = current_owner(user)
    catalog = design_capabilities(candidate=snapshot(run))
    allowed_themes = []
    for theme in catalog["choices"]["theme"]:
        # A bound form includes restrictions for both the stored document and
        # resulting theme. Field validation does not mutate the model instance.
        form = NofoThemeOptionsForm(
            data={"theme": theme}, instance=run.nofo, user=owner
        )
        try:
            form.fields["theme"].clean(theme)
            form.fields["cover"].clean(run.nofo.cover)
        except ValidationError:
            continue
        allowed_themes.append(theme)
    catalog["choices"] = {
        "theme": allowed_themes,
        "cover": [run.nofo.cover],  # This host never permits cover mutations.
    }
    return catalog


def _values(record, excluded=()):
    return {
        field.name: field.value_from_object(record)
        for field in record._meta.concrete_fields
        if field.name
        not in {"created", "updated", "created_by", "updated_by", *excluded}
    }


def content_snapshot(nofo):
    data = {"nofo": _values(nofo, ("theme", "cover")), "sections": []}
    for section in nofo.sections.order_by("order", "pk"):
        values = _values(section)
        values["html_class"] = " ".join(
            c for c in section.html_class.split() if c != WIDTH_CLASS
        )
        values["subsections"] = [
            _values(sub) for sub in section.subsections.order_by("order", "pk")
        ]
        data["sections"].append(values)
    return json.dumps(
        data, cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":")
    )


def snapshot(run):
    if hashlib.sha256(bytes(run.source_bytes)).hexdigest() != run.source_sha256:
        raise DesignRequestError("Stored source failed its integrity check")
    if content_snapshot(run.nofo) != run.content_json:
        raise DesignRequestError(
            "This candidate’s content changed outside the pilot and can no longer be used. "
            "Uploading the same file again will not repair it. "
            "Ask the developer running the pilot to remove this candidate and its "
            "associated NOFO record, then upload the original Word file again."
        )
    candidate = DesignCandidate(
        str(run.pk),
        run.source_sha256,
        run.content_json,
        run.presentation_json,
        run.changes_json,
        run.sequence,
    )
    if candidate.revision != run.revision:
        raise DesignRequestError("Candidate state failed its integrity check")
    presentation = json.loads(run.presentation_json)
    if (
        run.nofo.theme != presentation["theme"]
        or run.nofo.cover != presentation["cover"]
        or {
            str(s.pk): WIDTH_CLASS in s.html_class.split()
            for s in run.nofo.sections.all()
        }
        != presentation["section_table_width"]
    ):
        raise DesignRequestError("Candidate presentation changed outside this workflow")
    return candidate


def _safe_document(nofo):
    # This slice owns no cover assets. Never invoke S3/external cover resolution.
    if nofo.cover_image or nofo.inline_css:
        raise DesignRequestError(
            "External cover assets and custom CSS are unsupported in this local slice"
        )
    context = {
        "nofo": nofo,
        "object": nofo,
        **get_nofo_document_context(nofo),
        **template_context(None),
    }
    soup = BeautifulSoup(
        render_to_string("nofos/design_pilot_document.html", context), "html.parser"
    )
    for node in list(
        soup.find_all(["script", "style", "iframe", "object", "embed", "form", "base"])
    ):
        node.decompose()
    for node in soup.find_all(True):
        for attr in list(node.attrs):
            if attr.lower().startswith("on") or attr in ("srcset", "ping"):
                del node[attr]
        for attr in ("src", "href", "xlink:href"):
            value = str(node.get(attr, ""))
            if not value:
                continue
            if node.name == "a":
                if "#" in value and value.startswith(f"/nofos/{nofo.pk}"):
                    node[attr] = "#" + value.split("#", 1)[1]
                elif not value.startswith("#"):
                    del node[attr]
            elif not (
                value.startswith("/static/")
                and ".." not in value
                or value.startswith("#")
                or node.name == "img"
                and value.startswith(
                    ("data:image/png;base64,", "data:image/jpeg;base64,")
                )
            ):
                del node[attr]
        if (
            "url(" in str(node.get("style", "")).lower()
            or "@import" in str(node.get("style", "")).lower()
        ):
            del node["style"]
    return str(soup)


def _render_inputs():
    """Conservative byte binding, not an assertion of PDF-layout equivalence."""
    digest = hashlib.sha256()
    root = Path(settings.BASE_DIR)
    for directory in (root / "nofos", root / "bloom_nofos"):
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or any(
                p in path.parts for p in ("fixtures", "__pycache__", "migrations")
            ):
                continue
            if path.suffix not in {
                ".py",
                ".html",
                ".css",
                ".js",
                ".svg",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".woff",
                ".woff2",
                ".ttf",
            }:
                continue
            if path.is_symlink():
                raise DesignRequestError("Linked render assets are unsupported")
            digest.update(str(path.relative_to(root)).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    digest.update((root.parent / "poetry.lock").read_bytes())
    flags = {
        name: getattr(config, name)
        for name, definition in settings.CONSTANCE_CONFIG.items()
        if type(definition[0]) is bool
    }
    digest.update(json.dumps(flags, sort_keys=True).encode())
    return digest.hexdigest()


def review_artifact(run):
    candidate = snapshot(run)
    html = _safe_document(run.nofo)
    revision = hashlib.sha256(
        (
            candidate.revision
            + _render_inputs()
            + hashlib.sha256(html.encode()).hexdigest()
        ).encode()
    ).hexdigest()
    return revision, html


def import_candidate(user, upload):
    owner = current_owner(user)
    if (
        not upload
        or not upload.name.lower().endswith(".docx")
        or upload.size > 1024 * 1024
    ):
        raise ValidationError(
            "Choose one synthetic NOFO Word file (.docx), no larger than 1 MB."
        )
    data = upload.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValidationError("Choose a Word file no larger than 1 MB.")
    digest = hashlib.sha256(data).hexdigest()
    existing = DesignPilotCandidate.objects.filter(
        owner=owner, source_sha256=digest
    ).first()
    if existing:
        run = owned_candidate(owner, existing.pk)
        snapshot(run)
        return run
    # Reuse the existing bounded Word container/recognition guard. Its readability
    # conversion is not used for Builder import, which retains its own transforms.
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".docx", dir=settings.DESIGN_PILOT_ROOT
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            # Builder's own structural/OpDiv validation follows below. Its
            # supported imports need not match the readability pilot's policy.
            word_html(Path(temporary.name), require_nofo_recognition=False)
    except ValueError:
        raise ValidationError(
            "This file is not a supported NOFO Word document. Check the document format and headings."
        ) from None
    warnings = []
    html, count = parse_uploaded_file_as_html_string(
        SimpleUploadedFile("synthetic.docx", data, content_type=WORD_TYPE),
        omit_leading_title=True,
        review_warnings=warnings,
        list_review_warnings=warnings,
        preserve_empty_paragraphs=True,
    )
    content = process_document_content(
        html, builder_import=True, extract_scoped_tagline=True, editable_intro="detect"
    )
    try:
        with transaction.atomic():
            nofo = create_nofo(
                "Synthetic design candidate",
                content.sections,
                suggest_nofo_opdiv(content.soup),
                group=owner.group,
            )
            add_headings_to_document(nofo)
            suggest_all_nofo_fields(
                nofo,
                content.soup,
                first_time_import=True,
                imported_tagline=content.imported_tagline,
            )
            nofo.short_name = "Synthetic local design candidate"
            nofo.cover_image = ""
            nofo.cover = "nofo--cover-page--text"
            nofo.save()
            run = DesignPilotCandidate(
                owner=owner,
                owner_group=owner.group,
                nofo=nofo,
                source_sha256=digest,
                source_bytes=data,
                source_name=Path(upload.name).name[:200],
                conversion_html=html,
                warnings=warnings
                + (
                    ["Review Word conversion warnings against the source."]
                    if count
                    else []
                ),
            )
            candidate = DesignCandidate.create(
                str(run.pk),
                digest,
                json.loads(content_snapshot(nofo)),
                {
                    "theme": nofo.theme,
                    "cover": nofo.cover,
                    "section_table_width": {
                        str(s.pk): WIDTH_CLASS in s.html_class.split()
                        for s in nofo.sections.all()
                    },
                },
            )
            run.content_json = candidate.content_json
            run.presentation_json = candidate.presentation_json
            run.revision = candidate.revision
            run.save()
            review_artifact(run)  # A real rendering failure rolls back the import.
            return run
    except IntegrityError:
        run = owned_candidate(
            owner,
            DesignPilotCandidate.objects.get(owner=owner, source_sha256=digest).pk,
        )
        snapshot(run)
        return run


def update_candidate(user, candidate_id, request):
    if not isinstance(request, dict):
        raise DesignRequestError("A design request must be an object")
    if request.get("operation") == "set_cover":
        raise DesignRequestError(
            "Cover changes are not available in this text-only slice"
        )
    with transaction.atomic():
        run = owned_candidate(user, candidate_id)
        review_revision, _ = review_artifact(run)
        if request.get("expected_revision") != review_revision:
            raise DesignRequestError(
                "This candidate or its rendering changed. Return to review before saving again."
            )
        current = snapshot(run)
        command = {**request, "expected_revision": current.revision}
        updated = apply_design_request(
            current, command, choices=candidate_capabilities(user, run)["choices"]
        )
        if updated is current:
            return run
        if not DesignPilotCandidate.objects.filter(
            pk=run.pk, revision=current.revision
        ).update(
            presentation_json=updated.presentation_json,
            changes_json=updated.changes_json,
            sequence=updated.sequence,
            revision=updated.revision,
        ):
            raise DesignRequestError(
                "This candidate changed. Return to review before saving again."
            )
        design = updated.read()["presentation"]
        run.nofo.theme, run.nofo.cover = design["theme"], design["cover"]
        run.nofo.save(update_fields=["theme", "cover"])
        for section in run.nofo.sections.all():
            classes = [c for c in section.html_class.split() if c != WIDTH_CLASS]
            if design["section_table_width"][str(section.pk)]:
                classes.append(WIDTH_CLASS)
            section.html_class = " ".join(classes)
            section.save(update_fields=["html_class"])
        run.refresh_from_db()
        review_artifact(run)
        return run
