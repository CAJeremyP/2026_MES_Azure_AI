"""
vision.py — Azure Custom Vision Object Detection
=================================================
Calls detect_image on an Object Detection project.
Returns tag name, confidence, and normalised bounding box
(left, top, width, height as fractions of image size)
for each detected object above the confidence threshold.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials

PREDICTION_ENDPOINT  = os.environ["CUSTOM_VISION_PREDICTION_ENDPOINT"]
PREDICTION_KEY       = os.environ["CUSTOM_VISION_PREDICTION_KEY"]
PROJECT_ID           = os.environ.get("CUSTOM_VISION_PROJECT_ID", "")
PUBLISH_NAME         = os.environ.get("CUSTOM_VISION_PUBLISH_NAME", "demov1")
CONFIDENCE_THRESHOLD = 0.4


def run_custom_vision(blob_url: str, image_path: Path) -> list[dict]:
    """
    Run object detection on image_path.
    Returns list of dicts: { tag, probability, bounding_box: {left,top,width,height} }
    sorted by probability descending.
    """
    if not PROJECT_ID:
        print("  ⚠️  CUSTOM_VISION_PROJECT_ID not set in .env — skipping vision step.")
        return []

    credentials = ApiKeyCredentials(in_headers={"Prediction-key": PREDICTION_KEY})
    predictor   = CustomVisionPredictionClient(PREDICTION_ENDPOINT, credentials)

    with open(image_path, "rb") as img_data:
        results = predictor.detect_image(PROJECT_ID, PUBLISH_NAME, img_data)

    detections = [
        {
            "tag":         pred.tag_name,
            "probability": pred.probability,
            "bounding_box": {
                "left":   round(pred.bounding_box.left,   4),
                "top":    round(pred.bounding_box.top,    4),
                "width":  round(pred.bounding_box.width,  4),
                "height": round(pred.bounding_box.height, 4),
            },
        }
        for pred in results.predictions
        if pred.probability >= CONFIDENCE_THRESHOLD
    ]
    detections.sort(key=lambda x: x["probability"], reverse=True)
    return detections
