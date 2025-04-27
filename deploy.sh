measure_time() {
    local start_time=$(date +%s)
    echo "Running: $@"
    "$@"
    local end_time=$(date +%s)
    local elapsed_time=$((end_time - start_time))
    echo "Time taken: ${elapsed_time} seconds"
}

echo "=== Starting PDF deploy process ==="

# Run the AWS CLI sync command
measure_time aws s3 sync build s3://projects.montanafreepress.org/capitol-tracker-2025 \
  --delete \
  --exact-timestamps \
  --size-only \
  --include "*.pdf" \
  --content-type "application/pdf" \
  --max-concurrent-requests 10

# Create CloudFront invalidation to refresh the cache
measure_time aws cloudfront create-invalidation --distribution-id E1G7ISX2SZFY34 --paths "/capitol-tracker-2025/*"

echo "=== Deployment complete ==="