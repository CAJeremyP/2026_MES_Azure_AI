"""
database.py — Azure SQL Database integration
Creates tables and persists pipeline results.

Uses pyodbc with ODBC Driver 18 for SQL Server.
Install driver: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
"""
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

try:
    import pyodbc
except ImportError:
    raise ImportError(
        "pyodbc not installed. Run: pip install pyodbc\n"
        "Also install ODBC Driver 18 from Microsoft."
    )

from tabulate import tabulate

SQL_CONNECTION_STRING = os.environ.get("SQL_CONNECTION_STRING", "")
SQL_SERVER_NAME      = os.environ.get("SQL_SERVER_NAME", "")
SQL_DATABASE_NAME    = os.environ.get("SQL_DATABASE_NAME", "aidemodb")
SQL_ADMIN_USER       = os.environ.get("SQL_ADMIN_USER", "demoadmin")
SQL_ADMIN_PASSWORD   = os.environ.get("SQL_ADMIN_PASSWORD", "")


DDL_RUNS = """
IF NOT EXISTS (
    SELECT * FROM sys.tables WHERE name = 'pipeline_runs'
)
CREATE TABLE pipeline_runs (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    run_id        NVARCHAR(50)  NOT NULL,
    image_name    NVARCHAR(500) NOT NULL,
    blob_url      NVARCHAR(2000),
    created_at    DATETIME2     DEFAULT GETUTCDATE()
);
"""

DDL_VISION = """
IF NOT EXISTS (
    SELECT * FROM sys.tables WHERE name = 'vision_detections'
)
CREATE TABLE vision_detections (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    run_id        INT           NOT NULL REFERENCES pipeline_runs(id),
    tag           NVARCHAR(100) NOT NULL,
    probability   FLOAT         NOT NULL,
    bbox_left     FLOAT,
    bbox_top      FLOAT,
    bbox_width    FLOAT,
    bbox_height   FLOAT,
    created_at    DATETIME2     DEFAULT GETUTCDATE()
);
"""

DDL_DOC = """
IF NOT EXISTS (
    SELECT * FROM sys.tables WHERE name = 'doc_intel_lines'
)
CREATE TABLE doc_intel_lines (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    run_id        INT           NOT NULL REFERENCES pipeline_runs(id),
    line_number   INT           NOT NULL,
    content       NVARCHAR(MAX) NOT NULL,
    page_number   INT,
    polygon_json  NVARCHAR(MAX),
    created_at    DATETIME2     DEFAULT GETUTCDATE()
);
"""


class DatabaseClient:
    def __init__(self):
        conn_str = SQL_CONNECTION_STRING
        if not conn_str:
            # Build from parts
            conn_str = (
                f"Driver={{ODBC Driver 18 for SQL Server}};"
                f"Server=tcp:{SQL_SERVER_NAME},1433;"
                f"Database={SQL_DATABASE_NAME};"
                f"Uid={SQL_ADMIN_USER};"
                f"Pwd={SQL_ADMIN_PASSWORD};"
                f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
            )

        print("  🔌  Connecting to Azure SQL...")
        print("      (First connection may take ~60s if database is paused/cold)")
        self.conn = pyodbc.connect(conn_str, timeout=90)
        self.conn.autocommit = False
        print("  ✅  Connected.")

    def ensure_tables(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        for ddl in [DDL_RUNS, DDL_VISION, DDL_DOC]:
            cursor.execute(ddl)
        self.conn.commit()
        print("  ✅  Database tables ready.")

    def insert_run(self, run_id: str, image_name: str, blob_url: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO pipeline_runs (run_id, image_name, blob_url) "
            "OUTPUT INSERTED.id VALUES (?, ?, ?)",
            run_id, image_name, blob_url
        )
        row = cursor.fetchone()
        self.conn.commit()
        return row[0]

    def insert_vision_results(self, run_db_id: int, detections: list):
        if not detections:
            return
        cursor = self.conn.cursor()
        for d in detections:
            bb = d.get("bounding_box", {})
            cursor.execute(
                "INSERT INTO vision_detections "
                "(run_id, tag, probability, bbox_left, bbox_top, bbox_width, bbox_height) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                run_db_id,
                d["tag"],
                d["probability"],
                bb.get("left"), bb.get("top"), bb.get("width"), bb.get("height")
            )
        self.conn.commit()
        print(f"  ✅  Saved {len(detections)} vision detection(s).")

    def insert_doc_results(self, run_db_id: int, lines: list):
        if not lines:
            return
        cursor = self.conn.cursor()
        for i, line in enumerate(lines):
            cursor.execute(
                "INSERT INTO doc_intel_lines "
                "(run_id, line_number, content, page_number, polygon_json) "
                "VALUES (?, ?, ?, ?, ?)",
                run_db_id,
                i + 1,
                line["content"],
                line.get("page"),
                json.dumps(line.get("polygon")) if line.get("polygon") else None
            )
        self.conn.commit()
        print(f"  ✅  Saved {len(lines)} OCR line(s).")

    def print_run_summary(self, run_db_id: int):
        cursor = self.conn.cursor()

        # Vision detections
        cursor.execute(
            "SELECT tag, ROUND(probability*100,1) AS pct, "
            "ROUND(bbox_left,3), ROUND(bbox_top,3), "
            "ROUND(bbox_width,3), ROUND(bbox_height,3) "
            "FROM vision_detections WHERE run_id = ? ORDER BY probability DESC",
            run_db_id
        )
        rows = cursor.fetchall()
        if rows:
            print("\n  Custom Vision Detections:")
            print(tabulate(rows,
                headers=["Tag", "Confidence %", "Left", "Top", "Width", "Height"],
                tablefmt="rounded_outline"))

        # OCR lines
        cursor.execute(
            "SELECT line_number, content FROM doc_intel_lines "
            "WHERE run_id = ? ORDER BY line_number",
            run_db_id
        )
        rows = cursor.fetchall()
        if rows:
            print("\n  Document Intelligence Lines:")
            print(tabulate(rows, headers=["Line #", "Text"], tablefmt="rounded_outline"))

    def close(self):
        self.conn.close()
