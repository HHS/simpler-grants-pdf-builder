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
