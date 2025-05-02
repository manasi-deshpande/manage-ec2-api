terraform {
  backend "s3" {
    bucket = "terraform-state-912603525564"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}
