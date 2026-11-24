resource "aws_s3_bucket" "orderflow" {
  bucket = "orderflow-abdullah-2026"

  tags = {
    Name        = "OrderFlow S3"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "orderflow" {
  bucket = aws_s3_bucket.orderflow.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "orderflow" {
  bucket = aws_s3_bucket.orderflow.id

  versioning_configuration {
    status = "Enabled"
  }
}
