data "aws_vpc" "dev" {
  id = "vpc-0e63acc374dd13e17"
}

data "aws_subnet" "public_a" {
  id = "subnet-09bd45133cdb3c880"
}

data "aws_subnet" "public_b" {
  id = "subnet-0be2fdb168b0e927a"
}

data "aws_subnet" "public_c" {
  id = "subnet-01d849b13473bad6f"
}

data "aws_subnet" "private_a" {
  id = "subnet-0da14191b866530e3"
}

data "aws_subnet" "private_b" {
  id = "subnet-0ea93051eefce2ed6"
}

data "aws_subnet" "private_c" {
  id = "subnet-0a977b8d3f5639a68"
}
