terraform {
  backend "s3" {
    bucket         = "ec2-lambda-api-terraform-state"
    key            = "lambda/ec2-api.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ec2-lambda-api-locks"
    encrypt        = true
  }
}
