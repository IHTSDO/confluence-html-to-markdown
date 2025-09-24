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

### Remove Confluence Links Script

The `remove_confluence_links.py` script is a specialized utility for cleaning up internal Confluence links that may remain in your converted documentation:

**Purpose**: Removes internal Confluence links (pointing to `https://confluence.ihtsdotools.org`) while preserving the link text, making your documentation cleaner and more readable.

**What it does**:
- Finds Markdown links in the format `[Link Text](https://confluence.ihtsdotools.org/...)`
- Replaces them with just the link text: `Link Text`
- Preserves all other links (Wikipedia, external sites, etc.)
- Processes all `.md` files recursively in the specified directory

**Usage**:
```bash
# Basic usage - processes the 'output' directory
python3 remove_confluence_links.py

# Specify a different directory
python3 remove_confluence_links.py --directory /path/to/markdown/files

# Dry run to see what would be changed without modifying files
python3 remove_confluence_links.py --dry-run --verbose

# Verbose output to see detailed processing information
python3 remove_confluence_links.py --verbose
```

**Command line options**:
- `--directory`, `-d`: Directory to process (default: `output`)
- `--dry-run`, `-n`: Preview changes without modifying files
- `--verbose`, `-v`: Show detailed output including examples of links being processed

**Example transformation**:
```markdown
# Before
This is an abbreviation for [Augmented Backus-Naur Form](https://confluence.ihtsdotools.org/display/DOCGLOSS/Augmented+Backus-Naur+Form "Glossary link").

# After  
This is an abbreviation for Augmented Backus-Naur Form.
```

**Safe operation**:
- Only removes links pointing to `confluence.ihtsdotools.org`
- Preserves external links to Wikipedia, RFC documents, and other sites
- Includes comprehensive error handling and progress reporting
- Supports dry-run mode for safe testing

This tool is particularly useful after converting Confluence documentation that contains many internal cross-references, helping to create cleaner, more portable documentation.

### Frontmatter Management Tool

The `frontmatter_tool.py` script is a utility for managing YAML frontmatter in markdown files, specifically designed for GitBook-style documentation:

**Purpose**: Adds or removes standardized YAML frontmatter from markdown files in bulk, with support for handling multiple copies of the same frontmatter.

**What it does**:
- Adds GitBook-compatible YAML frontmatter to markdown files
- Removes existing frontmatter (including multiple copies) from files
- Processes all `.md` files recursively in specified directories
- Provides dry-run mode for safe testing
- Smart detection to avoid unnecessary modifications

**Frontmatter template**:
```yaml
---
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
---
```

**Usage**:
```bash
# Add frontmatter to all .md files in a directory
python3 frontmatter_tool.py --add ./docs

# Remove frontmatter from all .md files in a directory
python3 frontmatter_tool.py --remove ./output

# See what would be done without making changes
python3 frontmatter_tool.py --add ./docs --dry-run

# Combine operations (add to one directory, remove from another)
python3 frontmatter_tool.py --add ./docs --remove ./output
```

**Command line options**:
- `--add DIRECTORY`: Add frontmatter to all .md files in the specified directory
- `--remove DIRECTORY`: Remove frontmatter from all .md files in the specified directory
- `--dry-run`: Show what would be done without making changes

**Key features**:
- **Multiple copy handling**: Removes all instances of the same frontmatter from a single file
- **Smart detection**: Only modifies files that actually need changes
- **Recursive processing**: Handles subdirectories automatically
- **Safe operation**: Includes dry-run mode and comprehensive error handling
- **Progress reporting**: Shows detailed output of what files were modified

**Example transformations**:
```markdown
# Before (no frontmatter)
# My Document
Content here...

# After adding frontmatter
---
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
---

# My Document
Content here...
```

This tool is essential for preparing markdown documentation for GitBook or other platforms that require specific YAML frontmatter formatting.

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