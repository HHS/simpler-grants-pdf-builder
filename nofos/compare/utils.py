import os

from django.forms import ValidationError

from nofos.nofo import _build_document

from .models import CompareDocument, CompareSection, CompareSubsection


def create_compare_document(title, sections, opdiv):
    document = CompareDocument(title=title)
    document.opdiv = opdiv
    document.save()
    try:
        return _build_document(document, sections, CompareSection, CompareSubsection)
    except ValidationError as e:
        document.delete()
        e.document = document
        raise e


def strip_file_suffix(filename: str) -> str:
    """
    Removes the final file extension from a filename.
    e.g., 'Document_123_2025.08.01.docx' → 'Document_123_2025.08.01'
    """
    return os.path.splitext(filename)[0]
