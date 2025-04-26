import requests
import json
import os
from pathlib import Path

# Import shared configuration
# configuration
UPDATE_URLS = {
    'legalNotes': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/refs/heads/main/interface/legal-note-updates.json',
    'fiscalNotes': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/refs/heads/main/interface/fiscal-note-updates.json',
    'amendments': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/refs/heads/main/interface/amendment-updates.json'
}

RAW_URL_BASES = {
    'legalNotes': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/main/interface/downloads/legal-note-pdfs-2/',
    'fiscalNotes': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/main/interface/downloads/fiscal-note-pdfs-2/',
    'amendments': 'https://raw.githubusercontent.com/mtfreepress/legislative-interface/main/interface/downloads/amendment-pdfs-2/'
}

# local directories
BUILD_DIR = Path('build')
OUT_DIRS = {
    'legalNotes': BUILD_DIR / 'legal-notes',
    'fiscalNotes': BUILD_DIR / 'fiscal-notes',
    'amendments': BUILD_DIR / 'amendments'
}


def fetch_json(url):
    """Fetch JSON data from a URL with optional GitHub token authentication."""
    headers = {}
    if 'GITHUB_TOKEN' in os.environ:
        headers['Authorization'] = f"token {os.environ['GITHUB_TOKEN']}"
        headers['Accept'] = 'application/vnd.github.v3+json'
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def ensure_directory(directory):
    """Create directory if it doesn't exist."""
    directory.mkdir(parents=True, exist_ok=True)

def download_pdf(url, output_path, clear_before=True):
    """Download a PDF file."""
    # Make sure the parent directory exists
    ensure_directory(output_path.parent)
    
    # Clear directory if requested
    if clear_before and output_path.parent.exists():
        for file in output_path.parent.glob('*'):
            if file.is_file():
                file.unlink()
    
    # Download the file
    response = requests.get(url)
    response.raise_for_status()
    
    # Save the file
    with open(output_path, 'wb') as f:
        f.write(response.content)
    
    print(f"Downloaded: {output_path}")

def process_notes(note_type):
    """Process legal or fiscal notes."""
    print(f"Processing {note_type} updates...")
    
    # Fetch the updates list
    updates = fetch_json(UPDATE_URLS[note_type])
    
    for update in updates:
        bill_folder = f"{update['billType']}-{update['billNumber']}"
        folder_path = OUT_DIRS[note_type] / bill_folder
        ensure_directory(folder_path)
        
        file_url = f"{RAW_URL_BASES[note_type]}{bill_folder}/{update['fileName']}"
        output_path = folder_path / update['fileName']
        
        # For notes, we only keep the latest version
        download_pdf(file_url, output_path, clear_before=True)

def process_amendments():
    """Process amendments, keeping all versions."""
    print("Processing amendments updates...")
    
    # Fetch the updates list
    updates = fetch_json(UPDATE_URLS['amendments'])
    
    # Group amendments by bill for easier processing
    bill_amendments = {}
    for amendment in updates:
        bill_key = f"{amendment['billType']}-{amendment['billNumber']}"
        if bill_key not in bill_amendments:
            bill_amendments[bill_key] = []
        bill_amendments[bill_key].append(amendment)
    
    # Process each bill's amendments
    for bill_key, amendments in bill_amendments.items():
        print(f"Processing amendments for {bill_key}...")
        folder_path = OUT_DIRS['amendments'] / bill_key
        ensure_directory(folder_path)
        
        # Get existing files to avoid re-downloading
        existing_files = [f.name for f in folder_path.glob('*')] if folder_path.exists() else []
        
        # Download each amendment
        for amendment in amendments:
            file_url = f"{RAW_URL_BASES['amendments']}{bill_key}/{amendment['fileName']}"
            output_path = folder_path / amendment['fileName']
            
            # Skip if file already exists
            if amendment['fileName'] in existing_files:
                print(f"File already exists, skipping: {amendment['fileName']}")
                continue
            
            # Download without clearing directory (to keep all versions)
            download_pdf(file_url, output_path, clear_before=False)

def main():
    """Main function to run the fetch process."""
    try:
        # Create the build directory structure
        for directory in OUT_DIRS.values():
            ensure_directory(directory)
        
        # Process legal and fiscal notes
        process_notes('legalNotes')
        process_notes('fiscalNotes')
        
        # Process amendments
        process_amendments()
        
        print("All fetch operations completed successfully")
        
    except Exception as e:
        print(f"Error during fetch: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()