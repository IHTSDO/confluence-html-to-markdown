# Confluence HTML to GitBook Markdown Directory Converter

This script converts a directory structure of HTML files exported from Atlassian Confluence into clean Markdown format, preserving the directory structure, organizing content hierarchically, and properly handling image references. The target format has been built around synchronising git repositories with document spaces in **GitBook**, https://www.gitbook.com/, but it could probably be used for other services.

## Features

- Converts all HTML files in a Confluence export to Markdown
- Removes Confluence-specific content and navigation elements
- Creates a proper hierarchical folder structure based on section numbering:
  - Top-level sections (e.g., "4-logical-design.html") become README.md files in their folders
  - Subsections with multiple pages get their own folders
  - Avoids creating unnecessary folders for isolated subsection pages
- Places images in an `images` directory and properly handles relative paths
- Cleans up file names by removing page IDs and numbers from filenames
- Wraps images in `<figure>` tags with captions from text immediately following the image
- Ensures all images display at full width with `style="width: 100%;"`
- Extracts page titles and adds them as Markdown headings
- Removes "- Confluence" suffix from page titles
- Automatically detects and removes common title prefixes (e.g., "Project Name:" or "Documentation Title:") across all pages

## Section Organization

The script creates a logical folder structure matching your documentation hierarchy:

```
4 logical-design/                    <- Main section folder
  ├── README.md                      <- Main section content (was 4-logical-design.md)
  ├── 4.1-namespaces.md              <- Direct subsection without children
  ├── 4.2 modules/                   <- Subsection folder with multiple children
  │   ├── README.md                  <- Subsection content (was 4.2-modules.md)
  │   ├── 4.2.1-module-definition.md
  │   └── 4.2.2-module-dependencies.md
  └── 4.3 extensions/                <- Nested subsection structure
      ├── README.md
      ├── 4.3.1 components/
      │   ├── README.md
      │   ├── 4.3.1.1-common-attributes.md
      │   └── 4.3.1.2-concepts.md
      └── 4.3.2 reference-sets/
          ├── README.md
          └── 4.3.2.1-common-attributes.md
```

## Image Handling

- Images are wrapped in `<figure>` tags with captions
- Captions are automatically extracted from text following the image
- All images are displayed at full width
- Relative paths are adjusted based on folder depth
- The resulting HTML looks like:
  ```html
  <figure>
    <img src="../images/example.png" alt="Alt text" style="width: 100%;">
    <figcaption><p>Image caption text</p></figcaption>
  </figure>
  ```

## Confluence-Specific Processing

- Removes UI elements like headers, footers, navigation, comments, and sidebars
- Extracts only the main content from each page
- Handles Confluence attachments by looking for them in attachments directories
- Cleans filenames by removing page IDs from both beginning and end:
  - "12345678-My-Page.html" becomes "my-page.md"
  - "My-Page-12345678.html" becomes "my-page.md"
- Preserves section numbers in filenames:
  - "4.3.2-Reference-Sets_57815107.html" becomes "4.3.2 reference-sets/README.md"
- Identifies and removes common title prefixes (like "Compositional Grammar:" or "Project Guide:") that appear across multiple pages

## Title Cleaning

The script performs multiple levels of title cleaning:

1. **Global prefix detection**: Identifies common prefixes used across all pages (e.g., "Project Name: ", "Documentation Title: ")
2. **Individual title cleaning**: Applies rules to each title to remove repetitive elements
3. **Suffix removal**: Removes standard suffixes like "- Confluence"

This ensures consistent and clean headings throughout your documentation.

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
2. Analyze all titles to identify common prefixes
3. Clean up Confluence-specific elements
4. Convert each HTML file to Markdown, removing identified title prefixes
5. Organize content into a hierarchical folder structure based on section numbering
6. Create README.md files for section and subsection main pages
7. Copy all images to `./markdown_output/images/`
8. Update image references in the Markdown files with proper relative paths
9. Wrap images in figure tags with captions
10. Report the common prefixes that were removed

## Additional Tools

### Append Content Tool

This repository includes a powerful utility for managing feedback links across your converted documentation:

📄 **[Append Content Tool Documentation](append-content-tool.md)**

The `append-content.py` script allows you to:
- Add feedback links to all text files in your documentation
- **Automatically extract page titles from H1 headers** and include them in feedback URLs
- Remove specific or all feedback links from files
- Support dry-run mode to preview changes
- Filter operations by file patterns (e.g., only HTML files)
- Handle duplicate detection and smart cleanup
- **URL-encode page titles** to handle special characters properly
- **Fallback to filename** when no H1 header is found
- **Optional page title extraction** with `--no-page-titles` flag

Perfect for adding feedback forms to your converted Confluence documentation or managing feedback links across large document sets.

## Notes

- External images (URLs starting with http:// or https://) are kept as-is
- The script assumes UTF-8 encoding for HTML files
- For complex Confluence macros and layouts, some formatting may be simplified
- Best results are achieved with standard Confluence exports rather than custom themes
- A lot of the code here was created using [Cursor](https://cursor.com/) and claude-4-sonnet, then tested by humans.

## Customization

You can modify the following parts of the script to adjust the conversion:

- `clean_confluence_html()`: Edit to add or remove Confluence elements to be removed
- `clean_confluence_filename()`: Adjust filename cleaning logic
- `get_section_path()`: Modify the folder structure and file organization logic
- `setup_html2text()`: Change HTML to Markdown conversion settings 
- `process_images_with_placeholders()`: Adjust image handling and styling
- `find_common_title_prefix()`: Modify how common prefixes are detected (e.g., change the 50% threshold) 