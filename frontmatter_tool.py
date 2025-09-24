#!/usr/bin/env python3
"""
Frontmatter Tool for Markdown Files

This script adds or removes YAML frontmatter from markdown files in a directory.
It can handle multiple copies of the same frontmatter and remove them all.

Usage:
    python frontmatter_tool.py --add <directory>     # Add frontmatter to all .md files
    python frontmatter_tool.py --remove <directory>  # Remove frontmatter from all .md files
    python frontmatter_tool.py --help                # Show help message
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


# The frontmatter template to add
FRONTMATTER_TEMPLATE = """---
layout:
  width: wide
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
  metadata:
    visible: true
---"""


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text for comparison purposes."""
    # Replace multiple spaces with single spaces and normalize line endings
    return re.sub(r'\s+', ' ', text.strip())


def extract_frontmatter(content: str) -> Tuple[str, str, bool]:
    """
    Extract YAML frontmatter from markdown content.
    
    Returns:
        Tuple of (frontmatter, content_without_frontmatter, has_frontmatter)
    """
    # Pattern to match YAML frontmatter between --- markers
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        content_without = content[match.end():]
        return frontmatter, content_without, True
    
    return "", content, False


def has_target_frontmatter(content: str) -> bool:
    """Check if content has the target frontmatter."""
    frontmatter, _, has_frontmatter = extract_frontmatter(content)
    
    if not has_frontmatter:
        return False
    
    # Normalize both frontmatters for comparison
    normalized_extracted = normalize_whitespace(frontmatter)
    normalized_target = normalize_whitespace(FRONTMATTER_TEMPLATE.split('---')[1])
    
    return normalized_extracted == normalized_target


def remove_all_frontmatter_copies(content: str) -> str:
    """Remove all copies of the target frontmatter from content."""
    # Pattern to match the complete frontmatter block
    frontmatter_block_pattern = r'^---\s*\nlayout:\s*\n\s*width:\s*wide\s*\n\s*title:\s*\n\s*visible:\s*true\s*\n\s*description:\s*\n\s*visible:\s*true\s*\n\s*tableOfContents:\s*\n\s*visible:\s*true\s*\n\s*outline:\s*\n\s*visible:\s*true\s*\n\s*pagination:\s*\n\s*visible:\s*true\s*\n\s*metadata:\s*\n\s*visible:\s*true\s*\n---\s*\n'
    
    # Remove all occurrences of the frontmatter block
    cleaned_content = re.sub(frontmatter_block_pattern, '', content, flags=re.MULTILINE | re.DOTALL)
    
    # Clean up any extra newlines at the beginning
    cleaned_content = re.sub(r'^\n+', '', cleaned_content)
    
    return cleaned_content


def add_frontmatter(content: str) -> str:
    """Add frontmatter to the beginning of content."""
    # Remove any existing copies first
    cleaned_content = remove_all_frontmatter_copies(content)
    
    # Add the frontmatter at the beginning
    return FRONTMATTER_TEMPLATE + '\n\n' + cleaned_content


def process_markdown_file(file_path: Path, operation: str) -> bool:
    """
    Process a single markdown file.
    
    Args:
        file_path: Path to the markdown file
        operation: 'add' or 'remove'
    
    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        if operation == 'add':
            if has_target_frontmatter(original_content):
                print(f"  ✓ {file_path.name} already has target frontmatter")
                return False
            
            new_content = add_frontmatter(original_content)
            if new_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✓ Added frontmatter to {file_path.name}")
                return True
            else:
                print(f"  - No changes needed for {file_path.name}")
                return False
        
        elif operation == 'remove':
            if not has_target_frontmatter(original_content):
                print(f"  ✓ {file_path.name} doesn't have target frontmatter")
                return False
            
            new_content = remove_all_frontmatter_copies(original_content)
            if new_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✓ Removed frontmatter from {file_path.name}")
                return True
            else:
                print(f"  - No changes needed for {file_path.name}")
                return False
        
    except Exception as e:
        print(f"  ✗ Error processing {file_path.name}: {e}")
        return False


def find_markdown_files(directory: Path) -> List[Path]:
    """Find all markdown files in the directory."""
    markdown_files = []
    
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return markdown_files
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory")
        return markdown_files
    
    # Find all .md files recursively
    for file_path in directory.rglob('*.md'):
        if file_path.is_file():
            markdown_files.append(file_path)
    
    return sorted(markdown_files)


def main():
    parser = argparse.ArgumentParser(
        description="Add or remove YAML frontmatter from markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python frontmatter_tool.py --add ./docs          # Add frontmatter to all .md files in ./docs
  python frontmatter_tool.py --remove ./output     # Remove frontmatter from all .md files in ./output
  python frontmatter_tool.py --add . --remove .    # Add to all files, then remove from all files
        """
    )
    
    parser.add_argument(
        '--add',
        metavar='DIRECTORY',
        help='Add frontmatter to all .md files in the specified directory'
    )
    
    parser.add_argument(
        '--remove',
        metavar='DIRECTORY',
        help='Remove frontmatter from all .md files in the specified directory'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    if not args.add and not args.remove:
        parser.print_help()
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
        print()
    
    total_modified = 0
    
    # Process add operation
    if args.add:
        directory = Path(args.add)
        print(f"Adding frontmatter to markdown files in: {directory}")
        print()
        
        markdown_files = find_markdown_files(directory)
        
        if not markdown_files:
            print("No markdown files found in the directory")
        else:
            print(f"Found {len(markdown_files)} markdown file(s):")
            for file_path in markdown_files:
                print(f"  - {file_path.relative_to(directory)}")
            print()
            
            if not args.dry_run:
                for file_path in markdown_files:
                    if process_markdown_file(file_path, 'add'):
                        total_modified += 1
            else:
                for file_path in markdown_files:
                    if has_target_frontmatter(file_path.read_text(encoding='utf-8')):
                        print(f"  ✓ {file_path.name} already has target frontmatter")
                    else:
                        print(f"  → Would add frontmatter to {file_path.name}")
                        total_modified += 1
        
        print()
    
    # Process remove operation
    if args.remove:
        directory = Path(args.remove)
        print(f"Removing frontmatter from markdown files in: {directory}")
        print()
        
        markdown_files = find_markdown_files(directory)
        
        if not markdown_files:
            print("No markdown files found in the directory")
        else:
            print(f"Found {len(markdown_files)} markdown file(s):")
            for file_path in markdown_files:
                print(f"  - {file_path.relative_to(directory)}")
            print()
            
            if not args.dry_run:
                for file_path in markdown_files:
                    if process_markdown_file(file_path, 'remove'):
                        total_modified += 1
            else:
                for file_path in markdown_files:
                    content = file_path.read_text(encoding='utf-8')
                    if not has_target_frontmatter(content):
                        print(f"  ✓ {file_path.name} doesn't have target frontmatter")
                    else:
                        print(f"  → Would remove frontmatter from {file_path.name}")
                        total_modified += 1
        
        print()
    
    if args.dry_run:
        print(f"DRY RUN COMPLETE - Would modify {total_modified} file(s)")
    else:
        print(f"Operation complete - Modified {total_modified} file(s)")


if __name__ == '__main__':
    main()

