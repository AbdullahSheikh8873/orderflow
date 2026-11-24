resource "aws_ecr_repository" "api" {
  name         = "${var.project_name}-api"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "OrderFlow API ECR"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
