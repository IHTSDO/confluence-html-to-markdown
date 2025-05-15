#!/usr/bin/env python3
"""
Confluence HTML to Markdown Directory Converter

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

def setup_html2text():
    """Configure html2text with appropriate settings."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True  # Tell html2text to ignore image tags, we'll handle them manually
    h.ignore_emphasis = False
    h.ignore_tables = False
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
        
        # Check if this line contains an image placeholder
        placeholder_match = None
        for placeholder in image_map.keys():
            if placeholder in line:
                placeholder_match = placeholder
                break
        
        if placeholder_match:
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
                
                # Convert _text_ or *text* to <em>text</em>
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
            
            # Replace the placeholder line with the figure
            lines[i] = lines[i].replace(placeholder_match, figure_html)
        
        i += 1
    
    # Join lines back into content
    processed_content = '\n'.join(lines)
    
    # Make sure no dashes are added after the image replacement
    # This prevents the "---" horizontal rule after images
    processed_content = re.sub(r'<figure>.*?</figure>\n---', lambda m: m.group(0).replace('\n---', ''), processed_content, flags=re.DOTALL)
    processed_content = re.sub(r'<figure>.*?</figure>\n----', lambda m: m.group(0).replace('\n----', ''), processed_content, flags=re.DOTALL)
    
    return processed_content

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
        
        # Confluence specific classes
        '.confluence-information-macro', '.contentLayout2', '.columnLayout', '.aui-buttons',
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
    
    # Special handling for section numbering
    # Identify if the filename starts with a section number pattern like 1, 2.1, 3.4.5, etc.
    section_match = re.match(r'^(\d+(?:\.\d+)*)-', cleaned)
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

def clean_title(title_text):
    """
    Clean up the title by removing repeated site titles and Confluence suffix.
    Examples:
    - "SNOMED CT Starter Guide : 5. SNOMED CT Logical Model" -> "5. SNOMED CT Logical Model"
    - "Data Analytics with SNOMED CT : Introduction to Data Analytics" -> "Introduction to Data Analytics"
    - "Site Title - Page Title - Confluence" -> "Page Title"
    """
    # First remove Confluence suffix
    title_text = re.sub(r'\s*-\s*Confluence.*$', '', title_text.strip())
    
    # Define common site title prefixes to remove (exact matches)
    common_prefixes = [
        "SNOMED CT Starter Guide", 
        "SNOMED CT Starter Guide :",
        "SNOMED CT Starter Guide:",
        "Data Analytics with SNOMED CT :",
        "Data Analytics with SNOMED CT",
        "Data Analytics with SNOMED CT:"
    ]
    
    # Check for exact prefix matches
    for prefix in common_prefixes:
        if title_text.startswith(prefix):
            cleaned_title = title_text[len(prefix):].strip()
            # Remove any leading colon or dash with spaces
            cleaned_title = re.sub(r'^[\s:|-]+', '', cleaned_title)
            return cleaned_title
    
    # For other patterns, look for common separators
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
        if re.search(r'(guide|docs|documentation|manual|handbook|analytics)$', site_title.lower()):
            return page_title.strip()
    
    return title_text

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

def convert_html_to_markdown(html_file_path, output_dir, rel_path, title_mapping=None, subsection_counts=None):
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
            # Clean the title text
            title_text = clean_title(title_tag.string)
            title = f"# {title_text}\n\n"
        
        # Clean Confluence-specific elements
        soup = clean_confluence_html(soup)
        
        # Determine output path and folder depth before processing images
        original_filename = os.path.basename(html_file_path)
        
        # Check if filename is just a numeric ID
        is_numeric_id = re.match(r'^\d+\.html$', original_filename) is not None
        
        # For numeric-only filenames, use the title instead
        if is_numeric_id and title_text:
            # Extract section number if present
            section_match = re.search(r'(\d+(?:\.\d+)*)\s+(.+)', title_text)
            if section_match:
                section_num = section_match.group(1)
                section_title = section_match.group(2)
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

def process_directory(input_dir, output_dir):
    """Process all HTML files in the input directory and its subdirectories."""
    input_path = Path(input_dir)
    
    # Create images directory in the output
    os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    
    # Track conversion stats
    stats = {'processed': 0, 'success': 0, 'failed': 0}
    
    # First pass: build a mapping of section numbers to titles
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
    
    # Second pass: convert the files with title information
    for html_file in input_path.glob('**/*.html'):
        stats['processed'] += 1
        
        # Get the relative path from the input directory
        rel_path = os.path.relpath(html_file.parent, input_dir)
        if rel_path == '.':
            rel_path = ''
        
        # Convert the file
        success = convert_html_to_markdown(str(html_file), output_dir, rel_path, title_mapping, subsection_counts)
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

if __name__ == "__main__":
    main() 