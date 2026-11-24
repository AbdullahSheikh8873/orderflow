variable "aws_region" {
  description = "AWS region for OrderFlow"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "orderflow"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "db_password" {
  description = "Password for the OrderFlow PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "key_name" {
  description = "EC2 SSH key pair"
  type        = string
  default     = "DEV-PEM-KP"
}
