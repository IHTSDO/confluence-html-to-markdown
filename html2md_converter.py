#!/usr/bin/env python3
"""
Confluence HTML to GitBook Markdown Directory Converter

This script converts a directory structure of HTML files (exported from Confluence)
into clean Markdown, preserving the directory structure and handling images correctly.
It removes Confluence-specific elements and cleans up file names.

Usage:
    python html2md_converter.py <input_directory> <output_directory>
"""

import os
import sys
import re
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
import html2text
import argparse
import urllib.parse
from collections import Counter

# Track common prefixes across all titles
common_prefixes = Counter()
removed_prefix = None

def setup_html2text():
    """Configure html2text with appropriate settings."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True  # Tell html2text to ignore image tags, we'll handle them manually
    h.ignore_emphasis = False
    h.ignore_tables = True  # Ignore tables since we handle them manually
    h.body_width = 0  # Don't wrap text
    h.unicode_snob = True  # Use Unicode instead of ASCII
    h.wrap_links = False  # Don't wrap links
    h.mark_code = True  # Wrap code blocks
    
    # Define our custom image handling function to ensure img tags aren't converted
    def handle_img(self, tag):
        # Skip all image processing - we'll handle them via placeholders
        pass
    
    # Override the image handling method
    h.handle_img = handle_img.__get__(h)
    
    return h

def process_images_with_placeholders(soup, html_file_path, output_dir, rel_path, folder_depth=0):
    """
    Process images by replacing them with placeholders in the HTML,
    and return a mapping of placeholders to processed image HTML.
    
    This allows us to preserve the original image positions in the document.
    
    Args:
        soup: BeautifulSoup object with the HTML content
        html_file_path: Path to the HTML file being processed
        output_dir: Base output directory
        rel_path: Relative path of the HTML file
        folder_depth: How many folder levels deep the output file will be
    """
    html_dir = os.path.dirname(html_file_path)
    image_map = {}
    image_count = 0
    
    # Calculate relative path to images based on folder depth
    image_rel_prefix = "../" * folder_depth if folder_depth > 0 else ""
    
    # First handle img tags directly in HTML
    for img in soup.find_all('img'):
        if 'src' not in img.attrs:
            continue
        
        image_count += 1
        placeholder = f"__IMAGE_PLACEHOLDER_{image_count}__"
        
        src = img['src']
        alt = img.get('alt', '')
        title = img.get('title', '')
        width = img.get('width', '')
        height = img.get('height', '')
        
        # Skip external images, just update the placeholder
        if src.startswith(('http://', 'https://')):
            image_html = f'<img src="{src}" alt="{alt}" title="{title}" style="width: 100%;">'
            image_map[placeholder] = image_html
            placeholder_tag = soup.new_tag('div')
            placeholder_tag.string = placeholder
            img.replace_with(placeholder_tag)
            continue
        
        # Handle local images
        src = urllib.parse.unquote(src)
        if src.startswith('/'):
            src = src.lstrip('/')
            
        # Construct source and destination paths
        src_path = os.path.join(html_dir, src)
        
        # Handle Confluence attachment paths
        if not os.path.isfile(src_path) and 'attachments' in src:
            # Try to find the file in the attachments directory
            attachments_dirs = [d for d in os.listdir(html_dir) if 'attachments' in d.lower()]
            for attachments_dir in attachments_dirs:
                attachment_path = os.path.join(html_dir, attachments_dir, os.path.basename(src))
                if os.path.isfile(attachment_path):
                    src_path = attachment_path
                    break
        
        # Create relative destination path
        img_rel_path = os.path.join(rel_path, os.path.basename(src))
        dest_path = os.path.join(output_dir, 'images', img_rel_path)
        
        # Ensure the destination directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Copy the image file if it exists
        if os.path.isfile(src_path):
            try:
                shutil.copy2(src_path, dest_path)
                # Create the image HTML with updated path adjusted for folder depth
                new_src = os.path.join(image_rel_prefix + 'images', img_rel_path).replace('\\', '/')
                image_html = f'<img src="{new_src}" alt="{alt}" title="{title}" style="width: 100%;">'
                image_map[placeholder] = image_html
            except (shutil.Error, IOError) as e:
                print(f"Error copying image {src_path}: {e}")
                # Keep original path in case of error
                image_html = f'<img src="{src}" alt="{alt}" title="{title}" style="width: 100%;">'
                image_map[placeholder] = image_html
        else:
            print(f"Warning: Image file not found: {src_path}")
            # Keep original path if file not found
            image_html = f'<img src="{src}" alt="{alt}" title="{title}" style="width: 100%;">'
            image_map[placeholder] = image_html
        
        # Replace image with placeholder in the HTML
        placeholder_tag = soup.new_tag('div')
        placeholder_tag.string = placeholder
        img.replace_with(placeholder_tag)
    
    # Also look for markdown-style image references in any pre or code blocks
    # and replace them with placeholders
    for pre in soup.find_all(['pre', 'code']):
        if pre.string:
            for match in re.finditer(r'!\[(.*?)\]\((.*?)\)', pre.string):
                image_count += 1
                placeholder = f"__IMAGE_PLACEHOLDER_{image_count}__"
                alt_text = match.group(1)
                img_src = match.group(2)
                
                # Adjust image path based on folder depth
                if not img_src.startswith(('http://', 'https://')):
                    img_src = image_rel_prefix + img_src
                
                # Create HTML image tag
                image_html = f'<img src="{img_src}" alt="{alt_text}" style="width: 100%;">'
                image_map[placeholder] = image_html
                
                # Replace in the text
                pre.string = pre.string.replace(match.group(0), placeholder)
    
    return soup, image_map

def replace_image_placeholders(markdown_content, image_map):
    """Replace image placeholders in markdown with the actual image HTML."""
    # Split the content into lines to detect captions
    lines = markdown_content.split('\n')
    
    # Process lines to find image placeholders and potential captions
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line contains any image placeholders and replace ALL of them
        placeholders_found = []
        for placeholder in image_map.keys():
            if placeholder in line:
                placeholders_found.append(placeholder)
        
        if placeholders_found:
            # Process each placeholder found on this line
            for placeholder_match in placeholders_found:
                # Get the image HTML
                image_html = image_map[placeholder_match]
                
                # Check if there are subsequent lines for caption text
                caption_text = ""
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Skip empty lines
                    if not next_line:
                        j += 1
                        continue
                    
                    # Skip if the next line is a heading, horizontal rule, another image, or table
                    if (next_line.startswith('#') or 
                        re.match(r'^-{3,}$', next_line) or 
                        '<img' in next_line or 
                        any(p in next_line for p in image_map.keys()) or
                        next_line.startswith('|')):
                        break
                    
                    # Found potential caption text
                    caption_text = next_line
                    
                    # Convert markdown formatting to HTML tags instead of removing it
                    # Convert __text__ or **text** to <strong>text</strong>
                    caption_text = re.sub(r'(__|\*\*)([^_*]+)(__|\*\*)', r'<strong>\2</strong>', caption_text)
                    
                    # Convert _text_ or *text_ to <em>text</em>
                    caption_text = re.sub(r'(_|\*)([^_*]+)(_|\*)', r'<em>\2</em>', caption_text)
                    
                    # Remove the caption line
                    lines.pop(j)
                    break
                    
                # Fix image tag to remove duplicate style
                image_html = re.sub(r' style="width: 100%;"', '', image_html, count=1)
                
                # Wrap in figure tag with caption if available
                if caption_text:
                    figure_html = f'<figure>{image_html}<figcaption><p>{caption_text}</p></figcaption></figure>'
                else:
                    figure_html = f'<figure>{image_html}</figure>'
                
                # Replace this specific placeholder in the line
                lines[i] = lines[i].replace(placeholder_match, figure_html)
        
        i += 1
    
    # Join lines back into content
    processed_content = '\n'.join(lines)
    
    # Make sure no dashes are added after the image replacement
    # This prevents the "---" horizontal rule after images
    processed_content = re.sub(r'<figure>.*?</figure>\n---', lambda m: m.group(0).replace('\n---', ''), processed_content, flags=re.DOTALL)
    processed_content = re.sub(r'<figure>.*?</figure>\n----', lambda m: m.group(0).replace('\n----', ''), processed_content, flags=re.DOTALL)
    
    return processed_content

def convert_tables_to_markdown(soup):
    """Convert HTML tables to markdown tables manually to ensure proper formatting."""
    for table in soup.find_all('table'):
        rows = []
        
        # Process each row
        for row in table.find_all('tr'):
            cells = []
            row_type = 'data'  # Track if this is a header or data row
            
            for cell in row.find_all(['td', 'th']):
                if cell.name == 'th':
                    row_type = 'header'
                    
                # Get cell text content and clean it up
                cell_text = cell.get_text(' ', strip=True)
                # Escape pipe characters
                cell_text = cell_text.replace('|', '\\|')
                # Remove excessive whitespace
                cell_text = ' '.join(cell_text.split())
                # Handle empty cells
                if not cell_text:
                    cell_text = ' '
                cells.append(cell_text)
            
            if cells:  # Only add non-empty rows
                # Skip rows that contain only separator-like content
                is_separator_content = all(cell.strip() in ['---', '-', ''] for cell in cells)
                if not is_separator_content:
                    rows.append((cells, row_type))
        
        if rows:
            # Determine number of columns from the first row
            max_cols = max(len(row_data[0]) for row_data in rows) if rows else 0
            
            # Pad all rows to have the same number of columns
            for i, (row, row_type) in enumerate(rows):
                while len(row) < max_cols:
                    row.append(' ')
                rows[i] = (row, row_type)
            
            # Create markdown table
            markdown_lines = []
            
            # Find the first header row or use the first row as header
            header_row = None
            data_rows = []
            
            for row_data, row_type in rows:
                if row_type == 'header' and header_row is None:
                    header_row = row_data
                else:
                    data_rows.append(row_data)
            
            # If no header found, use first row as header
            if header_row is None and rows:
                header_row = rows[0][0]
                data_rows = [row_data for row_data, _ in rows[1:]]
            
            if header_row:
                # Header row
                header = '| ' + ' | '.join(header_row) + ' |'
                markdown_lines.append(header)
                
                # Separator row
                separator = '|' + '---|' * max_cols
                markdown_lines.append(separator)
                
                # Data rows
                for row in data_rows:
                    data_row = '| ' + ' | '.join(row) + ' |'
                    markdown_lines.append(data_row)
            
            # Replace the table with the markdown version
            markdown_table = '\n'.join(markdown_lines)
            
            # Create a new pre tag to preserve line breaks
            new_pre = soup.new_tag('pre')
            new_pre.string = '\n' + markdown_table + '\n'
            new_pre['data-markdown-table'] = 'true'  # Mark it as a markdown table
            
            # Also remove any stray table-related elements around this table
            parent = table.parent
            table.replace_with(new_pre)
            
            # Clean up any remaining table fragments in the parent
            if parent:
                for stray_element in parent.find_all(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot']):
                    stray_element.decompose()
    
    return soup

def escape_pipe_chars_in_tables(soup):
    """Escape pipe characters in table cell content to prevent markdown table breaking."""
    for table in soup.find_all('table'):
        for cell in table.find_all(['td', 'th']):
            # Process all text content in the cell
            for text_node in cell.find_all(string=True):
                if '|' in text_node:
                    # Replace pipe characters with HTML entity
                    new_text = text_node.replace('|', '&#124;')
                    text_node.replace_with(new_text)
    return soup

def clean_table_cells(soup):
    """Clean up table cell content to improve markdown conversion."""
    for table in soup.find_all('table'):
        for cell in table.find_all(['td', 'th']):
            # Remove excessive nested divs and wrappers that don't add content
            for wrapper in cell.find_all(['div'], class_=['content-wrapper']):
                if wrapper.find('div') or wrapper.find('p') or wrapper.find('ul') or wrapper.find('ol'):
                    # If the wrapper contains block elements, unwrap it
                    wrapper.unwrap()
            
            # Clean up footnote markers and references
            for footnote in cell.find_all(['sup']):
                # Keep the footnote number but remove complex styling
                if footnote.find('a'):
                    footnote_text = footnote.get_text(strip=True)
                    if footnote_text:
                        footnote.clear()
                        footnote.string = footnote_text
            
            # Clean up status macros (REQUIRED, RECOMMENDED, etc.)
            for status in cell.find_all(class_=['status-macro']):
                status_text = status.get_text(strip=True)
                if status_text:
                    status.replace_with(f"**{status_text}**")
            
            # Remove empty inline spans that don't add content
            for span in cell.find_all('span'):
                if not span.get_text(strip=True) and not span.find():
                    span.decompose()
                elif span.get('id') and span.get('id').startswith('backref'):
                    # Remove backref spans which are just for footnote positioning
                    span.decompose()
            
            # Handle complex content in cells by flattening it
            # Convert block elements to inline with separators
            for div in cell.find_all('div'):
                if div.get('style') and 'border-style:solid' in div.get('style'):
                    # This is likely a code block or example, wrap it properly
                    div.name = 'pre'
                    # Remove style attributes to clean it up
                    if 'style' in div.attrs:
                        del div['style']
                else:
                    # Regular div, unwrap it
                    div.unwrap()
            
            # Convert multiple paragraphs in a cell to a single paragraph with line breaks
            paragraphs = cell.find_all('p')
            if len(paragraphs) > 1:
                # Collect all paragraph content
                combined_content = []
                for p in paragraphs:
                    content = p.get_text(strip=True)
                    if content:
                        combined_content.append(content)
                    p.decompose()
                
                # Create a single paragraph with the combined content
                if combined_content:
                    new_p = soup.new_tag('p')
                    new_p.string = ' '.join(combined_content)
                    cell.append(new_p)
            
            # Convert line breaks to spaces in cell content to prevent table breaking
            for br in cell.find_all('br'):
                br.replace_with(' ')
    
    return soup

def clean_confluence_html(soup):
    """Remove Confluence-specific elements from the HTML."""
    # Remove common Confluence navigation and UI elements
    confluence_elements = [
        # Header, footer, navigation
        'header', 'footer', 'nav', '.aui-header', '.aui-sidebar', '.ia-splitter-sidebar',
        '#navigation', '#header', '#footer', '.page-metadata', '.page-metadata-container',
        
        # Comments and other UI elements
        '#comments-section', '.comments-container', '.likes-and-labels-container',
        '.page-tools', '.ia-secondary-container', '.ia-secondary-content', 
        
        # Confluence specific classes (but NOT content layout containers)
        '.aui-buttons',
        '.ia-fixed-sidebar', '.acs-side-bar', '.ia-secondary-header-title',
        '.ia-secondary-parent-hd', '.analytics-container', '.page-children', 
        '.plugin_pagetree', '.ia-splitter-handle',
        
        # Confluence macros that usually don't translate well
        '.status-macro', '.viewfile-macro', '.panel-macro', '.expand-container',
        '.aui-message', '.aui-icon', '.plugin_attachments', '.toc-macro'
    ]
    
    # Use CSS selectors to find and remove elements
    for selector in confluence_elements:
        try:
            if selector.startswith('.') or selector.startswith('#'):
                # It's a class or id
                if selector.startswith('.'):
                    elements = soup.find_all(class_=selector[1:])
                else:  # Starts with #
                    elements = soup.find_all(id=selector[1:])
            else:
                # It's a tag name
                elements = soup.find_all(selector)
                
            for element in elements:
                element.decompose()
        except Exception as e:
            print(f"Error removing {selector}: {e}")
    
    # Handle confluence-information-macro more selectively
    # Remove only navigation-type info macros, keep content-bearing ones
    for info_macro in soup.find_all(class_='confluence-information-macro'):
        try:
            # Check if this is just a navigation macro (like "In this page:")
            title_elem = info_macro.find(class_='title')
            if title_elem and title_elem.get_text(strip=True).lower() in ['in this page:', 'on this page:', 'contents:']:
                # This looks like a table of contents, remove it
                info_macro.decompose()
            else:
                # Keep other information macros as they might contain useful content
                # Just remove the icon and styling, keep the text content
                for icon in info_macro.find_all(class_='aui-icon'):
                    icon.decompose()
                # Remove the macro wrapper but keep content
                if info_macro.find(class_='confluence-information-macro-body'):
                    body = info_macro.find(class_='confluence-information-macro-body')
                    info_macro.replace_with(body)
        except Exception as e:
            print(f"Error processing info macro: {e}")
    
    # Remove empty H1 tags or H1 tags with only styling
    for h1 in soup.find_all('h1'):
        # Check if empty or only contains whitespace/styling tags
        if not h1.get_text(strip=True) or h1.get_text(strip=True) == "":
            h1.decompose()
        elif len(h1.get_text(strip=True)) < 3:  # Very short content is likely just styling
            h1.decompose()
        # Check for hidden H1 tags (often used for styling in Confluence)
        elif 'style' in h1.attrs and 'display:none' in h1['style']:
            h1.decompose()
        elif h1.find('span', style=lambda s: s and 'display:none' in s):
            h1.decompose()
    
    # Try to extract just the main content
    main_content = soup.find(id='main-content') or soup.find(class_='wiki-content') or soup.find(id='content')
    
    if main_content:
        # Replace the body with just the main content
        if soup.body:
            # Save the title if it exists
            title_tag = soup.title
            
            # Clear body content and add only main content
            soup.body.clear()
            soup.body.append(main_content)
            
            # Restore title if it existed
            if title_tag and not soup.title:
                soup.head.append(title_tag)
    
    return soup

def clean_confluence_filename(filename):
    """
    Clean Confluence export filenames by removing page IDs and other junk,
    while preserving section numbering format (e.g., 1, 2.1, 5.3.2, etc.)
    Examples: 
    - "12345678-My-Page-Title.html" becomes "my-page-title.html"
    - "My-Page-Title-12345678.html" becomes "my-page-title.html"
    - "My-Page-Title_12345678.html" becomes "my-page-title.html"
    - "1-Introduction_12345678.html" becomes "1-introduction.html"
    - "2.1-Section-Title_12345678.html" becomes "2.1-section-title.html"
    - "6.4.-Distribution_35985762.html" becomes "6.4-distribution.html" (removes trailing dot)
    """
    # Get the filename without extension
    basename, ext = os.path.splitext(filename)
    
    # Remove page ID prefix (digits and dash at the beginning, but not if it's a chapter number)
    # We want to preserve "1-" or "2-" at the beginning, but remove "12345-"
    # Only remove if there are 5 or more digits at the beginning
    cleaned = re.sub(r'^(\d{5,})-', '', basename)
    
    # Remove page ID suffix (dash/underscore and digits at the end)
    cleaned = re.sub(r'-\d+$', '', cleaned)  # Remove trailing -12345
    cleaned = re.sub(r'_\d+$', '', cleaned)  # Remove trailing _12345
    
    # Special handling for section numbering with trailing dots
    # First, look for formats like "6.4." (with trailing dot) and fix them
    cleaned = re.sub(r'(\d+(?:\.\d+)*)\.-', r'\1-', cleaned)
    
    # Now the regular section number check after fixes
    section_match = re.match(r'^(\d+(?:\.\d+)*)-(.+)$', cleaned)
    section_prefix = ""
    if section_match:
        # Save the section number including dots
        section_prefix = section_match.group(1)
        # Remove it from the string for now (we'll add it back later)
        cleaned = cleaned[len(section_prefix) + 1:]  # +1 for the hyphen
    
    # Convert to lowercase and replace spaces/underscores with hyphens
    cleaned = cleaned.lower().replace('_', '-').replace(' ', '-')
    
    # Remove any other invalid characters, but preserve dots for file extensions
    cleaned = re.sub(r'[^a-z0-9-]', '', cleaned)
    
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    
    # Trim leading/trailing hyphens
    cleaned = cleaned.strip('-')
    
    # Make sure we have a non-empty filename
    if not cleaned and not section_prefix:
        cleaned = "page"
    
    # Add back the section prefix if it existed
    if section_prefix:
        cleaned = section_prefix + "-" + cleaned
    
    # Add back the extension
    return cleaned + ext

def find_common_title_prefix(titles):
    """
    Find common prefix across all titles.
    Returns the prefix and its frequency if it appears in enough titles.
    """
    # Extract potential prefixes with separators like ":" or "-"
    prefix_candidates = []
    for title in titles:
        match = re.search(r'^(.+?)(?:\s*[:|-]\s+)(.+)$', title)
        if match:
            prefix = match.group(1).strip()
            prefix_candidates.append(prefix)
    
    # Count occurrences of each prefix
    prefix_counter = Counter(prefix_candidates)
    
    # Find most common prefix that appears in at least 50% of titles
    if prefix_candidates:
        most_common = prefix_counter.most_common(1)[0]
        prefix, count = most_common
        if count >= len(titles) * 0.5 and len(prefix) > 0:
            return prefix, count
    
    return None, 0

def clean_title(title_text, global_prefix=None):
    """
    Clean up the title by removing repeated site titles and Confluence suffix.
    Uses both global prefix detection and pattern detection for greater flexibility.
    """
    # First remove Confluence suffix
    title_text = re.sub(r'\s*-\s*Confluence.*$', '', title_text.strip())
    
    # Remove identified global prefix if present
    if global_prefix and title_text.startswith(global_prefix):
        separator_match = re.search(f'^{re.escape(global_prefix)}\\s*[:|-]\\s+', title_text)
        if separator_match:
            return title_text[len(separator_match.group(0)):].strip()
    
    # Look for common title patterns with separators like ":" or "-"
    site_title_match = re.search(r'^(.+?)(?:\s*[:|-]\s+)(.+)$', title_text)
    if site_title_match:
        site_title, page_title = site_title_match.groups()
        
        # Rule 1: If site title is less than 30% of the full title length
        if len(site_title) < len(title_text) * 0.3:
            return page_title.strip()
            
        # Rule 2: If site title appears multiple times in the document
        if site_title.lower() in page_title.lower():
            return page_title.strip()
            
        # Rule 3: If site title matches known patterns (e.g., ends with "Guide", "Documentation", etc.)
        if re.search(r'(guide|docs|documentation|manual|handbook|reference|standard|user guide|starter)(?:\s+|$)', 
                    site_title.lower()):
            return page_title.strip()
            
        # Rule 4: If the site title follows a "Product Name + Content Type" pattern
        # For example: "Product Analytics with X" or "X Starter Guide"
        if re.search(r'(?:with|for|using|in)\s+\w+\s*$', site_title.lower()) or \
           re.search(r'^\w+(?:\s+\w+)?\s+(?:guide|standard|reference|docs)$', site_title.lower()):
            return page_title.strip()
    
    return title_text

def restore_markdown_tables(md_content):
    """Extract markdown tables from code blocks and restore them as proper tables."""
    # Pattern to find [code] blocks that contain our markdown tables
    pattern = r'\[code\]\s*\n((?:\s*\|.*\|\s*\n)+)\s*\[/code\]'
    
    def replace_table(match):
        table_content = match.group(1).strip()
        # Clean up the table lines
        lines = table_content.split('\n')
        cleaned_lines = []
        seen_separator = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('|') and line.endswith('|'):
                # Check if this line is a separator row (only contains |, -, and spaces)
                # This regex matches lines like |---|---| or | --- | --- | etc.
                # For any number of columns
                cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Remove first and last empty cells
                is_separator = all(cell in ['---', '-', ''] or re.match(r'^-+$', cell) for cell in cells if cell.strip())
                
                if is_separator:
                    if not seen_separator:
                        cleaned_lines.append(line)
                        seen_separator = True
                    # Skip additional separator rows (this should catch the | --- | --- | --- | format)
                else:
                    cleaned_lines.append(line)
        
        return '\n' + '\n'.join(cleaned_lines) + '\n'
    
    # Replace code-blocked tables with raw markdown tables
    md_content = re.sub(pattern, replace_table, md_content, flags=re.MULTILINE)
    
    # Also handle ``` style code blocks
    pattern2 = r'```\s*\n((?:\s*\|.*\|\s*\n)+)\s*```'
    md_content = re.sub(pattern2, replace_table, md_content, flags=re.MULTILINE)
    
    return md_content

def is_table_separator(line):
    """Check if a line is a markdown table separator."""
    if not line.startswith('|') or not line.endswith('|'):
        return False
    
    # Split by | and check the content between
    cells = line.split('|')[1:-1]  # Remove first and last empty parts
    for cell in cells:
        cell = cell.strip()
        if not cell or not re.match(r'^-+$', cell):
            return False
    
    return len(cells) > 0  # Must have at least one cell

def remove_duplicate_table_separators(md_content):
    """Remove duplicate table separator rows."""
    lines = md_content.split('\n')
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped_line = line.strip()
        
        # If this line is a table separator, check if the next line is also a separator
        if stripped_line and is_table_separator(stripped_line):
            # Add this separator only if we haven't just added one
            if not cleaned_lines or not is_table_separator(cleaned_lines[-1].strip()):
                cleaned_lines.append(line)
            # Skip any consecutive separators
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line and is_table_separator(next_line):
                    j += 1  # Skip this duplicate separator
                else:
                    break
            i = j - 1  # Will be incremented at the end of the loop
        else:
            cleaned_lines.append(line)
        
        i += 1
    
    return '\n'.join(cleaned_lines)

def fix_markdown_tables(md_content):
    """Fix markdown table formatting issues."""
    lines = md_content.split('\n')
    fixed_lines = []
    in_table = False
    table_columns = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect table header
        if '|' in line and i + 1 < len(lines) and '---' in lines[i + 1]:
            # This is the start of a table
            in_table = True
            # Count columns from header
            table_columns = len([cell for cell in line.split('|') if cell.strip()]) if '|' in line else 0
            
            # Fix header line
            line = line.replace('&#124;', '\\|')
            if line.strip().startswith('|') and line.strip().endswith('|'):
                fixed_lines.append(line)
            else:
                # Ensure proper table structure
                parts = [part.strip() for part in line.split('|')]
                if parts and not parts[0]:
                    parts = parts[1:]  # Remove empty first element
                if parts and not parts[-1]:
                    parts = parts[:-1]  # Remove empty last element
                line = '| ' + ' | '.join(parts) + ' |'
                fixed_lines.append(line)
            
            # Handle separator line
            i += 1
            if i < len(lines):
                separator = lines[i]
                fixed_lines.append(separator)
            continue
        
        # Check if we're still in a table
        elif in_table:
            if line.strip() == '':
                # Empty line might indicate end of table, but let's be cautious
                # Look ahead to see if there are more table-like lines
                next_table_line = False
                for j in range(i + 1, min(i + 3, len(lines))):
                    if j < len(lines) and '|' in lines[j] and lines[j].strip():
                        next_table_line = True
                        break
                
                if not next_table_line:
                    in_table = False
                    fixed_lines.append(line)
                    i += 1
                    continue
                else:
                    # Skip empty lines in tables
                    i += 1
                    continue
            
            elif '|' in line:
                # This is a table row
                line = line.replace('&#124;', '\\|')
                
                # Ensure proper table structure
                parts = [part.strip() for part in line.split('|')]
                if parts and not parts[0]:
                    parts = parts[1:]  # Remove empty first element
                if parts and not parts[-1]:
                    parts = parts[:-1]  # Remove empty last element
                
                # Pad or trim to match table columns
                while len(parts) < table_columns:
                    parts.append('')
                if len(parts) > table_columns:
                    parts = parts[:table_columns]
                
                line = '| ' + ' | '.join(parts) + ' |'
                fixed_lines.append(line)
                i += 1
                continue
            
            elif line.strip() and not line.strip().startswith('#'):
                # Non-table content while in table - might be continuation of previous cell
                # Try to append to the previous line if it was a table row
                if fixed_lines and '|' in fixed_lines[-1]:
                    # Append to the last cell of the previous row
                    last_line = fixed_lines[-1]
                    if last_line.strip().endswith('|'):
                        # Remove the trailing |, add content, then add | back
                        last_line = last_line.rstrip().rstrip('|').rstrip()
                        fixed_lines[-1] = last_line + ' ' + line.strip() + ' |'
                        i += 1
                        continue
                
                # Otherwise, end the table
                in_table = False
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def clean_markdown(md_content):
    """Clean up the markdown output by removing empty headings and other artifacts."""
    # Remove lines that are just # with no content
    lines = md_content.split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip lines that are just heading markers with no content
        if re.match(r'^#+\s*$', line.strip()):
            i += 1
            continue
        
        # Skip lines with just a heading followed by nothing or minimal content
        if re.match(r'^#+\s*\W*$', line.strip()):
            i += 1
            continue
        
        # Skip Confluence-specific formatting lines
        if "<span" in line and ("display:none" in line or "h2-promote" in line):
            i += 1
            continue
        
        # Check for image or figure followed by horizontal rule (---)
        if ('<img src=' in line or '<figure>' in line) and i + 1 < len(lines) and re.match(r'^-{3,}\s*$', lines[i+1].strip()):
            # Add the image/figure line without the horizontal rule
            cleaned_lines.append(line)
            # Skip the horizontal rule line
            i += 2
            continue

        # Check for image/figure inside a table with | markers that gets followed by horizontal rule
        if '|' in line and ('<img src=' in line or '<figure>' in line) and i + 1 < len(lines) and re.match(r'^-{3,}\s*$', lines[i+1].strip()):
            # Extract just the image/figure tag from the line
            img_match = re.search(r'<(img src=[^>]+|figure>.*?</figure)>', line, re.DOTALL)
            if img_match:
                # Replace the line with just the image/figure
                cleaned_lines.append(img_match.group(0))
            else:
                # If we can't extract the image/figure, keep the original line
                cleaned_lines.append(line)
            # Skip the horizontal rule line
            i += 2
            continue
        
        # Clean up lines that contain only an image/figure with table formatting (| prefix)
        # while preserving blank lines before and after
        if re.match(r'^\s*\|\s*(<img\s+src=.*>|<figure>.*?</figure>)\s*$', line, re.DOTALL):
            # Check if the previous line was blank and preserve it
            if i > 0 and not lines[i-1].strip() and (len(cleaned_lines) == 0 or cleaned_lines[-1] != ''):
                # Make sure we don't add duplicate blank lines
                cleaned_lines.append('')
            
            # Extract just the image/figure tag
            img_match = re.search(r'<(img[^>]+>|figure>.*?</figure>)', line, re.DOTALL)
            if img_match:
                # Replace the line with just the image/figure
                cleaned_lines.append('<' + img_match.group(1))
            else:
                # If we can't extract the image/figure, keep the original line
                cleaned_lines.append(line)
            
            # Check if the next line is blank and preserve it
            if i + 1 < len(lines) and not lines[i+1].strip():
                cleaned_lines.append('')
                i += 2  # Skip both the image and the blank line
            else:
                i += 1  # Just skip the image line
            continue
            
        # Remove empty table lines (just dashes)
        if re.match(r'^---+\s*$', line.strip()) and (not cleaned_lines or '|' not in cleaned_lines[-1]):
            i += 1
            continue
            
        # Convert any Markdown-style image links to HTML img tags with figure wrapper
        # Pattern: ![alt text](image.jpg) -> <figure><img src="image.jpg" alt="alt text" style="width: 100%;"></figure>
        if re.search(r'!\[.*?\]\(.*?\)', line):
            # Find the first non-empty, non-heading, non-image line after this one for caption
            caption_text = ""
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Skip empty lines
                if not next_line:
                    j += 1
                    continue
                
                # Skip if the next line is a heading, horizontal rule, another image, or table
                if (next_line.startswith('#') or 
                    re.match(r'^-{3,}$', next_line) or 
                    '![' in next_line or 
                    '<img' in next_line or
                    next_line.startswith('|')):
                    break
                
                # Found potential caption text
                caption_text = next_line
                
                # Convert markdown formatting to HTML tags instead of removing it
                # Convert __text__ or **text** to <strong>text</strong>
                caption_text = re.sub(r'(__|\*\*)([^_*]+)(__|\*\*)', r'<strong>\2</strong>', caption_text)
                
                # Convert _text_ or *text* to <em>text</em>
                caption_text = re.sub(r'(_|\*)([^_*]+)(_|\*)', r'<em>\2</em>', caption_text)
                
                # Remove the caption line from the original list
                lines.pop(j)
                break
            
            if caption_text:
                line = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<figure><img src="\2" alt="\1" style="width: 100%;"><figcaption><p>' + caption_text + r'</p></figcaption></figure>', line)
            else:
                line = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<figure><img src="\2" alt="\1" style="width: 100%;"></figure>', line)
        
        cleaned_lines.append(line)
        i += 1
    
    # Join lines back together
    cleaned_md = '\n'.join(cleaned_lines)
    
    # Fix multiple consecutive newlines (more than 2)
    cleaned_md = re.sub(r'\n{3,}', '\n\n', cleaned_md)
    
    # Convert any remaining Markdown image links that might span multiple lines
    # No caption handling here since this is a final fallback for any remaining markdown images
    cleaned_md = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<figure><img src="\2" alt="\1" style="width: 100%;"></figure>', cleaned_md, flags=re.DOTALL)
    
    # Clean up any remaining cases of image/figure followed by horizontal rule
    cleaned_md = re.sub(r'(<img[^>]+>|<figure>.*?</figure>)\s*\n\s*[-]{3,}', r'\1', cleaned_md)
    
    # Final pass to clean up any remaining table-formatted images/figures while preserving spacing
    # This regex now preserves blank lines before and after the image/figure
    cleaned_md = re.sub(r'(^|\n\n)\s*\|\s*(<img[^>]+>|<figure>.*?</figure>)\s*$', r'\1\2', cleaned_md, flags=re.MULTILINE)
    
    # Ensure images and figures have proper spacing (blank line before and after)
    # First, find standalone image/figure lines that don't have a blank line before
    cleaned_md = re.sub(r'([^\n])\n(<img[^>]+>|<figure>)', r'\1\n\n\2', cleaned_md)
    
    # Then find standalone image/figure lines that don't have a blank line after
    cleaned_md = re.sub(r'(<img[^>]+>|</figure>)\n([^\n])', r'\1\n\n\2', cleaned_md)
    
    # Fix any img tags that are not wrapped in figure tags
    img_pattern = re.compile(r'<img\s([^>]*?)(?:style="[^"]*")?([^>]*)>', re.DOTALL)
    
    def replace_img(match):
        img_attrs = match.group(1) + match.group(2)
        return f'<figure><img {img_attrs} style="width: 100%;"></figure>'
    
    # Only replace img tags that are not already inside figure tags
    parts = re.split(r'(<figure>.*?</figure>)', cleaned_md, flags=re.DOTALL)
    result_parts = []
    
    for part in parts:
        if part.startswith('<figure>'):
            # This part already has figure tags, leave it as is
            result_parts.append(part)
        else:
            # Replace standalone img tags with figure-wrapped tags
            result_parts.append(img_pattern.sub(replace_img, part))
    
    cleaned_md = ''.join(result_parts)
    
    return cleaned_md

def get_section_path(filename, title_mapping=None, subsection_counts=None):
    """
    Determine the correct folder structure and file path based on section numbering.
    Will create proper nested folder structure for subsections with multiple files,
    while avoiding unnecessary folders for isolated files.
    
    Args:
        filename: The cleaned markdown filename
        title_mapping: Dictionary mapping section numbers to titles
        subsection_counts: Dictionary tracking how many pages are in each subsection
    
    Returns a tuple of (folder_path, file_name, folder_depth)
    """
    # Get filename without extension
    basename, ext = os.path.splitext(filename)
    
    # Check if this is a section/subsection file
    # Make sure to check for traditional section patterns as well as those with trailing dots
    section_match = re.match(r'^(\d+(?:\.\d+)*)-(.+)$', basename)
    if not section_match:
        # No section numbering, keep in root
        return "", filename, 0
    
    section_number = section_match.group(1)
    section_title = section_match.group(2)
    
    # Split the section number to get hierarchy (e.g., "4.3.1" → ["4", "3", "1"])
    parts = section_number.split('.')
    
    # Top-level section always gets a folder
    main_section_number = parts[0]
    main_section_title = title_mapping.get(main_section_number, section_title if len(parts) == 1 else "section")
    main_folder = f"{main_section_number} {main_section_title}"
    
    # For single-part sections (e.g., "4-logical-design.md"), it becomes README.md
    if len(parts) == 1:
        return main_folder, "README.md", 1
    
    # Initialize folder structure
    folder_path = main_folder
    folder_depth = 1
    current_section = main_section_number
    level_title = main_section_title  # Initialize to avoid UnboundLocalError
    has_subsections = False            # Initialize to avoid UnboundLocalError
    is_leaf = True                     # Default value if we don't enter the loop
    
    # Build the folder path recursively for each level of the section hierarchy
    for i in range(1, len(parts)):
        # Get section number up to this level (e.g., "4.2" or "4.3.1")
        current_section = '.'.join(parts[:i+1])
        
        # Check if this is the terminal (leaf) part of the section number
        is_leaf = (i == len(parts) - 1)
        
        # Get the section count for the current section (how many files exist at this exact level)
        section_count = subsection_counts.get(current_section, 0) if subsection_counts else 0
        
        # Look ahead to check if we have any deeper subsections
        has_subsections = False
        if subsection_counts:
            prefix = current_section + "."
            for section in subsection_counts:
                if section.startswith(prefix):
                    has_subsections = True
                    break
        
        # If this is a leaf section (e.g., 4.2.1 with no further subsections like 4.2.1.1),
        # and it's the only file at this level, we don't need a separate folder for it
        if is_leaf and section_count <= 1 and not has_subsections:
            # Just place this file in the parent folder
            break
        
        # Otherwise we need a folder for this level
        level_title = title_mapping.get(current_section, "section")
        subfolder = f"{current_section} {level_title}"
        folder_path = os.path.join(folder_path, subfolder)
        folder_depth += 1
    
    # Determine the file name based on if it's a "README" or a regular file
    if is_leaf:
        # This is the final part of the section number (e.g., the "3" in "4.2.3")
        if parts[-1] == "1" and len(parts) > 1:
            # Special handling for "*.*.1" files
            if has_subsections:
                # If this is like "4.2.1" and has subsections like "4.2.1.1", it should be README.md
                file_name = "README.md"
            else:
                # Otherwise, it's a regular file
                file_name = f"{section_number}-{section_title}.md"
        else:
            # For sections not ending in "1" (like "4.2"), they become README.md
            # if the folder exists for them
            if folder_path.endswith(f"{current_section} {level_title}"):
                file_name = "README.md"
            else:
                file_name = f"{section_number}-{section_title}.md"
    else:
        # We broke out of the loop early - this is a file that doesn't need its own folder
        file_name = f"{section_number}-{section_title}.md"
    
    return folder_path, file_name, folder_depth

def convert_html_to_markdown(html_file_path, output_dir, rel_path, title_mapping=None, subsection_counts=None, global_prefix=None):
    """Convert an HTML file to Markdown and save it to the output directory."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title if available
        title = ""
        title_text = ""
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            # Clean the title text using both global prefix and regular cleaning
            original_title = title_tag.string
            title_text = clean_title(original_title, global_prefix)
            title = f"# {title_text}\n\n"
        
        # Clean Confluence-specific elements
        soup = clean_confluence_html(soup)
        
        # Clean up table cells and convert tables to markdown manually
        soup = clean_table_cells(soup)
        soup = convert_tables_to_markdown(soup)
        
        # Determine output path and folder depth before processing images
        original_filename = os.path.basename(html_file_path)
        
        # Check if filename is just a numeric ID
        is_numeric_id = re.match(r'^\d+\.html$', original_filename) is not None
        
        # For numeric-only filenames, use the title instead
        if is_numeric_id and title_text:
            # Extract section number if present
            section_match = re.search(r'^(?:(?:\d+(?:\.\d+)*)|(?:\d+(?:\.\d+)*\.))[\s\-:]+(.+)', title_text)
            if section_match:
                # Extract the section number, handling both formats like "6.4" and "6.4."
                section_parts = title_text.split()
                section_num = section_parts[0].rstrip('.')  # Remove trailing dot if present
                section_title = section_match.group(1)
                # Create filename from section number and title
                md_file_name = f"{section_num}-{section_title}.md"
            else:
                # No section number, just use the title
                md_file_name = f"{title_text}.md"
            
            # Clean up the generated filename
            md_file_name = clean_confluence_filename(md_file_name)
        else:
            # Normal case: use the original filename
            md_file_name = clean_confluence_filename(os.path.splitext(original_filename)[0] + '.md')
        
        # Determine folder structure based on section numbers
        folder_path, file_name, folder_depth = get_section_path(md_file_name, title_mapping, subsection_counts)
        
        # Process images and replace with placeholders
        soup, image_map = process_images_with_placeholders(soup, html_file_path, output_dir, rel_path, folder_depth)
        
        # Convert to Markdown
        h = setup_html2text()
        md_content = h.handle(str(soup))
        
        # Replace image placeholders with actual image HTML
        md_content = replace_image_placeholders(md_content, image_map)
        
        # Extract and restore markdown tables from pre blocks
        md_content = restore_markdown_tables(md_content)
        
        # Remove duplicate table separators first
        md_content = remove_duplicate_table_separators(md_content)
        
        # Fix table formatting issues (disabled - custom table conversion should handle this)
        # md_content = fix_markdown_tables(md_content)
        
        # Clean up the markdown
        md_content = clean_markdown(md_content)
        
        # Add title if found (after cleaning to avoid duplicate titles)
        if title:
            md_content = title + md_content
        
        # Create full output path
        if folder_path:
            md_dir = os.path.join(output_dir, folder_path)
        else:
            md_dir = os.path.join(output_dir, os.path.dirname(rel_path))
        
        os.makedirs(md_dir, exist_ok=True)
        md_file_path = os.path.join(md_dir, file_name)
        
        # Write Markdown content
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"Converted: {html_file_path} -> {md_file_path}")
        return True
    
    except Exception as e:
        print(f"Error converting {html_file_path}: {e}")
        return False

