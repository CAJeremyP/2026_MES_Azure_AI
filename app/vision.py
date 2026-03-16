"""
vision.py — Azure Custom Vision (shape detection)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials

PREDICTION_ENDPOINT = os.environ["CUSTOM_VISION_PREDICTION_ENDPOINT"]
PREDICTION_KEY      = os.environ["CUSTOM_VISION_PREDICTION_KEY"]
PROJECT_ID          = os.environ.get("CUSTOM_VISION_PROJECT_ID", "")
PUBLISH_NAME        = os.environ.get("CUSTOM_VISION_PUBLISH_NAME", "demov1")
CONFIDENCE_THRESHOLD = 0.4   # Only return results above 40% confidence


def run_custom_vision(blob_url: str, image_path: Path) -> list[dict]:
    """
    Run Custom Vision object detection on the local image file.
    Returns a list of detection results.
    """
    if not PROJECT_ID:
        print("  ⚠️  CUSTOM_VISION_PROJECT_ID not set — skipping vision step.")
        return []

    credentials = ApiKeyCredentials(in_headers={"Prediction-key": PREDICTION_KEY})
    predictor = CustomVisionPredictionClient(PREDICTION_ENDPOINT, credentials)

    with open(image_path, "rb") as img_data:
        results = predictor.detect_image(
            PROJECT_ID,
            PUBLISH_NAME,
            img_data
        )

    detections = []
    for pred in results.predictions:
        if pred.probability >= CONFIDENCE_THRESHOLD:
            detections.append({
                "tag": pred.tag_name,
                "probability": pred.probability,
                "bounding_box": {
                    "left":   pred.bounding_box.left,
                    "top":    pred.bounding_box.top,
                    "width":  pred.bounding_box.width,
                    "height": pred.bounding_box.height,
                }
            })

    # Sort by confidence descending
    detections.sort(key=lambda x: x["probability"], reverse=True)
    return detections
