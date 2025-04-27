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

# grab bill list from legislative-interface
measure_time python3 main/fetch_bill_list.py $sessionId
# grab fiscal notes
measure_time python3 main/get_fiscal_review_notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# grab legal nots
measure_time python3 main/get_legal_review_notes.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# grab amendments
measure_time python3 main/get_amendments.py "$sessionId" "$legislatureOrdinal" "$sessionOrdinal"
# compress pdfs
measure_time python3 main/compress_pdfs.py $sessionId
# generate links? — figure out how we integrate them with the website
measure_time python3 main/generate_document_index.py $sessionId