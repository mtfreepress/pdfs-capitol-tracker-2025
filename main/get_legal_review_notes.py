import os
import json
import requests
import argparse
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

def fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number):
    """Fetch document IDs from API."""
    url = f"{API_BASE_URL}/docs/v1/documents/getBillOther"
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
        print(f"Error fetching document IDs: {response.status_code} for bill: {bill_type} {bill_number}")
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

def get_latest_document(documents):
    """Get the latest document based on document ID."""
    latest_document = None
    latest_id = None
    for document in documents:
        document_id = document["id"]
        if latest_id is None or document_id > latest_id:
            latest_id = document_id
            latest_document = document
    return latest_document

def fetch_and_save_legal_review_notes(bill, legislature_ordinal, session_ordinal, download_dir):
    """Fetch and save legal notes for a bill."""
    session = create_session_with_retries()
    bill_type = bill["billType"]
    bill_number = bill["billNumber"]

    documents = fetch_document_ids(session, legislature_ordinal, session_ordinal, bill_type, bill_number)
    
    dest_folder = download_dir / f"{bill_type}-{bill_number}"
    existing_files = list_files_in_directory(dest_folder)

    latest_document = get_latest_document(documents)
    if latest_document:
        file_name = latest_document["fileName"]
        if file_name not in existing_files:
            # Remove older files
            for file in existing_files:
                (dest_folder / file).unlink()
                
            document_id = latest_document["id"]
            pdf_url = fetch_pdf_url(session, document_id)
            if pdf_url:
                download_file(pdf_url, dest_folder, file_name)
            else:
                print(f"Failed to fetch PDF URL for document ID: {document_id}")
    else:
        # Remove existing files if no legal notes are found
        for file in existing_files:
            (dest_folder / file).unlink()

def main():
    parser = argparse.ArgumentParser(description="Download legal review notes for bills")
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

    download_dir = DATA_DIR / f"legal-note-pdfs-{session_id}"
    print(f"Download directory: {download_dir}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                fetch_and_save_legal_review_notes, 
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

    print(f"Completed fetching legal notes to {download_dir}")
    return 0

if __name__ == "__main__":
    exit(main())