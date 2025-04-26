import os
import sys
import requests
import argparse
from pathlib import Path

def fetch_bills_list(session_id):
    """
    Fetch bills list JSON for a given session ID and save it to the data directory.
    
    Args:
        session_id (str): The session ID (e.g., '2025')
    
    Returns:
        Path: Path to the saved JSON file
    """
    # Use absolute paths relative to this script's location
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data" / "bills-list"
    
    # Create the directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the URL and output file path
    url = f"https://raw.githubusercontent.com/mtfreepress/legislative-interface/refs/heads/main/list-bills-{session_id}.json"
    output_path = data_dir / f"list-bills-{session_id}.json"
    
    print(f"Fetching bills list from: {url}")
    
    try:
        # Fetch the JSON
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for non-200 status codes
        
        # Save to file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Successfully saved bills list to: {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching bills list: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Fetch bills list JSON from the legislative interface repository")
    parser.add_argument("session_id", help="Legislative session ID (e.g., 2025)")
    args = parser.parse_args()
    
    fetch_bills_list(args.session_id)

if __name__ == "__main__":
    main()