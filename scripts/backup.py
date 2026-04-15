#!/usr/bin/env python3
"""
Backup CFO database to S3/Backblaze.

Usage:
    python backup.py

Environment variables:
    BACKUP_S3_BUCKET
    BACKUP_S3_REGION
    BACKUP_S3_ACCESS_KEY
    BACKUP_S3_SECRET_KEY
    BACKUP_S3_ENDPOINT
    BACKUP_PREFIX (default: cfo-brain/backups)
"""

import gzip
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import boto3
from loguru import logger

from core.config import get_settings

# Database path inside container
DB_PATH = Path("/app/data/cfo.db")
BACKUP_DIR = Path("/tmp")


def backup_db() -> None:
    """Copy DB, compress, upload to S3."""
    settings = get_settings()

    # Validate required settings
    if not settings.backup_s3_bucket:
        logger.error("BACKUP_S3_BUCKET not set, backup skipped")
        return

    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    backup_filename = f"cfo_{timestamp}.db.gz"
    s3_key = f"{settings.backup_prefix}/{date_prefix}/{backup_filename}"

    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_path = tmp_db.name
    with tempfile.NamedTemporaryFile(suffix=".db.gz", delete=False) as tmp_gz:
        tmp_gz_path = tmp_gz.name

    try:
        # 1. Copy DB (to avoid locking)
        logger.info(f"Copying database from {DB_PATH} to temporary file")
        shutil.copy2(DB_PATH, tmp_db_path)

        # 2. Compress with gzip
        logger.info(f"Compressing {tmp_db_path} -> {tmp_gz_path}")
        with open(tmp_db_path, "rb") as f_in:
            with gzip.open(tmp_gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 3. Upload to S3
        logger.info(f"Uploading to S3 bucket {settings.backup_s3_bucket}, key {s3_key}")
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.backup_s3_endpoint or None,
            region_name=settings.backup_s3_region or None,
            aws_access_key_id=settings.backup_s3_access_key,
            aws_secret_access_key=settings.backup_s3_secret_key,
        )

        with open(tmp_gz_path, "rb") as f:
            s3_client.upload_fileobj(f, settings.backup_s3_bucket, s3_key)

        logger.success(f"Backup completed: {s3_key}")

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise
    finally:
        # Cleanup temporary files
        for path in [tmp_db_path, tmp_gz_path]:
            if os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Removed temporary file {path}")


if __name__ == "__main__":
    logger.add(
        "logs/backup.log",
        rotation="1 week",
        retention="1 month",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    try:
        backup_db()
    except Exception as e:
        logger.critical(f"Unhandled error in backup: {e}")
        exit(1)