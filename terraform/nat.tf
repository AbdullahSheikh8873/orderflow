resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name        = "OrderFlow-NAT-EIP"
    Project     = "OrderFlow"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "orderflow" {
  allocation_id = aws_eip.nat.id
  subnet_id     = data.aws_subnet.public_a.id

  tags = {
    Name        = "OrderFlow-NAT-Gateway"
    Project     = "OrderFlow"
    Environment = var.environment
  }

  depends_on = [
    data.aws_vpc.dev
  ]
}

resource "aws_route" "private_nat" {
  route_table_id         = "rtb-084f82761f1d4aade"
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.orderflow.id
}
