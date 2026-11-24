data "aws_ami" "ubuntu" {
  most_recent = true

  owners = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "api" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  subnet_id = data.aws_subnet.public_a.id

  associate_public_ip_address = true

  key_name = var.key_name

  iam_instance_profile = aws_iam_instance_profile.api.name

  vpc_security_group_ids = [
    aws_security_group.api.id
  ]

  root_block_device {
    volume_size           = 10
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_tokens = "required"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    exec > >(tee /var/log/orderflow-user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

    apt-get update -y
    apt-get install -y docker.io

    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
    apt-get install -y unzip
    unzip -q /tmp/awscliv2.zip -d /tmp
    /tmp/aws/install

    systemctl enable --now docker

    mkdir -p /opt/orderflow

    cat > /opt/orderflow/.env <<'ENVEOF'
    DATABASE_URL=postgresql+psycopg2://orderflow:${urlencode(var.db_password)}@${aws_db_instance.orderflow.address}:5432/orderflow
    ENVIRONMENT=production
    DEBUG=false
    AWS_REGION=${var.aws_region}
    SQS_QUEUE_URL=${aws_sqs_queue.orders.url}
    SQS_DLQ_URL=${aws_sqs_queue.dlq.url}
    SNS_TOPIC_ARN=${aws_sns_topic.notifications.arn}
    S3_BUCKET_NAME=${aws_s3_bucket.orderflow.bucket}
    AWS_DISABLED=false
    ENVEOF

    aws ecr get-login-password \
      --region ${var.aws_region} | \
      docker login \
      --username AWS \
      --password-stdin ${aws_ecr_repository.api.repository_url}

    docker pull ${aws_ecr_repository.api.repository_url}:latest

    docker rm -f orderflow-api || true

    docker run -d \
      --name orderflow-api \
      --restart unless-stopped \
      -p 8000:8000 \
      --env-file /opt/orderflow/.env \
      ${aws_ecr_repository.api.repository_url}:latest
  EOF

  user_data_replace_on_change = true

  depends_on = [
    aws_db_instance.orderflow,
    aws_iam_role_policy.api,
    aws_iam_role_policy_attachment.api_ecr,
    aws_ecr_repository.api
  ]

  tags = {
    Name        = "OrderFlow-API"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
