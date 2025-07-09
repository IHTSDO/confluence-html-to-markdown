import os
import argparse
import sys
import re
from pathlib import Path
from typing import List, Tuple
from urllib.parse import quote

def is_text_file(filepath: str) -> bool:
    """Check if a file is likely a text file by checking its extension."""
    text_extensions = {
        '.txt', '.md', '.html', '.htm', '.xml', '.json', '.yaml', '.yml',
        '.css', '.js', '.py', '.java', '.cpp', '.h', '.c', '.php', '.rb',
        '.go', '.rs', '.sh', '.bat', '.ps1', '.sql', '.csv', '.log'
    }
    return Path(filepath).suffix.lower() in text_extensions

def has_content_already(filepath: str, content: str) -> bool:
    """Check if the content already exists in the file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return content.strip() in f.read()
    except Exception:
        return False

def has_any_feedback_link(filepath: str) -> bool:
    """Check if the file contains any feedback link to the Google Form."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Look for the specific Google Form ID and entry parameter
            pattern = r'docs\.google\.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q.*entry\.1767247133='
            return bool(re.search(pattern, content))
    except Exception:
        return False

def remove_content_from_file(filepath: str, content_to_remove: str) -> bool:
    """
    Remove specific content from a file, including preceding newlines that were added with it.
    
    Returns: True if content was found and removed, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        content_stripped = content_to_remove.strip()
        filtered_lines = []
        content_found = False
        
        i = 0
        while i < len(lines):
            line_stripped = lines[i].strip()
            
            # Check if this line contains the feedback content
            if content_stripped in line_stripped or line_stripped == content_stripped:
                content_found = True
                
                # Remove preceding empty lines (up to 10 to handle the 6 newlines + some buffer)
                # Work backwards from current position to remove empty lines
                removal_start = i
                for j in range(i - 1, max(-1, i - 10), -1):
                    if j >= 0 and lines[j].strip() == '':
                        removal_start = j
                    else:
                        break
                
                # Remove lines from removal_start to current position (inclusive)
                # by not adding them to filtered_lines and skipping ahead
                if removal_start < len(filtered_lines):
                    # Remove some lines that were already added to filtered_lines
                    lines_to_remove = len(filtered_lines) - removal_start
                    filtered_lines = filtered_lines[:-lines_to_remove]
                
                # Skip the content line and any immediate following empty lines
                i += 1
                while i < len(lines) and lines[i].strip() == '':
                    i += 1
                continue
            else:
                filtered_lines.append(lines[i])
                i += 1
        
        if content_found:
            # Write back the filtered content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            return True
        
        return False
        
    except Exception:
        raise

def remove_any_feedback_links(filepath: str) -> bool:
    """
    Remove any feedback links to the Google Form from a file, including preceding newlines.
    
    Returns: True if any feedback links were found and removed, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Pattern to match any feedback link to our Google Form
        feedback_pattern = r'docs\.google\.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q.*entry\.1767247133='
        
        filtered_lines = []
        content_found = False
        
        i = 0
        while i < len(lines):
            line_stripped = lines[i].strip()
            
            # Check if this line contains a feedback link
            if re.search(feedback_pattern, lines[i]):
                content_found = True
                
                # Remove preceding empty lines (up to 10 to handle the 6 newlines + some buffer)
                # Work backwards from current position to remove empty lines
                removal_start = i
                for j in range(i - 1, max(-1, i - 20), -1):
                    if j >= 0 and lines[j].strip() == '':
                        removal_start = j
                    else:
                        break
                
                # Remove lines from removal_start to current position (inclusive)
                # by not adding them to filtered_lines and skipping ahead
                if removal_start < len(filtered_lines):
                    # Remove some lines that were already added to filtered_lines
                    lines_to_remove = len(filtered_lines) - removal_start
                    filtered_lines = filtered_lines[:-lines_to_remove]
                
                # Skip the content line and any immediate following empty lines
                i += 1
                while i < len(lines) and lines[i].strip() == '':
                    i += 1
                continue
            else:
                filtered_lines.append(lines[i])
                i += 1
        
        if content_found:
            # Write back the filtered content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            return True
        
        return False
        
    except Exception:
        raise

