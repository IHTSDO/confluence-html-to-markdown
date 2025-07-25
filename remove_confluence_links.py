#!/usr/bin/env python3
"""
Script to remove Confluence links while preserving link text in markdown files.

This script processes all .md files in the output directory and replaces 
Confluence links of the format:
[Link Text](https://confluence.ihtsdotools.org/... "title")

With just the link text:
Link Text
"""

import os
import re
import argparse
from pathlib import Path

def remove_confluence_links(content):
    """
    Remove Confluence links while preserving the link text.
    
    Args:
        content (str): The markdown content to process
        
    Returns:
        str: Content with Confluence links replaced by plain text
    """
    # Pattern to match Confluence links
    # Matches: [Link Text](https://confluence.ihtsdotools.org/... "optional title")
    confluence_pattern = r'\[([^\]]+)\]\(https://confluence\.ihtsdotools\.org/[^)]+\)'
    
    # Replace with just the link text (group 1)
    processed_content = re.sub(confluence_pattern, r'\1', content)
    
    return processed_content

def process_file(file_path, dry_run=False):
    """
    Process a single markdown file to remove Confluence links.
    
    Args:
        file_path (Path): Path to the file to process
        dry_run (bool): If True, show what would be changed without modifying files
        
    Returns:
        tuple: (original_content, processed_content, changes_made)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        processed_content = remove_confluence_links(original_content)
        changes_made = original_content != processed_content
        
        if changes_made and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
        return original_content, processed_content, changes_made
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None, None, False

def find_markdown_files(directory):
    """
    Recursively find all .md files in the given directory.
    
    Args:
        directory (Path): Directory to search
        
    Returns:
        list: List of Path objects for markdown files
    """
    markdown_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.md'):
                markdown_files.append(Path(root) / file)
    return markdown_files

def main():
    parser = argparse.ArgumentParser(description='Remove Confluence links from markdown files')
    parser.add_argument('--directory', '-d', default='output', 
                       help='Directory to process (default: output)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    
    args = parser.parse_args()
    
    output_dir = Path(args.directory)
    
    if not output_dir.exists():
        print(f"Error: Directory '{output_dir}' does not exist")
        return 1
    
    # Find all markdown files
    markdown_files = find_markdown_files(output_dir)
    
    if not markdown_files:
        print(f"No markdown files found in '{output_dir}'")
        return 0
    
    print(f"Found {len(markdown_files)} markdown files to process")
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    
    files_changed = 0
    total_links_removed = 0
    
    for file_path in markdown_files:
        original, processed, changed = process_file(file_path, args.dry_run)
        
        if original is not None and processed is not None:
            # Count the number of Confluence links that would be/were removed
            confluence_links = len(re.findall(r'\[([^\]]+)\]\(https://confluence\.ihtsdotools\.org/[^)]+\)', original))
            
            if changed:
                files_changed += 1
                total_links_removed += confluence_links
                
                if args.verbose or args.dry_run:
                    print(f"{'Would process' if args.dry_run else 'Processed'}: {file_path.relative_to(output_dir)}")
                    if confluence_links > 0:
                        print(f"  - {confluence_links} Confluence links {'would be' if args.dry_run else ''} removed")
                        
                        if args.dry_run and args.verbose:
                            # Show examples of what would be changed
                            links = re.findall(r'\[([^\]]+)\]\(https://confluence\.ihtsdotools\.org/[^)]+\)', original)
                            for i, link_text in enumerate(links[:3]):  # Show first 3 examples
                                print(f"    Example {i+1}: '{link_text}'")
                            if len(links) > 3:
                                print(f"    ... and {len(links) - 3} more")
            elif args.verbose:
                print(f"No changes needed: {file_path.relative_to(output_dir)}")
    
    print("\nSummary:")
    print(f"Files {'that would be' if args.dry_run else ''} modified: {files_changed}")
    print(f"Total Confluence links {'that would be' if args.dry_run else ''} removed: {total_links_removed}")
    
    if args.dry_run and files_changed > 0:
        print("\nTo actually make these changes, run the script without --dry-run")
    
    return 0

if __name__ == "__main__":
    exit(main())