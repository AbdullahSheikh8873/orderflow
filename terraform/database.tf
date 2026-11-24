resource "aws_db_subnet_group" "orderflow" {
  name = "${var.project_name}-db-subnet-group"

  subnet_ids = [
    data.aws_subnet.private_a.id,
    data.aws_subnet.private_b.id,
    data.aws_subnet.private_c.id
  ]

  tags = {
    Name        = "OrderFlow DB Subnet Group"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_db_instance" "orderflow" {
  identifier = "${var.project_name}-postgres"

  engine         = "postgres"
  engine_version = "16"

  instance_class        = "db.t4g.micro"
  allocated_storage     = 20
  max_allocated_storage = 20
  storage_type          = "gp3"

  db_name  = "orderflow"
  username = "orderflow"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.orderflow.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false
  multi_az            = false
  skip_final_snapshot = true
  deletion_protection = false

  backup_retention_period = 0

  tags = {
    Name        = "OrderFlow PostgreSQL"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}
