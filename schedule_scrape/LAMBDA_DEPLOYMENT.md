# AWS Lambda Deployment Guide

This guide explains how to deploy `scrape_schedule.py` to AWS Lambda.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.9+ (for building the package)
- pip installed

## Step 1: Build the Deployment Package

Run the build script to create a Lambda-ready zip file:

```bash
cd schedule_scrape
chmod +x build_lambda.sh
./build_lambda.sh
```

This will create `scrape_schedule_lambda.zip` containing:
- `scrape_schedule.py` (your Lambda handler)
- All required dependencies (beautifulsoup4, requests, lxml, urllib3)
- Flask is excluded (not needed for Lambda)

## Step 2: Create/Update Lambda Function

### Option A: Using AWS Console

1. Go to AWS Lambda Console
2. Click "Create function" (or select existing function)
3. Choose:
   - **Function name**: `scrape-schedule` (or your preferred name)
   - **Runtime**: Python 3.9, 3.10, or 3.11
   - **Architecture**: x86_64
4. Click "Create function"
5. In "Code" tab:
   - Click "Upload from" → ".zip file"
   - Select `scrape_schedule_lambda.zip`
   - Click "Save"
6. In "Configuration" → "General configuration":
   - Set **Handler**: `scrape_schedule.lambda_handler`
   - Set **Timeout**: 30 seconds (or more if needed)
   - Set **Memory**: 256 MB (or more if needed)

### Option B: Using AWS CLI

```bash
# Create function (first time)
aws lambda create-function \
  --function-name scrape-schedule \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler scrape_schedule.lambda_handler \
  --zip-file fileb://scrape_schedule_lambda.zip \
  --timeout 30 \
  --memory-size 256

# Update function code (subsequent deployments)
aws lambda update-function-code \
  --function-name scrape-schedule \
  --zip-file fileb://scrape_schedule_lambda.zip
```

## Step 3: Configure IAM Role

Your Lambda execution role needs basic permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

The function makes outbound HTTP requests to ESPN, so no special VPC or network configuration is needed.

## Step 4: Test the Function

### Test via AWS Console

1. Go to your Lambda function
2. Click "Test" tab
3. Create a new test event:

```json
{
  "queryStringParameters": {
    "team_slug": "dal",
    "team_name_long": "dallas-cowboys"
  }
}
```

4. Click "Test" and verify the response

### Test via AWS CLI

```bash
aws lambda invoke \
  --function-name scrape-schedule \
  --payload '{"queryStringParameters":{"team_slug":"dal","team_name_long":"dallas-cowboys"}}' \
  response.json

cat response.json
```

## Step 5: Expose via API Gateway or Lambda Function URL

### Option A: Lambda Function URL (Simplest)

1. In Lambda Console, go to "Configuration" → "Function URL"
2. Click "Create function URL"
3. Choose:
   - **Auth type**: NONE (or AWS_IAM if you want authentication)
   - **CORS**: Enable if needed
4. Copy the Function URL
5. Test: `curl 'https://YOUR-FUNCTION-URL?team_slug=dal&team_name_long=dallas-cowboys'`

### Option B: API Gateway REST API

1. Create a new REST API in API Gateway
2. Create a resource (e.g., `/schedule`)
3. Create a GET method
4. Set integration type to "Lambda Function"
5. Select your Lambda function
6. Deploy the API
7. Test the endpoint

### Option C: API Gateway HTTP API (Recommended)

1. Create a new HTTP API
2. Add integration → Lambda function
3. Select your function
4. Configure routes (e.g., `GET /schedule`)
5. Deploy
6. Test the endpoint

## Environment Variables (Optional)

You can set environment variables in Lambda configuration:

- `LOG_LEVEL`: Set to "DEBUG" for verbose logging (default: "INFO")

## Monitoring

- View logs in CloudWatch Logs: `/aws/lambda/scrape-schedule`
- Set up CloudWatch Alarms for errors or high latency
- Enable X-Ray tracing if needed

## Cost Optimization

- The function is stateless, so no warm-up needed
- Consider using Provisioned Concurrency if you have predictable traffic
- Monitor memory usage and adjust if needed

## Troubleshooting

### Package too large
- The zip file should be < 50MB for direct upload
- If larger, use S3 and upload from there, or use Lambda Layers

### Timeout errors
- Increase timeout in Lambda configuration
- Check CloudWatch Logs for slow operations

### Import errors
- Ensure all dependencies are included in the zip
- Check that handler path is correct: `scrape_schedule.lambda_handler`

### Network errors
- Ensure Lambda has internet access (default VPC configuration)
- Check security groups if using VPC

## Example API Requests

### Query Parameters
```
GET https://your-api-url/schedule?team_slug=min&team_name_long=minnesota-vikings
```

### Path Parameters (if using API Gateway)
```
GET https://your-api-url/schedule/min/minnesota-vikings
```

### POST with JSON Body
```bash
curl -X POST https://your-api-url/schedule \
  -H "Content-Type: application/json" \
  -d '{"team_slug": "sea", "team_name_long": "seattle-seahawks"}'
```

## Response Format

Success (200):
```json
{
  "team_slug": "dal",
  "team_name_long": "dallas-cowboys",
  "sourceUrl": "https://www.espn.com/nfl/team/schedule/_/name/dal/dallas-cowboys",
  "games": [
    {
      "WK": "13",
      "DATE": "Sun, Nov 30",
      "MATCH_UP": "Dallas VS Minnesota",
      "TIME": "4:05 PM EST",
      "GAME_ID": "401772896",
      "TV": "FOX"
    }
  ],
  "count": 6
}
```

Error (502):
```json
{
  "message": "Unable to retrieve schedule data from ESPN.",
  "detail": "Error details...",
  "url": "https://www.espn.com/nfl/team/schedule/_/name/dal/dallas-cowboys",
  "team_slug": "dal",
  "team_name_long": "dallas-cowboys"
}
```

