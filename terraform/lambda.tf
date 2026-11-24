resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "order_processor" {
  function_name = "${var.project_name}-order-processor"

  role    = aws_iam_role.lambda.arn
  handler = "handler.handler"
  runtime = "python3.12"

  filename         = "${path.module}/../order_processor.zip"
  source_code_hash = filebase64sha256("${path.module}/../order_processor.zip")

  timeout     = 30
  memory_size = 256

  vpc_config {
    subnet_ids = [
      data.aws_subnet.private_a.id,
      data.aws_subnet.private_b.id,
      data.aws_subnet.private_c.id
    ]

    security_group_ids = [
      aws_security_group.lambda.id
    ]
  }

  environment {
    variables = {
      DATABASE_URL = "postgresql+psycopg2://orderflow:${urlencode(var.db_password)}@${aws_db_instance.orderflow.address}:5432/orderflow"

      SNS_TOPIC_ARN  = aws_sns_topic.notifications.arn
      S3_BUCKET_NAME = aws_s3_bucket.orderflow.bucket

      AWS_DISABLED = "false"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_nat_gateway.orderflow,
    aws_route.private_nat
  ]

  tags = {
    Name        = "OrderFlow Lambda"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_lambda_event_source_mapping" "orders" {
  event_source_arn = aws_sqs_queue.orders.arn
  function_name    = aws_lambda_function.order_processor.arn

  batch_size = 10

  function_response_types = [
    "ReportBatchItemFailures"
  ]

  enabled = true

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_iam_role_policy_attachment.lambda_vpc
  ]
}
