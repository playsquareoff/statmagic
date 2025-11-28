#!/bin/bash
# Script to import existing AWS resources into Terraform
# Run this if you already have the Lambda function and API Gateway created

set -e

echo "Importing existing AWS resources into Terraform..."
echo "=================================================="

# Get the API Gateway ID from the endpoint
API_ID="lf7a6w0f7g"
FUNCTION_NAME="scrape-schedule"

# Get integration and route IDs
echo "Fetching API Gateway details..."
INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id "$API_ID" --query "Items[?contains(IntegrationUri, 'scrape-schedule')].IntegrationId" --output text)
ROUTE_ID=$(aws apigatewayv2 get-routes --api-id "$API_ID" --query "Items[?RouteKey=='GET /schedule'].RouteId" --output text)

echo "API Gateway ID: $API_ID"
echo "Integration ID: $INTEGRATION_ID"
echo "Route ID: $ROUTE_ID"
echo ""

# Import Lambda function
echo "Importing Lambda function..."
terraform import aws_lambda_function.scrape_schedule "$FUNCTION_NAME" || echo "Lambda function may already be imported or doesn't exist"

# Import API Gateway
echo "Importing API Gateway..."
terraform import aws_apigatewayv2_api.scrape_api "$API_ID" || echo "API Gateway may already be imported"

# Import Integration
if [ -n "$INTEGRATION_ID" ]; then
  echo "Importing API Gateway integration..."
  terraform import aws_apigatewayv2_integration.lambda_integration "$API_ID/$INTEGRATION_ID" || echo "Integration may already be imported"
else
  echo "Warning: Could not find integration ID"
fi

# Import Route
if [ -n "$ROUTE_ID" ]; then
  echo "Importing API Gateway route..."
  terraform import aws_apigatewayv2_route.schedule_route "$API_ID/$ROUTE_ID" || echo "Route may already be imported"
else
  echo "Warning: Could not find route ID"
fi

# Import Stage
echo "Importing API Gateway stage..."
terraform import aws_apigatewayv2_stage.default "$API_ID/\$default" || echo "Stage may already be imported"

# Import CloudWatch log groups (if they exist)
echo "Importing CloudWatch log groups..."
terraform import aws_cloudwatch_log_group.lambda_logs "/aws/lambda/$FUNCTION_NAME" 2>/dev/null || echo "Lambda log group may not exist yet"
terraform import aws_cloudwatch_log_group.api_logs "/aws/apigateway/scrape" 2>/dev/null || echo "API log group may not exist yet"

echo ""
echo "=================================================="
echo "Import complete!"
echo ""
echo "Next steps:"
echo "  1. Run: terraform plan"
echo "  2. Review the plan to ensure everything matches"
echo "  3. Run: terraform apply (if needed)"
echo "=================================================="