def extract_titles_from_html(html_file_path):
    """Extract the title from an HTML file."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                return title_tag.string.strip()
    except Exception as e:
        print(f"Error extracting title from {html_file_path}: {e}")
    return None

def process_directory(input_dir, output_dir):
    """Process all HTML files in the input directory and its subdirectories."""
    global removed_prefix
    input_path = Path(input_dir)
    
    # Create images directory in the output
    os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    
    # Track conversion stats
    stats = {'processed': 0, 'success': 0, 'failed': 0}
    
    # First pass: collect all titles to identify common prefixes
    all_titles = []
    for html_file in input_path.glob('**/*.html'):
        title = extract_titles_from_html(str(html_file))
        if title:
            all_titles.append(title)
    
    # Identify common prefix across titles
    global_prefix, prefix_count = find_common_title_prefix(all_titles)
    if global_prefix:
        removed_prefix = global_prefix
        print(f"Identified common title prefix: '{global_prefix}' (found in {prefix_count} of {len(all_titles)} titles)")
    
    # Second pass: build a mapping of section numbers to titles
    # and count how many files are in each subsection
    title_mapping = {}
    subsection_counts = {}
    section_files = {}
    
    for html_file in input_path.glob('**/*.html'):
        # Get the filename without extension
        basename = os.path.splitext(os.path.basename(html_file))[0]
        
        # Clean up the filename to get the section number and title
        cleaned_filename = clean_confluence_filename(basename + '.md')
        cleaned_basename = os.path.splitext(cleaned_filename)[0]
        
        # Check if this is a section file
        section_match = re.match(r'^(\d+(?:\.\d+)*)-(.+)$', cleaned_basename)
        if section_match:
            section_number = section_match.group(1)
            section_title = section_match.group(2)
            title_mapping[section_number] = section_title
            
            # Group files by section number for later processing
            if section_number not in section_files:
                section_files[section_number] = []
            section_files[section_number].append(html_file)
            
            # Count subsections
            parts = section_number.split('.')
            for i in range(len(parts)):
                # We need to count how many files are at each exact level
                # (e.g., how many files have section number exactly "4.2")
                level_section = '.'.join(parts[:i+1])
                subsection_counts[level_section] = subsection_counts.get(level_section, 0) + 1
    
    # Third pass: convert the files with title information and global prefix
    for html_file in input_path.glob('**/*.html'):
        stats['processed'] += 1
        
        # Get the relative path from the input directory
        rel_path = os.path.relpath(html_file.parent, input_dir)
        if rel_path == '.':
            rel_path = ''
        
        # Convert the file
        success = convert_html_to_markdown(str(html_file), output_dir, rel_path, 
                                          title_mapping, subsection_counts, global_prefix)
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Convert Confluence HTML export to Markdown')
    parser.add_argument('input_dir', help='Input directory containing Confluence HTML files')
    parser.add_argument('output_dir', help='Output directory for Markdown files')
    args = parser.parse_args()
    
    # Check if input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Converting Confluence HTML files from '{args.input_dir}' to Markdown in '{args.output_dir}'...")
    stats = process_directory(args.input_dir, args.output_dir)
    
    print("\nConversion complete!")
    print(f"Files processed: {stats['processed']}")
    print(f"Successful conversions: {stats['success']}")
    print(f"Failed conversions: {stats['failed']}")
    
    # Report removed prefix
    if removed_prefix:
        print(f"\nRemoved common title prefix: '{removed_prefix}'")

if __name__ == "__main__":
    main() 