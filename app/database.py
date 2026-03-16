"""
database.py — Azure Cosmos DB (NoSQL) integration
==================================================
Replaces Azure SQL. Cosmos DB:
  - Has no regional provisioning restrictions
  - Free tier: 1000 RU/s + 25 GB = $0/month
  - No ODBC driver required — pure Python SDK
  - Uses serverless mode as fallback if free tier unavailable

Schema (all stored as JSON documents in 'pipeline_runs' container):
  {
    "id":           "<run_id>",          # Cosmos DB required field
    "run_id":       "<run_id>",          # partition key
    "image_name":   "circle_01.png",
    "blob_url":     "https://...",
    "created_at":   "2025-12-01T10:00:00Z",
    "vision": [
      { "tag": "circle", "probability": 0.97, "bounding_box": {...} }
    ],
    "ocr_lines": [
      { "line_number": 1, "content": "Hello world", "page": 1 }
    ]
  }
"""
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "azure-cosmos"])
    from azure.cosmos import CosmosClient, PartitionKey, exceptions

from tabulate import tabulate

COSMOS_ENDPOINT   = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY        = os.environ["COSMOS_KEY"]
COSMOS_DB_NAME    = os.environ.get("COSMOS_DATABASE_NAME", "aidemodb")
COSMOS_CONTAINER  = "pipeline_runs"


class DatabaseClient:
    def __init__(self):
        print("  🔌  Connecting to Azure Cosmos DB...")
        self.client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        self.db         = self.client.get_database_client(COSMOS_DB_NAME)
        self.container  = self.db.get_container_client(COSMOS_CONTAINER)
        print("  ✅  Connected.")

    def ensure_tables(self):
        """
        Cosmos DB containers are created by Bicep at deploy time.
        This method verifies the container is reachable and prints
        a confirmation — mirrors the SQL ensure_tables() interface.
        """
        try:
            props = self.container.read()
            print(f"  ✅  Container '{COSMOS_CONTAINER}' ready.")
        except exceptions.CosmosResourceNotFoundError:
            # Shouldn't happen after deploy, but handle gracefully
            print(f"  ⚠️   Container not found — creating '{COSMOS_CONTAINER}'...")
            self.db.create_container(
                id=COSMOS_CONTAINER,
                partition_key=PartitionKey(path="/run_id")
            )
            print(f"  ✅  Container created.")

    def insert_run(self, run_id: str, image_name: str, blob_url: str) -> str:
        """
        Insert a new pipeline run document.
        Returns the run_id (used as the document ID in Cosmos).
        """
        doc = {
            "id":         run_id,       # Cosmos DB required unique field
            "run_id":     run_id,       # partition key
            "image_name": image_name,
            "blob_url":   blob_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "vision":     [],
            "ocr_lines":  [],
        }
        self.container.create_item(body=doc)
        return run_id

    def insert_vision_results(self, run_id: str, detections: list):
        if not detections:
            return
        # Patch the existing document — append vision results
        doc = self.container.read_item(item=run_id, partition_key=run_id)
        doc["vision"] = detections
        self.container.replace_item(item=run_id, body=doc)
        print(f"  ✅  Saved {len(detections)} vision detection(s).")

    def insert_doc_results(self, run_id: str, lines: list):
        if not lines:
            return
        doc = self.container.read_item(item=run_id, partition_key=run_id)
        doc["ocr_lines"] = [
            {
                "line_number": i + 1,
                "content":     line["content"],
                "page":        line.get("page", 1),
                "polygon":     line.get("polygon"),
            }
            for i, line in enumerate(lines)
        ]
        self.container.replace_item(item=run_id, body=doc)
        print(f"  ✅  Saved {len(lines)} OCR line(s).")

    def print_run_summary(self, run_id: str):
        doc = self.container.read_item(item=run_id, partition_key=run_id)

        vision = doc.get("vision", [])
        if vision:
            rows = [
                (
                    d["tag"],
                    f"{d['probability']:.1%}",
                    f"{d.get('bounding_box',{}).get('left',0):.3f}",
                    f"{d.get('bounding_box',{}).get('top',0):.3f}",
                    f"{d.get('bounding_box',{}).get('width',0):.3f}",
                    f"{d.get('bounding_box',{}).get('height',0):.3f}",
                )
                for d in vision
            ]
            print("\n  Custom Vision Detections:")
            print(tabulate(rows,
                headers=["Tag", "Confidence", "Left", "Top", "Width", "Height"],
                tablefmt="rounded_outline"))

        lines = doc.get("ocr_lines", [])
        if lines:
            rows = [(l["line_number"], l["content"], l.get("page", 1)) for l in lines]
            print("\n  Document Intelligence Lines:")
            print(tabulate(rows,
                headers=["Line #", "Text", "Page"],
                tablefmt="rounded_outline"))

    def list_recent_runs(self, limit: int = 5):
        """Print the most recent pipeline runs stored in Cosmos."""
        items = list(self.container.query_items(
            query="SELECT c.run_id, c.image_name, c.created_at FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit",
            parameters=[{"name": "@limit", "value": limit}],
            enable_cross_partition_query=True
        ))
        if items:
            rows = [(i["run_id"], i["image_name"], i["created_at"]) for i in items]
            print(tabulate(rows, headers=["Run ID", "Image", "Created At"], tablefmt="rounded_outline"))
        else:
            print("  No runs found.")

    def close(self):
        pass  # CosmosClient has no explicit close needed
