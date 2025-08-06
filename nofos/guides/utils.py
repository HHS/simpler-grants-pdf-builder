import os


def strip_file_suffix(filename: str) -> str:
    """
    Removes the final file extension from a filename.
    e.g., 'Document_123_2025.08.01.docx' → 'Document_123_2025.08.01'
    """
    return os.path.splitext(filename)[0]
