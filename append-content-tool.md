# Append Content Tool

A Python script for adding or removing feedback links from text files in a directory tree. This tool is particularly useful for managing feedback links across documentation sets.

## Overview

The `append-content.py` script can:
- **Add feedback links** to all text files in a directory
- **Remove specific feedback links** that match a document name
- **Remove all feedback links** regardless of document name
- Support **dry-run mode** to preview changes
- Filter files by **pattern matching**
- Handle **duplicate detection** and **smart cleanup**

## Quick Start

```bash
# Add feedback links to all text files
python append-content.py /path/to/directory

# Remove all feedback links from files
python append-content.py /path/to/directory --remove-all-feedback

# Preview what would be changed (dry run)
python append-content.py /path/to/directory --dry-run
```

## Installation

No installation required. Just ensure you have Python 3.6+ installed.

## Usage

### Basic Syntax

```bash
python append-content.py <directory> [options]
```

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--document-name` | `-d` | Document name for the feedback link (default: `LOINC+Implementation+Guide`) |
| `--remove` | `-r` | Remove feedback links matching the specified document name |
| `--remove-all-feedback` | `-R` | Remove ALL feedback links regardless of document name |
| `--dry-run` | `-n` | Preview changes without modifying files |
| `--pattern` | `-f` | File pattern to match (e.g., `"*.html"`, `"*.md"`) |
| `--no-skip-existing` | | Add content even if it already exists (ignored in remove modes) |
| `--verbose` | `-v` | Enable detailed output |
| `--help` | `-h` | Show help message |

## Operation Modes

### 1. Add Mode (Default)

Adds feedback links to text files.

```bash
# Add with default document name
python append-content.py /path/to/docs

# Add with custom document name
python append-content.py /path/to/docs --document-name "My+Custom+Guide"

# Add only to HTML files
python append-content.py /path/to/docs --pattern "*.html"
```

**Features:**
- Automatically skips binary files
- Detects and skips files that already contain the content
- Adds proper line breaks around the content

### 2. Remove Specific Mode

Removes feedback links that match a specific document name.

```bash
# Remove links for default document
python append-content.py /path/to/docs --remove

# Remove links for specific document
python append-content.py /path/to/docs --remove --document-name "Old+Guide+Name"
```

**Use cases:**
- Removing outdated feedback links for a specific guide
- Updating document-specific feedback links

### 3. Remove All Feedback Mode

Removes any feedback link to the Google Form, regardless of document name.

```bash
# Remove all feedback links
python append-content.py /path/to/docs --remove-all-feedback

# Preview removal of all feedback links
python append-content.py /path/to/docs --remove-all-feedback --dry-run
```

**Use cases:**
- Complete cleanup of all feedback links
- Preparing for migration to a new feedback system

## Advanced Usage Examples

### Dry Run Operations

Always preview changes before making them:

```bash
# Preview adding feedback links
python append-content.py /path/to/docs --dry-run --verbose

# Preview removing all feedback links from HTML files
python append-content.py /path/to/docs --remove-all-feedback --dry-run --pattern "*.html"
```

### File Pattern Filtering

Target specific file types:

```bash
# Only process HTML files
python append-content.py /path/to/docs --pattern "*.html"

# Only process Markdown files
python append-content.py /path/to/docs --pattern "*.md"

# Process multiple extensions (using shell globbing)
python append-content.py /path/to/docs --pattern "*.{html,htm}"
```

### Verbose Output

Get detailed information about the operation:

```bash
python append-content.py /path/to/docs --verbose
```

This shows:
- Configuration details
- Document name being used
- Content being added/removed
- Processing mode
- File patterns

## File Type Support

The script automatically processes these text file types:

- **Web**: `.html`, `.htm`, `.css`, `.js`
- **Documentation**: `.md`, `.txt`
- **Data**: `.xml`, `.json`, `.yaml`, `.yml`, `.csv`
- **Code**: `.py`, `.java`, `.cpp`, `.h`, `.c`, `.php`, `.rb`, `.go`, `.rs`
- **Scripts**: `.sh`, `.bat`, `.ps1`
- **Database**: `.sql`
- **Logs**: `.log`

Binary files are automatically skipped.

## Output and Status

### Status Icons

- ✅ **Successfully processed**
- ⏭️ **Skipped** (with reason)
- ❌ **Error** (with details)
- 🗑️ **Removed content**
- 📁 **Processing directory**
- 🔍 **Dry run mode**

### Exit Codes

- `0`: Success
- `1`: Error occurred during processing

## Safety Features

### Duplicate Detection
- Automatically skips files that already contain the feedback link
- Prevents duplicate content when re-running the script

### Smart Content Removal
- Removes feedback links and associated empty lines
- Preserves file structure and formatting

### Dry Run Mode
- Preview all changes before making them
- See exactly which files would be affected
- Review configuration and content

### Input Validation
- Checks if directory exists and is accessible
- Validates command line arguments
- Prevents conflicting options

## Error Handling

The script handles common issues gracefully:

- **Permission denied**: Reports files that can't be accessed
- **Encoding errors**: Skips files with encoding issues
- **Invalid directories**: Clear error messages
- **File system errors**: Detailed error reporting

## Common Workflows

### Initial Setup
```bash
# 1. Preview what will be changed
python append-content.py /path/to/docs --dry-run --verbose

# 2. Add feedback links to all files
python append-content.py /path/to/docs

# 3. Verify results
python append-content.py /path/to/docs --dry-run
```

### Content Updates
```bash
# 1. Remove old feedback links
python append-content.py /path/to/docs --remove-all-feedback

# 2. Add new feedback links
python append-content.py /path/to/docs --document-name "New+Guide+Name"
```

### Targeted Operations
```bash
# Only update HTML documentation
python append-content.py /path/to/docs --remove-all-feedback --pattern "*.html"
python append-content.py /path/to/docs --document-name "Updated+Guide" --pattern "*.html"
```

## Feedback Link Format

The script generates feedback links in this format:

```html
<a href="https://docs.google.com/forms/d/e/1FAIpQLScTmbZIf0UEQwYDkY27EEWBkaiYkHSbR0_9DmFrMLXoQLyL7Q/viewform?usp=pp_url&#x26;entry.1767247133=DOCUMENT_NAME" class="button primary">Provide Feedback</a>
```

Where `DOCUMENT_NAME` is replaced with your `--document-name` parameter.

## Troubleshooting

### Permission Issues
```bash
# Check file permissions
ls -la /path/to/docs

# Run with appropriate permissions
sudo python append-content.py /path/to/docs --dry-run
```

### Large Directories
```bash
# Use pattern filtering to reduce scope
python append-content.py /path/to/docs --pattern "*.html" --verbose
```

### Verification
```bash
# Check what feedback links exist
grep -r "docs.google.com/forms" /path/to/docs

# Verify specific document names
grep -r "entry.1767247133=" /path/to/docs
```

## Contributing

When modifying this script, consider:

1. **Backward compatibility** with existing command line options
2. **Safety features** like dry-run mode and input validation
3. **Clear error messages** and status reporting
4. **File type detection** for new formats
5. **Pattern matching** improvements

## License

This tool is part of the confluence-html-to-markdown project. 