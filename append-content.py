import os
import argparse
import sys
import re
from pathlib import Path
from typing import List, Tuple

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
    Remove specific content from a file.
    
    Returns: True if content was found and removed, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find and remove lines containing the content
        content_stripped = content_to_remove.strip()
        original_count = len(lines)
        
        # Remove lines that contain the content (exact match or as substring)
        filtered_lines = []
        removed_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            # Skip empty lines that might have been added with the content
            if (content_stripped in line_stripped or 
                line_stripped == content_stripped or
                (line_stripped == '' and removed_count > 0 and len(filtered_lines) > 0 and filtered_lines[-1].strip() == '')):
                removed_count += 1
                # Skip consecutive empty lines after removal
                continue
            else:
                filtered_lines.append(line)
        
        if removed_count > 0:
            # Write back the filtered content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            return True
        
        return False
        
    except Exception:
        raise

def remove_any_feedback_links(filepath: str) -> bool:
    """
    Remove any feedback links to the Google Form from a file.
    
    Returns: True if any feedback links were found and removed, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Pattern to match any feedback link to our Google Form
        feedback_pattern = r'docs\.google\.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q.*entry\.1767247133='
        
        filtered_lines = []
        removed_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line contains a feedback link
            if re.search(feedback_pattern, line):
                removed_count += 1
                continue
            # Also remove empty lines that might have been added with the content
            elif (line_stripped == '' and removed_count > 0 and 
                  len(filtered_lines) > 0 and filtered_lines[-1].strip() == ''):
                continue
            else:
                filtered_lines.append(line)
        
        if removed_count > 0:
            # Write back the filtered content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            return True
        
        return False
        
    except Exception:
        raise

def process_files(directory: str, line_to_add: str, dry_run: bool = False, 
                 file_pattern: str = None, skip_existing: bool = True, 
                 remove_mode: bool = False, remove_all_feedback: bool = False) -> Tuple[int, int, int]:
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
    print()
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            relative_path = os.path.relpath(filepath, directory)
            
            # Apply file pattern filter if specified
            if file_pattern and not Path(filename).match(file_pattern):
                continue
            
            # Skip non-text files
            if not is_text_file(filepath):
                print(f"⏭️  Skipped {relative_path} (binary/non-text file)")
                skipped += 1
                continue
            
            try:
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
                    # Remove specific content mode
                    if not has_content_already(filepath, line_to_add):
                        print(f"⏭️  Skipped {relative_path} (specific content not found)")
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        success = remove_content_from_file(filepath, line_to_add)
                        if not success:
                            print(f"⏭️  Skipped {relative_path} (specific content not found during removal)")
                            skipped += 1
                            continue
                    
                    print(f"🗑️  {'Would remove from' if dry_run else 'Removed from'} {relative_path}")
                    processed += 1
                    
                else:
                    # Add mode: existing logic
                    if skip_existing and has_content_already(filepath, line_to_add):
                        print(f"⏭️  Skipped {relative_path} (content already exists)")
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        with open(filepath, 'a', encoding='utf-8') as f:
                            f.write('\n' + line_to_add + '\n')
                    
                    print(f"✅ {'Would append to' if dry_run else 'Appended to'} {relative_path}")
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
        description='Append or remove feedback links from text files in a directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add feedback links
  %(prog)s /path/to/directory
  %(prog)s /path/to/directory --document-name "Custom+Guide+Name"
  %(prog)s /path/to/directory --dry-run --pattern "*.html"
  
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
    parser.add_argument('--document-name', '-d', default='LOINC+Implementation+Guide', 
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
    
    # Build the line to add/remove
    line_to_add = f'<a href="https://docs.google.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q/viewform?usp=pp_url&#x26;entry.1767247133={args.document_name}" class="button primary">Provide Feedback</a>'
    
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
        if not args.remove_all_feedback:
            print(f"   Content to {'remove' if args.remove else 'add'}: {line_to_add}")
        print()
    
    # Process files
    processed, skipped, errors = process_files(
        directory=args.directory,
        line_to_add=line_to_add,
        dry_run=args.dry_run,
        file_pattern=args.pattern,
        skip_existing=not args.no_skip_existing,
        remove_mode=args.remove,
        remove_all_feedback=args.remove_all_feedback
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