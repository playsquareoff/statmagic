#!/bin/bash
# Pre-check script to ensure Lambda zip file exists before running Terraform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_FILE="${SCRIPT_DIR}/../schedule_scrape/scrape_schedule_lambda.zip"

echo "Checking for Lambda deployment package..."
echo "========================================"

if [ ! -f "$ZIP_FILE" ]; then
  echo "❌ Lambda zip file not found: $ZIP_FILE"
  echo ""
  echo "Building Lambda package..."
  cd "${SCRIPT_DIR}/../schedule_scrape"
  ./build_lambda.sh
  cd "${SCRIPT_DIR}"
  echo ""
  echo "✓ Build complete!"
else
  echo "✓ Lambda zip file exists: $ZIP_FILE"
  FILE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
  echo "  Size: $FILE_SIZE"
fi

echo "========================================"
echo "You can now run: terraform plan"
echo "========================================"

