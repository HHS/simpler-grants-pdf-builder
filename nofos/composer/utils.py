from django.forms import ValidationError

from nofos.nofo import _build_document

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection


def create_content_guide_document(title, sections, opdiv):
    document = ContentGuide(title=title)
    document.opdiv = opdiv
    document.save()
    try:
        return _build_document(
            document, sections, ContentGuideSection, ContentGuideSubsection
        )
    except ValidationError as e:
        document.delete()
        e.document = document
        raise e


EDIT_MODE_LABELS = {
    "full": "Some text",
    "variables": "Variables",
    "yes_no": "Yes/No",
    "locked": "Locked",
}


def get_edit_mode_label(value: str) -> str:
    """Return a human-readable label for an ContentGuideSubsection edit_mode value."""
    if not value:
        return ""
    return EDIT_MODE_LABELS.get(value) or value
