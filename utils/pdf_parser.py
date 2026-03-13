# utils/pdf_parser.py
import fitz  # PyMuPDF
import logging
import os

def extract_text_from_pdf(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        logging.error(f"PDF file not found or path is invalid: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    try:
        # Use context manager for automatic closing
        with fitz.open(pdf_path) as doc:
            full_text = "".join([page.get_text("text") for page in doc])
        logging.info(f"Successfully extracted text from {os.path.basename(pdf_path)}")
        return full_text
    except Exception as e:
        logging.error(f"Error reading PDF file {pdf_path}: {e}", exc_info=True)
        raise ValueError(f"Could not read or parse PDF '{os.path.basename(pdf_path)}': {e}")