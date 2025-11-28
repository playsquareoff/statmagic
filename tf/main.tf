terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for the existing IAM role
data "aws_iam_role" "lambda_execution_role" {
  name = var.lambda_execution_role_name
}

# Use the built zip file directly
locals {
  lambda_zip_path = "${path.module}/../schedule_scrape/scrape_schedule_lambda.zip"
}

# Build the Lambda package before deployment
resource "null_resource" "build_lambda" {
  triggers = {
    source_hash       = filemd5("${path.module}/../schedule_scrape/scrape_schedule.py")
    requirements_hash = filemd5("${path.module}/../schedule_scrape/requirements-lambda.txt")
  }

  provisioner "local-exec" {
    command     = "cd ${path.module}/../schedule_scrape && ./build_lambda.sh"
    working_dir = path.module
  }
}

# Lambda function
resource "aws_lambda_function" "scrape_schedule" {
  filename         = local.lambda_zip_path
  function_name    = var.lambda_function_name
  role             = data.aws_iam_role.lambda_execution_role.arn
  handler          = "scrape_schedule.lambda_handler"
  source_code_hash = filebase64sha256(local.lambda_zip_path)
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      LOG_LEVEL = var.log_level
    }
  }

  # Ensure the build completes before reading the file
  depends_on = [
    null_resource.build_lambda
  ]
  
  # Prevent hash recalculation issues during plan
  lifecycle {
    create_before_destroy = true
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.log_retention_days
}

# API Gateway HTTP API
resource "aws_apigatewayv2_api" "scrape_api" {
  name          = var.api_name
  protocol_type = "HTTP"
  description   = "API Gateway for schedule scraping Lambda function"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = var.cors_allow_methods
    allow_headers = var.cors_allow_headers
  }
}

# API Gateway Integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.scrape_api.id
  integration_type = "AWS_PROXY"

  integration_method     = "POST"
  integration_uri        = aws_lambda_function.scrape_schedule.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = var.lambda_timeout * 1000
}

# API Gateway Route
resource "aws_apigatewayv2_route" "schedule_route" {
  api_id    = aws_apigatewayv2_api.scrape_api.id
  route_key = "GET /schedule"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.scrape_api.id
  name        = var.api_stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.api_name}"
  retention_in_days = var.log_retention_days
}

# Lambda permission for API Gateway to invoke the function
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scrape_schedule.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.scrape_api.execution_arn}/*/*"
}

