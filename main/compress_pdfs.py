import os
import json
import subprocess
import hashlib
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

def load_tracking_data(tracking_file):
    """Load previously compressed files data"""
    if Path(tracking_file).exists():
        with open(tracking_file, 'r') as f:
            return json.load(f)
    return {}

def save_tracking_data(data, tracking_file):
    """Save compressed files tracking data"""
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=2)

def get_file_hash(file_path):
    """Get a hash of file contents for change detection"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def needs_compression(file_path, tracking_data):
    """Check if file needs compression based on content hash"""
    if not Path(file_path).exists():
        return False
        
    current_hash = get_file_hash(file_path)
    str_path = str(file_path)
    
    if str_path in tracking_data:
        # if hash matches, file hasn't changed
        if tracking_data[str_path]["hash"] == current_hash:
            return False
    
    return True

def compress_pdf(args):
    """Compress a single PDF file"""
    file_path, tracking_data, quality, dryrun, min_savings_percent = args
    str_path = str(file_path)
    
    if not needs_compression(file_path, tracking_data):
        return False, file_path, "Unchanged"
        
    # Use a temporary file for compression
    temp_output = f"{file_path}.compressed.pdf"
    
    try:
        # Skip actual compression in dry run mode
        if dryrun:
            print(f"[DRY RUN] Would compress: {file_path}")
            return False, file_path, "Dry Run"
            
        # Run ghostscript to compress
        result = subprocess.run([
            'gs', 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS=/{quality}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={temp_output}',
            str(file_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, file_path, f"Error: {result.stderr}"
            
        # check if compression was successful and worthwhile
        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(temp_output)
        savings_threshold = 1 - (min_savings_percent / 100)
        
        if compressed_size < original_size * savings_threshold:  # file must be smaller by the threshold
            # replace original with compressed version
            os.replace(temp_output, file_path)
            
            # get hash of compressed file
            compressed_hash = get_file_hash(file_path)
            
            # update tracking data
            tracking_data[str_path] = {
                "hash": compressed_hash,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compressed_size / original_size,
                "last_compressed": datetime.now().isoformat()
            }
            
            return True, file_path, {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "savings": original_size - compressed_size,
                "percent": (1 - compressed_size/original_size) * 100
            }
        else:
            # compression not worth it
            os.remove(temp_output)
            
            # track the file so we don't try again
            tracking_data[str_path] = {
                "hash": get_file_hash(file_path),
                "skipped": True,
                "reason": "minimal_savings",
                "last_checked": datetime.now().isoformat()
            }
            
            return False, file_path, "Minimal savings"
            
    except Exception as e:
        if Path(temp_output).exists():
            os.remove(temp_output)
        return False, file_path, f"Exception: {str(e)}"

def find_pdf_files(directory):
    """Find all PDF files in the directory (recursive)"""
    pdf_files = []
    for path in Path(directory).rglob('*.pdf'):
        pdf_files.append(path)
    return pdf_files

def compress_pdf_directory(directory, tracking_file, quality='ebook', workers=None, 
                          dryrun=False, min_savings_percent=5):
    """Compress all PDF files in the directory using multiple processes"""
    # default workers to CPU count
    if workers is None:
        workers = os.cpu_count()
    
    # load tracking data
    tracking_data = load_tracking_data(tracking_file)
    
    all_pdf_files = find_pdf_files(directory)
    
    if not all_pdf_files:
        print(f"No PDF files found in {directory}")
        return
    
    print(f"Found {len(all_pdf_files)} PDF files in {directory}")
    
    # Prepare arguments for the worker function
    work_args = [(pdf_file, tracking_data, quality, dryrun, min_savings_percent) 
                for pdf_file in all_pdf_files]
    
    # Track results
    compressed_count = 0
    unchanged_count = 0
    error_count = 0
    total_savings = 0
    
    # Process files in parallel
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(compress_pdf, args) for args in work_args]
        
        # Process results as they complete
        for future in as_completed(futures):
            success, file_path, result = future.result()
            
            if success:
                compressed_count += 1
                savings = result["savings"]
                total_savings += savings
                print(f"Compressed: {file_path} - Saved {savings/1024:.1f}KB ({result['percent']:.1f}%)")
            elif result == "Unchanged":
                unchanged_count += 1
            else:
                error_count += 1
                if result != "Minimal savings" and result != "Dry Run":
                    print(f"Failed: {file_path} - {result}")
    
    # only save tracking data if not in dry run mode
    if not dryrun:
        save_tracking_data(tracking_data, tracking_file)
    
    # print summary
    print(f"\nCompression Summary for {directory}:")
    print(f"- Total PDFs found: {len(all_pdf_files)}")
    print(f"- Compressed: {compressed_count} files")
    print(f"- Unchanged: {unchanged_count} files")
    print(f"- Skipped/Error: {error_count} files")
    print(f"- Total savings: {total_savings/1024/1024:.2f} MB")
    
    return compressed_count, unchanged_count, error_count, total_savings

def main():
    parser = argparse.ArgumentParser(description="Compress PDF files for Capitol Tracker")
    parser.add_argument("sessionId", help="Legislative session ID (e.g. 2025)")
    parser.add_argument("--tracking-file", default=None, 
                     help="JSON file to track compressed files (default: data/compression-tracking-{sessionId}.json)")
    parser.add_argument("--quality", choices=['screen', 'ebook', 'printer', 'prepress'], default='ebook',
                     help="Compression quality level (default: ebook)")
    parser.add_argument("--workers", type=int, default=None,
                     help="Number of worker processes (default: number of CPU cores)")
    parser.add_argument("--dry-run", action="store_true",
                     help="Dry run - don't actually compress files")
    parser.add_argument("--min-savings", type=float, default=5.0,
                     help="Minimum percentage savings required to keep compressed version (default: 5.0)")
    
    args = parser.parse_args()
    
    # Set up paths
    session_id = args.sessionId
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    
    tracking_file = args.tracking_file
    if tracking_file is None:
        tracking_file = data_dir / f"compression-tracking-{session_id}.json"
    
    # Directories to process
    directories = [
        data_dir / f"amendment-pdfs-{session_id}",
        data_dir / f"fiscal-note-pdfs-{session_id}",
        data_dir / f"legal-note-pdfs-{session_id}"
    ]
    
    # Track overall stats
    total_compressed = 0
    total_unchanged = 0
    total_errors = 0
    total_savings = 0
    
    print(f"=== Starting PDF compression process for session {session_id} ===")
    
    # Process each directory
    for directory in directories:
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue
        
        print(f"\nProcessing {directory}...")
        compressed, unchanged, errors, savings = compress_pdf_directory(
            directory, 
            tracking_file, 
            quality=args.quality, 
            workers=args.workers, 
            dryrun=args.dry_run, 
            min_savings_percent=args.min_savings
        )
        
        total_compressed += compressed
        total_unchanged += unchanged
        total_errors += errors
        total_savings += savings
    
    # Overall summary
    print(f"\n=== Overall Compression Summary ===")
    print(f"- Total compressed: {total_compressed} files")
    print(f"- Total unchanged: {total_unchanged} files")
    print(f"- Total errors/skipped: {total_errors} files")
    print(f"- Total disk space saved: {total_savings/1024/1024:.2f} MB")
    
    if args.dry_run:
        print("\nNote: This was a dry run. No files were actually compressed.")

if __name__ == "__main__":
    main()