from django.forms import ValidationError

from nofos.nofo import _build_document

from .models import CompareDocument, CompareSection, CompareSubsection


def create_compare_document(title, sections, opdiv):
    guide = CompareDocument(title=title)
    guide.opdiv = opdiv
    guide.save()
    try:
        return _build_document(guide, sections, CompareSection, CompareSubsection)
    except ValidationError as e:
        guide.delete()
        e.guide = guide
        raise e
