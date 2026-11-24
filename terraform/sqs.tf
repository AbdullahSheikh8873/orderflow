resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-dlq"

  tags = {
    Name        = "OrderFlow DLQ"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "orders" {
  name = "${var.project_name}-orders"

  visibility_timeout_seconds = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "OrderFlow Orders Queue"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
