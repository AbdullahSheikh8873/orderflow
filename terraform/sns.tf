resource "aws_sns_topic" "notifications" {
  name = "${var.project_name}-notifications"

  tags = {
    Name        = "OrderFlow Notifications"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
