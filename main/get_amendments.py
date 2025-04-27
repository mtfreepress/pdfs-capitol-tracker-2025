import os
import json
import requests
import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent / "data"
API_BASE_URL = "https://api.legmt.gov"

def load_json(file_path):
    """Load JSON data from file if it exists."""
    if Path(file_path).exists():
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def download_file(url, dest_folder, file_name):
    """Download a file from URL to destination folder."""
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url)
    if response.status_code == 200:
        file_path = dest_folder / file_name
        with open(file_path, "wb") as f:
            f.write(response.content)
        # print(f"Downloaded: {file_path}")
        return True
    else:
        print(f"Failed to download: {url}")
        return False

def list_files_in_directory(subdir):
    """List all files in directory except hidden files."""
    if subdir.exists():
        return {f.name for f in subdir.iterdir() if f.is_file() and not f.name.startswith('.')}
    return set()

def create_session_with_retries():
    """Create a requests session with retry capability."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_amendment_documents(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    """Fetch amendment documents from API."""
    url = f"{API_BASE_URL}/docs/v1/documents/getBillAmendments"
    params = {
        'legislatureOrdinal': legislature_ordinal,
        'sessionOrdinal': session_ordinal,
        'billType': bill_type,
        'billNumber': bill_number
    }
    response = session.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching amendment documents: {response.status_code} for bill: {bill_type} {bill_number}")
        return []

def fetch_pdf_url(session, document_id):
    """Fetch PDF URL for a document ID."""
    url = f"{API_BASE_URL}/docs/v1/documents/shortPdfUrl?documentId={document_id}"
    response = session.post(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Error fetching PDF URL for document {document_id}: {response.status_code}")
        return None
    
def get_base_filename(filename):
    """Extract base filename without the (N) suffix."""
    # Match pattern like "filename(1).pdf" or "filename(2).pdf" to get duplicates
    pattern = r'^(.+?)(?:\([0-9]+\))?(\.[^.]+)$'
    match = re.match(pattern, filename)
    if match:
        base_name = match.group(1)
        extension = match.group(2)
        return base_name + extension
    return filename

def group_amendments_by_base_name(amendments):
    """Group amendments by their base filename and select primary version."""
    grouped = {}
    
    for amendment in amendments:
        file_name = amendment["fileName"]
        base_name = get_base_filename(file_name)
        
        if base_name not in grouped:
            grouped[base_name] = []
        grouped[base_name].append(amendment)
    
    # Select primary version for each group
    primary_amendments = []
    for base_name, versions in grouped.items():
        # prefer the one without a number suffix
        primary = next((v for v in versions if v["fileName"] == base_name), None)
        if not primary:
            # If no clean version, take the highest ID (latest version)
            primary = max(versions, key=lambda x: x["id"])
        primary_amendments.append(primary)
    
    return primary_amendments

def fetch_and_save_amendments(bill, legislature_ordinal, session_ordinal, download_dir):
    """Fetch and save amendments for a bill."""
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    amendment_documents = fetch_amendment_documents(
        session, legislature_ordinal, session_ordinal, bill_type, bill_number)

    if not amendment_documents:
        return

    unique_amendments = group_amendments_by_base_name(amendment_documents)
    
    dest_folder = download_dir / f"{bill_type}-{bill_number}"
    existing_files = list_files_in_directory(dest_folder)
    existing_base_files = {get_base_filename(file) for file in existing_files}

    for amendment in unique_amendments:
        document_id = amendment["id"]
        file_name = amendment["fileName"]
        base_name = get_base_filename(file_name)

        # Check if any version of this file already exists
        if base_name not in existing_base_files:
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, dest_folder, file_name)
            else:
                print(f"Failed to fetch PDF URL for amendment ID: {document_id}")

def main():
    parser = argparse.ArgumentParser(description="Download bill amendments")
    parser.add_argument("sessionId", type=str, help="Legislative session ID")
    parser.add_argument("legislatureOrdinal", type=int, help="Legislature ordinal")
    parser.add_argument("sessionOrdinal", type=int, help="Session ordinal")
    args = parser.parse_args()

    session_id = args.sessionId
    legislature_ordinal = args.legislatureOrdinal
    session_ordinal = args.sessionOrdinal

    # Use the new bills list file location
    list_bills_file = BASE_DIR.parent / "working" / "bills-list" / f"list-bills-{session_id}.json"
    
    if not list_bills_file.exists():
        print(f"Error: Bills list file not found at {list_bills_file}")
        print("Please run fetch_bills_list.py first to download the bills list.")
        return 1
        
    bills_data = load_json(list_bills_file)
    if not bills_data:
        print("No bills found in the bills list file.")
        return 0

    download_dir = DATA_DIR / f"amendment-pdfs-{session_id}"
    print(f"Download directory: {download_dir}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                fetch_and_save_amendments, 
                bill, 
                legislature_ordinal, 
                session_ordinal, 
                download_dir
            ) 
            for bill in bills_data
        ]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing bill: {e}")

    print(f"Completed fetching amendments to {download_dir}")
    return 0

if __name__ == "__main__":
    exit(main())