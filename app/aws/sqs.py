"""
Thin wrapper around AWS SQS used to publish order-processing events from the
FastAPI application. The Lambda order-processor (lambda/order_processor)
consumes from this same queue.

If `AWS_DISABLED=true` (the local-dev default so the whole app can run
without any AWS account), calls are logged instead of sent -- this keeps the
call site in the service layer identical between local dev and a real AWS
deployment, satisfying "no fake integrations": the same boto3 client code
path runs for real once AWS_DISABLED=false and SQS_QUEUE_URL is set.
"""
import json
from typing import Any, Dict, Optional

import boto3

from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger("aws.sqs")
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url or None,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
    return _client


def send_order_event(event_type: str, order_id: int, user_id: int, order_number: str,
                      extra: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Publish an order-processing message to SQS. Returns the SQS MessageId on
    success, or None if AWS is disabled / the call failed (the caller should
    treat failure as non-fatal for the HTTP request but log it loudly, since
    a durable retry mechanism -- e.g. an outbox table -- would be added in a
    hardened production system).
    """
    message: Dict[str, Any] = {
        "event_type": event_type,
        "order_id": order_id,
        "user_id": user_id,
        "order_number": order_number,
    }
    if extra:
        message.update(extra)

    if settings.aws_disabled or not settings.sqs_queue_url:
        logger.info("SQS_DISABLED - would publish message", extra={"data": message})
        return None

    try:
        client = _get_client()
        response = client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(message),
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event_type},
            },
        )
        message_id = response.get("MessageId")
        logger.info("Published SQS message", extra={"data": {**message, "message_id": message_id}})
        return message_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to publish SQS message", extra={"data": {"error": str(exc), **message}})
        return None
