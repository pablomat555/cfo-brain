#!/usr/bin/env python3
"""
Restore CFO database from S3/Backblaze.

Usage:
    python restore.py <s3_key> [--force]

Example:
    python restore.py cfo-brain/backups/2025/04/15/cfo_20250415_030000.db.gz
"""

import argparse
import gzip
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import boto3
from loguru import logger

from core.config import get_settings

DB_PATH = Path("/app/data/cfo.db")
BACKUP_DIR = Path("/tmp")


def validate_sqlite(filepath: Path) -> bool:
    """Check if SQLite file is valid."""
    try:
        conn = sqlite3.connect(str(filepath))
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"SQLite validation failed: {e}")
        return False


def restore_db(s3_key: str, force: bool = False) -> None:
    """Download backup from S3, decompress, replace DB."""
    settings = get_settings()

    if not settings.backup_s3_bucket:
        logger.error("BACKUP_S3_BUCKET not set, restore impossible")
        return

    # Safety: backup current DB before overwrite
    backup_current_path = DB_PATH.parent / "cfo_backup_before_restore.db"
    if DB_PATH.exists():
        logger.info(f"Backing up current DB to {backup_current_path}")
        shutil.copy2(DB_PATH, backup_current_path)
        logger.info(f"Current DB backed up to {backup_current_path}")

    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix=".db.gz", delete=False) as tmp_gz:
        tmp_gz_path = tmp_gz.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_path = tmp_db.name

    try:
        # 1. Download from S3
        logger.info(f"Downloading {s3_key} from bucket {settings.backup_s3_bucket}")
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.backup_s3_endpoint or None,
            region_name=settings.backup_s3_region or None,
            aws_access_key_id=settings.backup_s3_access_key,
            aws_secret_access_key=settings.backup_s3_secret_key,
        )

        with open(tmp_gz_path, "wb") as f:
            s3_client.download_fileobj(settings.backup_s3_bucket, s3_key, f)

        # 2. Decompress gzip
        logger.info(f"Decompressing {tmp_gz_path} -> {tmp_db_path}")
        with gzip.open(tmp_gz_path, "rb") as f_in:
            with open(tmp_db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 3. Validate SQLite
        logger.info("Validating SQLite database")
        if not validate_sqlite(Path(tmp_db_path)):
            raise ValueError("Downloaded file is not a valid SQLite database")

        # 4. Replace current DB
        if not force:
            # Ask for confirmation (in CLI)
            response = input(
                f"Are you sure you want to replace {DB_PATH} with backup {s3_key}? [y/N]: "
            )
            if response.lower() != "y":
                logger.warning("Restore cancelled by user")
                return

        logger.info(f"Replacing {DB_PATH} with restored database")
        shutil.move(tmp_db_path, DB_PATH)

        logger.success(f"Restore completed from {s3_key}")

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        # Restore from backup if possible
        if backup_current_path.exists():
            logger.info("Attempting to revert to previous DB")
            shutil.copy2(backup_current_path, DB_PATH)
            logger.info("Reverted to previous DB")
        raise
    finally:
        # Cleanup temporary files
        for path in [tmp_gz_path, tmp_db_path]:
            if os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Removed temporary file {path}")


def list_backups() -> None:
    """List available backups in S3."""
    settings = get_settings()
    if not settings.backup_s3_bucket:
        logger.error("BACKUP_S3_BUCKET not set")
        return

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.backup_s3_endpoint or None,
        region_name=settings.backup_s3_region or None,
        aws_access_key_id=settings.backup_s3_access_key,
        aws_secret_access_key=settings.backup_s3_secret_key,
    )

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.backup_s3_bucket, Prefix=settings.backup_prefix
        ):
            for obj in page.get("Contents", []):
                print(obj["Key"])
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore CFO database from S3")
    parser.add_argument(
        "s3_key", nargs="?", help="S3 key of the backup file (e.g., cfo-brain/backups/...)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available backups"
    )
    args = parser.parse_args()

    logger.add(
        "logs/restore.log",
        rotation="1 week",
        retention="1 month",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    if args.list:
        list_backups()
    elif args.s3_key:
        try:
            restore_db(args.s3_key, force=args.force)
        except Exception as e:
            logger.critical(f"Unhandled error in restore: {e}")
            exit(1)
    else:
        parser.print_help()
        exit(1)