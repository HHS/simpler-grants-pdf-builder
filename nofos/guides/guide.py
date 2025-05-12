from django.forms import ValidationError
from guides.models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from nofos.nofo import _build_document


def create_content_guide(title, sections, opdiv):
    guide = ContentGuide(title=title)
    guide.opdiv = opdiv
    guide.save()
    try:
        return _build_document(
            guide, sections, ContentGuideSection, ContentGuideSubsection
        )
    except ValidationError as e:
        e.guide = guide
        raise e
