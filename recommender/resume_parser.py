"""
Resume text extraction utilities.

Supports PDF (.pdf) and Word (.docx) files.
"""

import fitz  # PyMuPDF
import docx


def extract_text_from_pdf(file_path):
    """Extract raw text from a PDF file using PyMuPDF."""
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def extract_text_from_docx(file_path):
    """Extract raw text from a DOCX file using python-docx."""
    document = docx.Document(file_path)
    text_parts = [para.text for para in document.paragraphs]
    return "\n".join(text_parts)


def extract_text(file_path):
    """
    Extract text from a resume file based on its extension.
    Returns an empty string if the file type is unsupported
    or extraction fails, rather than raising an error.
    """
    lower_path = str(file_path).lower()
    try:
        if lower_path.endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        elif lower_path.endswith('.docx'):
            return extract_text_from_docx(file_path)
        else:
            return ''
    except Exception as e:
        print(f"[resume_parser] Failed to extract text from {file_path}: {e}")
        return ''