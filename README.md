# Confluence HTML to Markdown Converter

This script converts a directory structure of HTML files exported from Atlassian Confluence into clean Markdown format, preserving the directory structure and properly handling image references.

## Features

- Converts all HTML files in a Confluence export to Markdown
- Removes Confluence-specific content and navigation elements
- Cleans up file names by removing page IDs and numbers (both at beginning and end of filenames)
- Preserves directory structure
- Handles image references:
  - Copies images to an `images` folder in the output directory
  - Preserves HTML `<img src=>` tags instead of converting to Markdown format
  - Updates image references to point to the new locations
- Extracts page titles and adds them as Markdown headings
- Removes "- Confluence" suffix from page titles

## Confluence-Specific Processing

- Removes UI elements like headers, footers, navigation, comments, and sidebars
- Extracts only the main content from each page
- Handles Confluence attachments by looking for them in attachments directories
- Cleans filenames by removing page IDs from both beginning and end:
  - "12345678-My-Page.html" becomes "my-page.md"
  - "My-Page-12345678.html" becomes "my-page.md"

## Requirements

- Python 3.6+
- BeautifulSoup4
- html2text

## Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required packages:
   ```bash
   pip install beautifulsoup4 html2text
   ```

## Usage

```bash
python html2md_converter.py <input_directory> <output_directory>
```

### Example

```bash
python html2md_converter.py ./confluence_export ./markdown_output
```

This will:
1. Scan the `./confluence_export` directory for HTML files
2. Clean up Confluence-specific elements
3. Convert each HTML file to Markdown
4. Save the Markdown files to `./markdown_output` with clean filenames
5. Copy all images to `./markdown_output/images/`
6. Update image references in the Markdown files

## Notes

- External images (URLs starting with http:// or https://) are kept as-is
- The script assumes UTF-8 encoding for HTML files
- For complex Confluence macros and layouts, some formatting may be simplified
- Best results are achieved with standard Confluence exports rather than custom themes

## Customization

You can modify the following parts of the script to adjust the conversion:

- `clean_confluence_html()`: Edit to add or remove Confluence elements to be removed
- `clean_confluence_filename()`: Adjust filename cleaning logic
- `setup_html2text()`: Change HTML to Markdown conversion settings 