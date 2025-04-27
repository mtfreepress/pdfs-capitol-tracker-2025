#!/bin/bash

set -e  # Exit on error

# 2025 arguments
sessionId=2 
sessionOrdinal=20251 
legislatureOrdinal=69

# measure time taken for a command
measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

echo "=== Starting PDF fetch process ==="
# grab bill list from legislative-interface
python3 main/fetch_bill_list.py $sessionId
# grab fiscal notes
python3 main/fetch_fiscal_notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# grab legal nots
python3 main/fetch_legal_notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# grab amendments
python3 main/fetch_amendments.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# compress pdfs
python3 main/compress_pdfs.py $sessionId
# generate links? — figure out how we integrate them with the website

# Run the fetch script
# python main/fetch_pdfs.py

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