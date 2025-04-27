#!/usr/bin/env python3
import os
import json
import re
import argparse
import shutil
from pathlib import Path

def generate_document_index(session_id):
    """Generate document index for amendments, fiscal notes, and legal notes."""
    print('Generating document index...')
    
    # Configuration
    document_types = ['amendments', 'fiscal-notes', 'legal-notes']
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent 
    data_dir = base_dir / "data"
    
    # Source directories based on session_id
    source_dirs = {
        'amendments': data_dir / f"amendment-pdfs-{session_id}",
        'fiscal-notes': data_dir / f"fiscal-note-pdfs-{session_id}",
        'legal-notes': data_dir / f"legal-note-pdfs-{session_id}"
    }
    
    # Output paths - directly in data directory for deployment
    metadata_dir = data_dir / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    
    # Create bills directory for individual JSONs
    bills_dir = metadata_dir / "bills"
    bills_dir.mkdir(exist_ok=True)
    
    # Define paths for output files
    output_path = metadata_dir / "document-index.json"
    bill_document_types_path = metadata_dir / "bill-document-types.json"
    
    bills_with_amendments_path = metadata_dir / "bills-with-amendments.txt"
    bills_with_fiscal_notes_path = metadata_dir / "bills-with-fiscal-notes.txt"
    bills_with_legal_notes_path = metadata_dir / "bills-with-legal-notes.txt"
    
    document_index = {}
    
    # Initialize lists for each document type
    bills_with_amendments = []
    bills_with_fiscal_notes = []
    bills_with_legal_notes = []
    
    # Initialize bill document types mapping
    bill_document_types = {}
    
    # Process each document type
    for doc_type in document_types:
        source_dir = source_dirs[doc_type]
        document_index[doc_type] = {}
        
        if not source_dir.exists():
            print(f"Directory doesn't exist: {source_dir}")
            continue
            
        print(f"Scanning {doc_type} directory...")
        
        try:
            # Get all bill folders
            bill_dirs = [d for d in source_dir.iterdir() if d.is_dir()]
            
            for bill_dir in bill_dirs:
                bill_id = bill_dir.name
                pdf_files = [f for f in bill_dir.iterdir() if f.name.lower().endswith('.pdf')]
                
                if not pdf_files:
                    continue
                
                files_data = []
                
                for pdf_file in pdf_files:
                    file_name = pdf_file.name
                    name = file_name.replace('.pdf', '')
                    
                    # Extract parenthetical suffixes like (1), (2) etc.
                    suffix_match = re.search(r'\((\d+)\)\.pdf$', file_name, re.IGNORECASE)
                    suffix = f"({suffix_match.group(1)})" if suffix_match else ''
                    
                    # Special handling for HB-2 with section letters
                    if bill_id == 'HB-2':
                        # Pattern to match HB-2 amendment files with section codes
                        section_pattern = r'([A-Z]{2})0*(\d+)\.(\d+)\.(\d+)\.([A-Z])\.(\d+)_[^_]+_(final-\w+)(?:\.pdf)?'
                        section_match = re.match(section_pattern, file_name, re.IGNORECASE)
                        
                        if section_match:
                            prefix, bill_num, major, minor, section_letter, amend_num, final_type = section_match.groups()
                            
                            # Map section letters to names
                            section_map = {
                                'A': 'general-government',
                                'B': 'health',
                                'C': 'nat-resource-transportation',
                                'D': 'public-safety',
                                'E': 'k-12-education',
                                'F': 'long-range',
                                'O': 'global-amendment'
                            }
                            
                            section_name = section_map.get(section_letter.upper(), section_letter)
                            
                            # Format the name
                            name = f"{prefix}-{bill_num}.{major}.{minor}.{section_letter}.{amend_num}.{section_name}.{final_type}{suffix}"
                    
                    # Standard processing for all other bills
                    else:
                        matches = re.match(r'([A-Z]{2})0*(\d+)((?:\.\d+)+(?:\.[A-Z]\.\d+)*)_[^_]+_(final-\w+)(?:\.pdf)?', file_name, re.IGNORECASE)
                        if matches:
                            prefix, bill_num, version_info, final_type = matches.groups()
                            # Add suffix to the name
                            name = f"{prefix}-{bill_num}{version_info}.{final_type}{suffix}"
                    
                    # Add the file entry
                    files_data.append({
                        'name': name,
                        'url': f"/capitol-tracker-2025/{doc_type}/{bill_id}/{file_name}"
                    })
                
                # Sort files by name
                files_data.sort(key=lambda x: x['name'].lower())
                document_index[doc_type][bill_id] = files_data
                
                # Add bill to appropriate list if it has documents
                if files_data:
                    bill_space_format = bill_id.replace('-', ' ')  # Convert from "HB-123" to "HB 123"
                    
                    # Add to bill_document_types
                    if bill_id not in bill_document_types:
                        bill_document_types[bill_id] = []
                    bill_document_types[bill_id].append(doc_type)
                    
                    if doc_type == 'amendments':
                        bills_with_amendments.append(bill_space_format)
                    elif doc_type == 'fiscal-notes':
                        bills_with_fiscal_notes.append(bill_space_format)
                    elif doc_type == 'legal-notes':
                        bills_with_legal_notes.append(bill_space_format)
            
        except Exception as e:
            print(f"Error processing {doc_type} directory: {e}")
            document_index[doc_type] = {}
    
    # Sort function for bills
    def sort_key(bill):
        parts = bill.split(' ')
        return (parts[0], int(parts[1]))
    
    # Sort all bill lists
    bills_with_amendments.sort(key=sort_key)
    bills_with_fiscal_notes.sort(key=sort_key)
    bills_with_legal_notes.sort(key=sort_key)
    
    # Write all bill lists to files
    with open(bills_with_amendments_path, 'w') as f:
        f.write('\n'.join(bills_with_amendments))
    
    with open(bills_with_fiscal_notes_path, 'w') as f:
        f.write('\n'.join(bills_with_fiscal_notes))
    
    with open(bills_with_legal_notes_path, 'w') as f:
        f.write('\n'.join(bills_with_legal_notes))
    
    # Write document index
    with open(output_path, 'w') as f:
        json.dump(document_index, f, indent=2)
    
    # Write bill document types index
    with open(bill_document_types_path, 'w') as f:
        json.dump(bill_document_types, f, indent=2)
    
    # Generate individual bill JSON files
    bill_ids = set()
    for doc_type in document_types:
        bill_ids.update(document_index[doc_type].keys())
    
    for bill_id in bill_ids:
        bill_info = {}
        for doc_type in document_types:
            if bill_id in document_index[doc_type]:
                bill_info[doc_type] = document_index[doc_type][bill_id]
        
        # Write the bill-specific JSON
        bill_json_path = bills_dir / f"{bill_id}.json"
        with open(bill_json_path, 'w') as f:
            json.dump(bill_info, f, indent=2)
    
    print(f"Generated bills-with-amendments list with {len(bills_with_amendments)} bills")
    print(f"Generated bills-with-fiscal-notes list with {len(bills_with_fiscal_notes)} bills")
    print(f"Generated bills-with-legal-notes list with {len(bills_with_legal_notes)} bills")
    print(f"Generated individual JSON files for {len(bill_ids)} bills")
    print(f"Document index created at {output_path}")
    print(f"Bill document types index created at {bill_document_types_path}")
    
    return document_index

def main():
    parser = argparse.ArgumentParser(description="Generate document index for Capitol Tracker PDFs")
    parser.add_argument("sessionId", help="Legislative session ID (e.g., 2025)")
    args = parser.parse_args()
    
    generate_document_index(args.sessionId)

if __name__ == "__main__":
    main()