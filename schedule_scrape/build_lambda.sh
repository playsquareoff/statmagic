#!/bin/bash
# Build script for AWS Lambda deployment package
# This script creates a deployment-ready zip file for Lambda

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build_lambda"
ZIP_FILE="${SCRIPT_DIR}/scrape_schedule_lambda.zip"

echo "Building Lambda deployment package..."
echo "======================================"

# Clean up previous build
rm -rf "${BUILD_DIR}"
rm -f "${ZIP_FILE}"

# Create build directory
mkdir -p "${BUILD_DIR}"

# Copy the main script
echo "Copying scrape_schedule.py..."
cp "${SCRIPT_DIR}/scrape_schedule.py" "${BUILD_DIR}/"

# Install dependencies (using Lambda-specific requirements without Flask)
echo "Installing dependencies..."
if [ -f "${SCRIPT_DIR}/requirements-lambda.txt" ]; then
    pip3 install -r "${SCRIPT_DIR}/requirements-lambda.txt" --target "${BUILD_DIR}" --upgrade
else
    # Fallback: install from main requirements and remove Flask
    pip install -r "${SCRIPT_DIR}/requirements.txt" --target "${BUILD_DIR}" --upgrade
    echo "Removing Flask (not needed for Lambda)..."
    rm -rf "${BUILD_DIR}/flask"*
    rm -rf "${BUILD_DIR}/Werkzeug"*
    rm -rf "${BUILD_DIR}/Jinja2"*
    rm -rf "${BUILD_DIR}/MarkupSafe"*
    rm -rf "${BUILD_DIR}/itsdangerous"*
    rm -rf "${BUILD_DIR}/click"*
    rm -rf "${BUILD_DIR}/blinker"*
fi

# Remove unnecessary files to reduce package size
echo "Cleaning up unnecessary files..."
find "${BUILD_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${BUILD_DIR}" -type f -name "*.pyo" -delete 2>/dev/null || true
find "${BUILD_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "Creating zip file..."
cd "${BUILD_DIR}"
zip -r "${ZIP_FILE}" . -q

# Get package size
PACKAGE_SIZE=$(du -h "${ZIP_FILE}" | cut -f1)
echo ""
echo "======================================"
echo "✓ Build complete!"
echo "  Package: ${ZIP_FILE}"
echo "  Size: ${PACKAGE_SIZE}"
echo ""
echo "Next steps:"
echo "  1. Upload ${ZIP_FILE} to AWS Lambda"
echo "  2. Set handler to: scrape_schedule.lambda_handler"
echo "  3. Set runtime to: Python 3.9, 3.10, or 3.11"
echo "  4. Set timeout to at least 30 seconds"
echo "  5. Configure API Gateway or Lambda Function URL if needed"
echo "======================================"

