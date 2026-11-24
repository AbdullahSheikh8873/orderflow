"""
Unit tests for the thin AWS wrapper modules. boto3 is always mocked here --
these tests never make a real network call, per the project requirement
that AWS services are mocked in unit tests.
"""
from unittest.mock import MagicMock, patch

from app.aws import s3 as aws_s3
from app.aws import sns as aws_sns
from app.aws import sqs as aws_sqs


def test_sqs_send_order_event_noop_when_aws_disabled():
    with patch.object(aws_sqs.settings, "aws_disabled", True):
        result = aws_sqs.send_order_event("ORDER_CREATED", order_id=1, user_id=1, order_number="ORD-1")
    assert result is None


def test_sqs_send_order_event_calls_boto3_when_enabled():
    aws_sqs._client = None
    fake_client = MagicMock()
    fake_client.send_message.return_value = {"MessageId": "abc-123"}

    with patch.object(aws_sqs.settings, "aws_disabled", False), \
         patch.object(aws_sqs.settings, "sqs_queue_url", "https://sqs.example.com/queue"), \
         patch("boto3.client", return_value=fake_client):
        message_id = aws_sqs.send_order_event("ORDER_CREATED", order_id=5, user_id=9, order_number="ORD-5")

    assert message_id == "abc-123"
    fake_client.send_message.assert_called_once()
    _, kwargs = fake_client.send_message.call_args
    assert kwargs["QueueUrl"] == "https://sqs.example.com/queue"
    assert "ORD-5" in kwargs["MessageBody"]
    aws_sqs._client = None


def test_sqs_send_order_event_handles_boto3_errors_gracefully():
    aws_sqs._client = None
    fake_client = MagicMock()
    fake_client.send_message.side_effect = RuntimeError("network error")

    with patch.object(aws_sqs.settings, "aws_disabled", False), \
         patch.object(aws_sqs.settings, "sqs_queue_url", "https://sqs.example.com/queue"), \
         patch("boto3.client", return_value=fake_client):
        result = aws_sqs.send_order_event("ORDER_CREATED", order_id=1, user_id=1, order_number="ORD-1")

    assert result is None
    aws_sqs._client = None


def test_sns_publish_order_event_noop_when_disabled():
    with patch.object(aws_sns.settings, "aws_disabled", True):
        result = aws_sns.publish_order_event("ORDER_CONFIRMED", 1, "ORD-1", "CONFIRMED")
    assert result is None


def test_sns_publish_order_event_calls_boto3_when_enabled():
    aws_sns._client = None
    fake_client = MagicMock()
    fake_client.publish.return_value = {"MessageId": "sns-123"}

    with patch.object(aws_sns.settings, "aws_disabled", False), \
         patch.object(aws_sns.settings, "sns_topic_arn", "arn:aws:sns:us-east-1:123:order-events"), \
         patch("boto3.client", return_value=fake_client):
        message_id = aws_sns.publish_order_event("ORDER_CONFIRMED", 1, "ORD-1", "CONFIRMED")

    assert message_id == "sns-123"
    fake_client.publish.assert_called_once()
    aws_sns._client = None


def test_s3_store_invoice_noop_returns_key_when_disabled():
    with patch.object(aws_s3.settings, "aws_disabled", True):
        key = aws_s3.store_invoice("ORD-1", {"total": "10.00"})
    assert key == aws_s3.build_order_key("ORD-1", "invoice.json")


def test_s3_put_json_calls_boto3_when_enabled():
    aws_s3._client = None
    fake_client = MagicMock()

    with patch.object(aws_s3.settings, "aws_disabled", False), \
         patch.object(aws_s3.settings, "s3_bucket_name", "orderflow-documents"), \
         patch("boto3.client", return_value=fake_client):
        key = aws_s3.put_json("orders/2026/09/ORD-1/invoice.json", {"total": "10.00"})

    assert key == "orders/2026/09/ORD-1/invoice.json"
    fake_client.put_object.assert_called_once()
    _, kwargs = fake_client.put_object.call_args
    assert kwargs["Bucket"] == "orderflow-documents"
    assert kwargs["Key"] == "orders/2026/09/ORD-1/invoice.json"
    aws_s3._client = None


def test_build_order_key_layout():
    from datetime import datetime, timezone

    when = datetime(2026, 9, 7, tzinfo=timezone.utc)
    key = aws_s3.build_order_key("ORD-2026-000123", "invoice.json", when=when)
    assert key == "orders/2026/09/ORD-2026-000123/invoice.json"
