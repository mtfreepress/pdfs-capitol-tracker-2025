#!/bin/bash

set -e  # Exit on error

echo "=== Starting PDF fetch process ==="

# Run the fetch script
python main/fetch_pdfs.py

# echo "=== Starting PDF deploy process ==="

# # Run the AWS CLI sync command
# aws s3 sync build s3://projects.montanafreepress.org/capitol-tracker-2025 \
#   --delete \
#   --exact-timestamps \
#   --size-only \
#   --include "*.pdf" \
#   --content-type "application/pdf" \
#   --max-concurrent-requests 10

# # Create CloudFront invalidation to refresh the cache
# aws cloudfront create-invalidation --distribution-id E1G7ISX2SZFY34 --paths "/capitol-tracker-2025/*"

# echo "=== Deployment complete ==="