def extract_page_title(filepath: str) -> str:
    """
    Extract the page title from the first H1 header in a markdown file.
    
    Returns: The page title if found, otherwise the filename without extension
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Look for the first H1 header (starts with # followed by space)
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                # Extract the title after the # 
                title = line[2:].strip()
                return title
        
        # If no H1 header found, use the filename without extension
        filename = Path(filepath).stem
        return filename
        
    except Exception:
        # Fallback to filename if there's any error
        return Path(filepath).stem

def build_feedback_link(document_name: str, page_title: str = None) -> str:
    """
    Build the feedback link with the document name and optional page title.
    
    Args:
        document_name: The document name for the feedback form
        page_title: The page title to add as a parameter (optional)
    
    Returns: The complete feedback link HTML
    """
    base_url = "https://docs.google.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q/viewform?usp=pp_url"
    params = [f"entry.1767247133={document_name}"]
    
    if page_title:
        # URL encode the page title to handle special characters
        encoded_title = quote(page_title)
        params.append(f"entry.670899847={encoded_title}")
    
    full_url = f"{base_url}&{'&'.join(params)}"
    return f'<a href="{full_url}" class="button primary">Provide Feedback</a>'

def process_files(directory: str, document_name: str, dry_run: bool = False, 
                 file_pattern: str = None, skip_existing: bool = True, 
                 remove_mode: bool = False, remove_all_feedback: bool = False,
                 use_page_titles: bool = True) -> Tuple[int, int, int]:
    """
    Process files in directory and append or remove content.
    
    Returns: (processed, skipped, errors)
    """
    processed = 0
    skipped = 0
    errors = 0
    
    if not os.path.exists(directory):
        print(f"❌ Error: Directory '{directory}' does not exist")
        return 0, 0, 1
    
    if not os.path.isdir(directory):
        print(f"❌ Error: '{directory}' is not a directory")
        return 0, 0, 1
    
    print(f"📁 Processing directory: {directory}")
    if dry_run:
        print(f"🔍 DRY RUN MODE - No files will be modified")
    
    if remove_mode or remove_all_feedback:
        if remove_all_feedback:
            print("🗑️  REMOVE ALL FEEDBACK MODE - Deleting all feedback links from files")
        else:
            print("🗑️  REMOVE MODE - Deleting specific feedback links from files")
    else:
        print("➕ ADD MODE - Adding feedback links to files")
        if use_page_titles:
            print("📄 Using page titles from H1 headers for feedback links")
        else:
            print("📄 Using document name only for feedback links")
    print()
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            relative_path = os.path.relpath(filepath, directory)
            
            # Skip README.md and SUMMARY.md files
            if filename.lower() in ['index.md', 'summary.md']:
                print(f"⏭️  Skipped {relative_path} (README.md/SUMMARY.md file)")
                skipped += 1
                continue
            
            # Apply file pattern filter if specified
            if file_pattern and not Path(filename).match(file_pattern):
                continue
            
            # Skip non-text files
            if not is_text_file(filepath):
                print(f"⏭️  Skipped {relative_path} (binary/non-text file)")
                skipped += 1
                continue
            
            try:
                # Generate the feedback link for this specific file
                if not (remove_mode or remove_all_feedback):
                    page_title = None
                    if use_page_titles:
                        page_title = extract_page_title(filepath)
                    line_to_add = build_feedback_link(document_name, page_title)
                
                if remove_all_feedback:
                    # Remove all feedback links mode
                    if not has_any_feedback_link(filepath):
                        print(f"⏭️  Skipped {relative_path} (no feedback links found)")
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        success = remove_any_feedback_links(filepath)
                        if not success:
                            print(f"⏭️  Skipped {relative_path} (no feedback links found during removal)")
                            skipped += 1
                            continue
                    
                    print(f"🗑️  {'Would remove all feedback links from' if dry_run else 'Removed all feedback links from'} {relative_path}")
                    processed += 1
                    
                elif remove_mode:
                    # For remove mode, we need to check for any feedback link with this document name
                    # Since we can't easily match the exact dynamic link, we'll use a pattern-based approach
                    if not has_any_feedback_link(filepath):
                        print(f"⏭️  Skipped {relative_path} (no feedback links found)")
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        success = remove_any_feedback_links(filepath)
                        if not success:
                            print(f"⏭️  Skipped {relative_path} (no feedback links found during removal)")
                            skipped += 1
                            continue
                    
                    print(f"🗑️  {'Would remove from' if dry_run else 'Removed from'} {relative_path}")
                    processed += 1
                    
                else:
                    # Add mode: check if any feedback link already exists
                    if skip_existing and has_any_feedback_link(filepath):
                        print(f"⏭️  Skipped {relative_path} (feedback link already exists)")
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        with open(filepath, 'a', encoding='utf-8') as f:
                            f.write('\n\n\n\n\n\n' + line_to_add + '\n')
                    
                    page_info = f" (page: {page_title})" if use_page_titles and page_title else ""
                    print(f"✅ {'Would append to' if dry_run else 'Appended to'} {relative_path}{page_info}")
                    processed += 1
                
            except PermissionError:
                print(f"❌ Permission denied: {relative_path}")
                errors += 1
            except UnicodeDecodeError:
                print(f"❌ Encoding error: {relative_path}")
                errors += 1
            except Exception as e:
                print(f"❌ Error processing {relative_path}: {e}")
                errors += 1
    
    return processed, skipped, errors

def main():
    """Main function to handle command line arguments and coordinate the processing."""
    parser = argparse.ArgumentParser(
        description='Append or remove feedback links from text files in a directory. Page titles from H1 headers are automatically included in feedback URLs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add feedback links with page titles from H1 headers
  %(prog)s /path/to/directory
  %(prog)s /path/to/directory --document-name "Custom+Guide+Name"
  %(prog)s /path/to/directory --dry-run --pattern "*.md"
  
  # Add feedback links without page titles (document name only)
  %(prog)s /path/to/directory --no-page-titles
  
  # Remove specific feedback links (matching document name)
  %(prog)s /path/to/directory --remove
  %(prog)s /path/to/directory --remove --document-name "Custom+Guide+Name"
  
  # Remove ALL feedback links (any document name)
  %(prog)s /path/to/directory --remove-all-feedback
  %(prog)s /path/to/directory --remove-all-feedback --dry-run
  %(prog)s /path/to/directory --remove-all-feedback --pattern "*.html"
        """
    )
    
    parser.add_argument('directory', help='Root directory to process')
    parser.add_argument('--document-name', '-d', default='SNOMED+Guide', 
                       help='Document name to substitute in the feedback link (default: %(default)s)')
    parser.add_argument('--remove', '-r', action='store_true',
                       help='Remove feedback links that match the specified document name')
    parser.add_argument('--remove-all-feedback', '-R', action='store_true',
                       help='Remove ALL feedback links to the Google Form, regardless of document name')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--pattern', '--filter', '-f',
                       help='File pattern to match (e.g., "*.html", "*.md")')
    parser.add_argument('--no-skip-existing', action='store_true',
                       help='Add content even if it already exists in the file (ignored in remove modes)')
    parser.add_argument('--no-page-titles', action='store_true',
                       help='Do not use page titles from H1 headers (use document name only)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.directory:
        print("❌ Error: Directory argument is required")
        sys.exit(1)
    
    if args.remove and args.remove_all_feedback:
        print("❌ Error: Cannot use both --remove and --remove-all-feedback at the same time")
        sys.exit(1)
    
    if args.verbose:
        print(f"🔧 Configuration:")
        print(f"   Directory: {args.directory}")
        print(f"   Document name: {args.document_name}")
        if args.remove_all_feedback:
            print(f"   Mode: Remove All Feedback Links")
        elif args.remove:
            print(f"   Mode: Remove Specific")
        else:
            print(f"   Mode: Add")
        print(f"   Pattern: {args.pattern or 'All text files'}")
        if not (args.remove or args.remove_all_feedback):
            print(f"   Skip existing: {not args.no_skip_existing}")
            print(f"   Use page titles: {not args.no_page_titles}")
        print()
    
    # Process files
    processed, skipped, errors = process_files(
        directory=args.directory,
        document_name=args.document_name,
        dry_run=args.dry_run,
        file_pattern=args.pattern,
        skip_existing=not args.no_skip_existing,
        remove_mode=args.remove,
        remove_all_feedback=args.remove_all_feedback,
        use_page_titles=not args.no_page_titles
    )
    
    # Print summary
    print()
    print("📊 Summary:")
    if args.remove_all_feedback:
        action = "remove all feedback links from"
        dry_action = f"Would {action}" if args.dry_run else "Removed all feedback links from"
    elif args.remove:
        action = "remove from"
        dry_action = f"Would {action}" if args.dry_run else "Removed from"
    else:
        action = "process"
        dry_action = f"Would {action}" if args.dry_run else "Processed"
    
    print(f"   {dry_action}: {processed} files")
    print(f"   Skipped: {skipped} files")
    if errors > 0:
        print(f"   Errors: {errors} files")
    
    if errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()