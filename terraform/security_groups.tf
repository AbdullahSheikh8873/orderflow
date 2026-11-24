resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "OrderFlow RDS PostgreSQL security group"
  vpc_id      = data.aws_vpc.dev.id

  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  ingress {
    description     = "PostgreSQL from API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "OrderFlow-RDS-SG"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg"
  description = "OrderFlow Lambda security group"
  vpc_id      = data.aws_vpc.dev.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "OrderFlow-Lambda-SG"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_security_group" "api" {
  name        = "${var.project_name}-api-sg"
  description = "OrderFlow API EC2 security group"
  vpc_id      = data.aws_vpc.dev.id

  ingress {
    description = "FastAPI"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "OrderFlow-API-SG"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
