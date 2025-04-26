import os
import boto3

# Import shared configuration
from config import BUILD_DIR, S3_BUCKET, S3_PREFIX

def sync_to_s3():
    """Sync the build directory to S3 using AWS CLI."""
    import subprocess
    
    if not BUILD_DIR.exists():
        print(f"Build directory {BUILD_DIR} does not exist. Run fetch_pdfs.py first.")
        return False
    
    cmd = [
        "aws", "s3", "sync",
        str(BUILD_DIR),
        f"s3://{S3_BUCKET}/{S3_PREFIX}",
        "--content-type", "application/pdf"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    
    if result.returncode == 0:
        print("S3 sync completed successfully")
        return True
    else:
        print(f"S3 sync failed with exit code {result.returncode}")
        return False