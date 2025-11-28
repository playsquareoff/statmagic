# Quick Start: Deploy to AWS Lambda

## 1. Build the Package

```bash
./build_lambda.sh
```

this creates `scrape_schedule_lambda.zip` ready for deployment.

## 2. Deploy to Lambda

### Using AWS Console:
1. Go to Lambda Console → Create Function
2. Upload `scrape_schedule_lambda.zip`
3. Set **Handler**: `scrape_schedule.lambda_handler`
4. Set **Runtime**: Python 3.11
5. Set **Timeout**: 30 seconds

### Using AWS CLI:
```bash
aws lambda create-function \
  --function-name scrape-schedule \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler scrape_schedule.lambda_handler \
  --zip-file fileb://scrape_schedule_lambda.zip \
  --timeout 30
```

## 3. Test It

```bash
aws lambda invoke \
  --function-name scrape-schedule \
  --payload '{"queryStringParameters":{"team_slug":"dal","team_name_long":"dallas-cowboys"}}' \
  response.json && cat response.json
```

## 4. Expose via Function URL

In Lambda Console:
- Configuration → Function URL → Create
- Auth type: NONE
- Copy the URL and test: `curl 'YOUR-URL?team_slug=dal&team_name_long=dallas-cowboys'`

## Full Documentation

See [LAMBDA_DEPLOYMENT.md](./LAMBDA_DEPLOYMENT.md) for detailed instructions.

