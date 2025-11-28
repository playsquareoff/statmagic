# Terraform Configuration for Schedule Scrape Lambda

This directory contains Terraform configuration to manage the `scrape-schedule` Lambda function and API Gateway.

## Prerequisites

1. **Terraform installed** (>= 1.0)
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **AWS CLI configured** with appropriate credentials
   ```bash
   aws configure
   ```

3. **Lambda package built**
   ```bash
   cd ../schedule_scrape
   ./build_lambda.sh
   ```

## Quick Start

1. **Build the Lambda package first** (required before running terraform plan)
   ```bash
   cd ../schedule_scrape
   ./build_lambda.sh
   cd ../tf
   ```

2. **Initialize Terraform**
   ```bash
   terraform init
   ```

3. **Review the plan**
   ```bash
   terraform plan
   ```

4. **Apply the configuration**
   ```bash
   terraform apply
   ```

**Note:** If you get an error about `filebase64sha256` returning an inconsistent result, make sure the zip file exists by running the build script first.

4. **View outputs**
   ```bash
   terraform output
   ```

## Importing Existing Resources

If you already have the Lambda function and API Gateway created manually, you can import them:

```bash
# Import Lambda function
terraform import aws_lambda_function.scrape_schedule scrape-schedule

# Import API Gateway
terraform import aws_apigatewayv2_api.scrape_api lf7a6w0f7g

# Import API Gateway integration
terraform import aws_apigatewayv2_integration.lambda_integration lf7a6w0f7g/ccgesjs

# Import API Gateway route
terraform import aws_apigatewayv2_route.schedule_route lf7a6w0f7g/uucf26b

# Import API Gateway stage
terraform import aws_apigatewayv2_stage.default lf7a6w0f7g/\$default

# Import CloudWatch log groups
terraform import aws_cloudwatch_log_group.lambda_logs /aws/lambda/scrape-schedule
terraform import aws_cloudwatch_log_group.api_logs /aws/apigateway/scrape
```

## Configuration

### Variables

Copy `terraform.tfvars.example` to `terraform.tfvars` and customize:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Key variables:
- `aws_region`: AWS region (default: us-west-2)
- `lambda_function_name`: Name of Lambda function
- `lambda_execution_role_name`: IAM role name for Lambda
- `lambda_timeout`: Function timeout in seconds
- `lambda_memory_size`: Memory allocation in MB
- `api_name`: API Gateway name
- `log_retention_days`: CloudWatch log retention

### Building Lambda Package

The Terraform configuration automatically builds the Lambda package before deployment. It triggers the build script when:
- `scrape_schedule.py` changes
- `requirements-lambda.txt` changes

## Deployment Workflow

1. **Make changes** to `scrape_schedule.py` or requirements
2. **Run Terraform**
   ```bash
   terraform plan   # Review changes
   terraform apply  # Deploy
   ```
3. Terraform will automatically rebuild the Lambda package if source files changed

## Manual Deployment

If you prefer to build manually:

```bash
cd ../schedule_scrape
./build_lambda.sh
cd ../tf
terraform apply
```

## Outputs

After deployment, view outputs:

```bash
terraform output
```

This shows:
- Lambda function ARN
- API Gateway endpoint URL
- Full invoke URL
- CloudWatch log group names

## Testing

After deployment, test the endpoint:

```bash
# Get the API endpoint
API_URL=$(terraform output -raw api_gateway_invoke_url)

# Test with query parameters
curl "${API_URL}?team_slug=dal&team_name_long=dallas-cowboys"
```

## Destroying Resources

To remove all resources:

```bash
terraform destroy
```

**Warning:** This will delete the Lambda function, API Gateway, and CloudWatch log groups.

## Troubleshooting

### Build fails
- Ensure `build_lambda.sh` is executable: `chmod +x ../schedule_scrape/build_lambda.sh`
- Check that Python dependencies are installed

### Import errors
- Verify resource names match exactly
- Check AWS credentials and permissions

### Lambda update fails
- Ensure the zip file exists in `build_lambda/` directory
- Check Lambda function permissions

## File Structure

```
tf/
├── main.tf              # Main Terraform resources
├── variables.tf         # Variable definitions
├── outputs.tf           # Output values
├── terraform.tfvars.example  # Example configuration
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Notes

- The Lambda package is built automatically before Terraform creates/updates the function
- CloudWatch logs are configured with 7-day retention (configurable)
- CORS is enabled by default (configurable via variables)
- The API Gateway uses HTTP API (not REST API) for better performance and lower cost

