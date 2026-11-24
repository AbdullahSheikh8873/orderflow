"""
Thin wrapper around AWS S3. Used to store order invoices, order-event JSON
files and processing/audit logs. PostgreSQL never stores these blobs
directly -- only the resulting S3 object key is written back onto the
`order_events` row so the UI can link out to the document.

Object key layout:

    orders/{year}/{month:02d}/{order_number}/invoice.json
    orders/{year}/{month:02d}/{order_number}/order-event.json
    orders/{year}/{month:02d}/{order_number}/processing-log.json
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3

from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger("aws.s3")
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url or None,
        )
    return _client


def build_order_key(order_number: str, filename: str, when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"orders/{when.year}/{when.month:02d}/{order_number}/{filename}"


def put_json(key: str, payload: Dict[str, Any]) -> Optional[str]:
    """
    Upload a JSON document to S3. Returns the object key on success (or on
    AWS_DISABLED, so callers can still persist the "would-be" key for
    traceability), or None if a real upload failed.
    """
    body = json.dumps(payload, default=str, indent=2)

    if settings.aws_disabled or not settings.s3_bucket_name:
        logger.info("S3_DISABLED - would upload object", extra={"data": {"key": key}})
        return key

    try:
        client = _get_client()
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded object to S3", extra={"data": {"bucket": settings.s3_bucket_name, "key": key}})
        return key
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to upload object to S3", extra={"data": {"error": str(exc), "key": key}})
        return None


def get_object_url(key: str) -> str:
    """Best-effort console/virtual-hosted-style URL for display purposes only."""
    bucket = settings.s3_bucket_name or "orderflow-documents"
    return f"https://{bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def store_invoice(order_number: str, invoice_payload: Dict[str, Any]) -> Optional[str]:
    key = build_order_key(order_number, "invoice.json")
    return put_json(key, invoice_payload)


def store_order_event(order_number: str, event_payload: Dict[str, Any]) -> Optional[str]:
    key = build_order_key(order_number, "order-event.json")
    return put_json(key, event_payload)


def store_processing_log(order_number: str, log_payload: Dict[str, Any]) -> Optional[str]:
    key = build_order_key(order_number, "processing-log.json")
    return put_json(key, log_payload)
