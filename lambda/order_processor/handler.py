"""
AWS Lambda entrypoint for the OrderFlow order-processor.

Trigger: an SQS event source mapping on the `orderflow-order-events` queue.
On repeated failure, SQS's redrive policy moves the message to the
`orderflow-order-events-dlq` Dead Letter Queue (configured on the queue
itself, not in this code) after `maxReceiveCount` attempts.

This handler uses SQS's "partial batch failure" response format
(`batchItemFailures`) so that only the messages which genuinely failed are
retried/redriven -- successfully processed messages in the same batch are
never reprocessed.

Deployment: this file (plus lambda/order_processor/services and the shared
`app` package for models/database/aws clients) is packaged into the Lambda
deployment zip. See README.md "Lambda deployment" section.
"""
import json
import os
import sys
from typing import Any, Dict

# `lambda` is a reserved Python keyword, so this package can never be
# imported with a normal dotted `import lambda.order_processor...`
# statement. We instead add both this directory (so `services.processing`
# resolves the same way whether the deployment zip has this folder as its
# root, which is how AWS Lambda actually runs it) and the repository root
# (so the shared `app` package resolves during local development / tests)
# to sys.path explicitly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
for _path in (_THIS_DIR, _REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from app.core.logging_config import configure_logging, get_logger  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from services.processing import OrderProcessingError, process_order_message  # noqa: E402

configure_logging("INFO")
logger = get_logger("lambda.order_processor.handler")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Standard AWS Lambda handler signature: (event, context) -> response."""
    records = event.get("Records", [])
    logger.info("Received SQS batch", extra={"data": {"record_count": len(records)}})

    batch_item_failures = []

    for record in records:
        message_id = record.get("messageId")
        try:
            body = json.loads(record.get("body", "{}"))
        except json.JSONDecodeError:
            logger.error("Malformed SQS message body, sending to DLQ", extra={"data": {"message_id": message_id}})
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        db = SessionLocal()
        try:
            result = process_order_message(db, message_id, body)
            logger.info("Message processed", extra={"data": {"message_id": message_id, "result": result}})
        except OrderProcessingError as exc:
            logger.error(
                "Order processing failed, message will be retried / eventually DLQ'd",
                extra={"data": {"message_id": message_id, "error": str(exc)}},
            )
            db.rollback()
            batch_item_failures.append({"itemIdentifier": message_id})
        except Exception as exc:  # noqa: BLE001 - guard against unexpected errors so the batch keeps moving
            logger.exception("Unexpected error processing SQS message", extra={"data": {"message_id": message_id}})
            db.rollback()
            batch_item_failures.append({"itemIdentifier": message_id})
        finally:
            db.close()

    return {"batchItemFailures": batch_item_failures}
