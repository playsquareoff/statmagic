variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "scrape-schedule"
}

variable "lambda_execution_role_name" {
  description = "Name of the IAM role for Lambda execution"
  type        = string
  default     = "scrape-scores-lambda-role"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "log_level" {
  description = "Log level for Lambda function"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "api_name" {
  description = "Name of the API Gateway HTTP API"
  type        = string
  default     = "scrape"
}

variable "api_stage_name" {
  description = "Name of the API Gateway stage"
  type        = string
  default     = "$default"
}

variable "cors_allow_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allow_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "POST", "OPTIONS"]
}

variable "cors_allow_headers" {
  description = "CORS allowed headers"
  type        = list(string)
  default     = ["content-type", "x-amz-date", "authorization", "x-api-key"]
}

