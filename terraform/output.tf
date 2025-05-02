output "ec2_lambda_function_name" {
  description = "Name of the EC2 management Lambda function"
  value       = aws_lambda_function.ec2_api.function_name
}


output "api_gateway_endpoint" {
  description = "Base URL of the deployed API Gateway"
  value       = aws_apigatewayv2_stage.dev.invoke_url
}
