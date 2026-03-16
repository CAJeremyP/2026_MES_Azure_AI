"""
uploader.py — Azure Blob Storage upload
"""
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions


STORAGE_CONNECTION_STRING = os.environ["STORAGE_CONNECTION_STRING"]
STORAGE_CONTAINER_NAME    = os.environ.get("STORAGE_CONTAINER_NAME", "demo-images")
STORAGE_ACCOUNT_NAME      = os.environ["STORAGE_ACCOUNT_NAME"]


def upload_image(image_path: Path) -> str:
    """
    Upload an image to Azure Blob Storage.
    Returns the blob URL (with SAS token for reading).
    """
    client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container = client.get_container_client(STORAGE_CONTAINER_NAME)

    # Ensure container exists
    try:
        container.create_container()
    except Exception:
        pass   # Already exists

    # Generate a unique blob name using timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"{timestamp}_{image_path.name}"
    blob_client = container.get_blob_client(blob_name)

    with open(image_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    # Return the blob URL (no SAS needed since Custom Vision/DocIntel
    # accept raw bytes — but URL is useful for logging/reporting)
    return blob_client.url
