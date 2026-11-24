"""
Thin wrapper around AWS SNS. Used by the Lambda order-processor (and
optionally the FastAPI app) to publish order lifecycle events to the
`order-events` topic. Any number of subscribers (email via SES, SMS, another
SQS queue, a webhook Lambda, etc.) can be attached to this topic later
without touching the order-processing logic itself.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3

from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger("aws.sns")
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "sns",
            endpoint_url=settings.aws_endpoint_url or None,
        )
    return _client


def publish_order_event(event_type: str, order_id: int, order_number: str, status: str,
                         extra: Optional[Dict[str, Any]] = None) -> Optional[str]:
    message: Dict[str, Any] = {
        "event_type": event_type,
        "order_id": order_id,
        "order_number": order_number,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        message.update(extra)

    if settings.aws_disabled or not settings.sns_topic_arn:
        logger.info("SNS_DISABLED - would publish notification", extra={"data": message})
        return None

    try:
        client = _get_client()
        response = client.publish(
            TopicArn=settings.sns_topic_arn,
            Message=json.dumps(message),
            Subject=f"OrderFlow: {event_type}",
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event_type},
            },
        )
        message_id = response.get("MessageId")
        logger.info("Published SNS notification", extra={"data": {**message, "message_id": message_id}})
        return message_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to publish SNS notification", extra={"data": {"error": str(exc), **message}})
        return None
