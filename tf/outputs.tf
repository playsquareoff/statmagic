output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.scrape_schedule.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.scrape_schedule.arn
}

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_apigatewayv2_api.scrape_api.id
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.scrape_api.api_endpoint
}

output "api_gateway_invoke_url" {
  description = "Full API Gateway invoke URL"
  value       = "${aws_apigatewayv2_api.scrape_api.api_endpoint}/${aws_apigatewayv2_stage.default.name}/schedule"
}

output "cloudwatch_log_group_lambda" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "cloudwatch_log_group_api" {
  description = "CloudWatch log group for API Gateway"
  value       = aws_cloudwatch_log_group.api_logs.name
}

