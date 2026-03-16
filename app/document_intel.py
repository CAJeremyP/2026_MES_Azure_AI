"""
document_intel.py — Azure Document Intelligence (Form Recognizer)
Extracts text from images using the prebuilt Read model.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

ENDPOINT = os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"]
KEY      = os.environ["DOCUMENT_INTELLIGENCE_KEY"]


def run_document_intelligence(image_path: Path) -> dict:
    """
    Run OCR on an image using the prebuilt-read model.
    Returns dict with 'lines', 'words', and 'pages' counts.
    """
    client = DocumentAnalysisClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY)
    )

    with open(image_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", f)
    result = poller.result()

    lines = []
    all_words = []

    for page in result.pages:
        for line in (page.lines or []):
            # Bounding polygon — list of points
            polygon = None
            if line.polygon:
                polygon = [{"x": p.x, "y": p.y} for p in line.polygon]

            lines.append({
                "content":    line.content,
                "confidence": None,   # Read model doesn't expose per-line confidence
                "polygon":    polygon,
                "page":       page.page_number,
            })

        for word in (page.words or []):
            all_words.append({
                "content":    word.content,
                "confidence": word.confidence,
                "page":       page.page_number,
            })

    return {
        "lines":      lines,
        "words":      all_words,
        "page_count": len(result.pages),
        "full_text":  "\n".join(l["content"] for l in lines),
    }
