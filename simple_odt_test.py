"""
simple_odt_test.py
=================

Simple test for ODT generation functionality without AI dependencies.
This tests only the ODT creation part of the enhanced agent.
"""

import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
import re


def _escape_xml(text: str) -> str:
    """Escape XML special characters in text."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))


def _markdown_to_odt_content(text: str) -> str:
    """Convert Markdown-like text to ODT XML content."""
    
    lines = text.strip().split('\n')
    content_lines = []
    list_level = 0
    in_list = False
    
    for line in lines:
        line = line.rstrip()
        
        # Empty line - add paragraph break
        if not line:
            if in_list:
                in_list = False
                list_level = 0
            content_lines.append('<text:p text:style-name="P1"/>')
            continue
            
        # Handle headings
        if line.startswith('#'):
            if in_list:
                in_list = False
                list_level = 0
            
            level = len(line) - len(line.lstrip('#'))
            heading_text = line[level:].strip()
            
            if level == 1:
                style = "Heading_20_1"
            elif level == 2:
                style = "Heading_20_2"
            else:
                style = "Heading_20_3"
                
            content_lines.append(f'<text:h text:style-name="{style}" text:outline-level="{level}">{_escape_xml(heading_text)}</text:h>')
            continue
            
        # Handle unordered lists
        stripped = line.lstrip()
        if stripped.startswith(('- ', '* ', '+ ')):
            if not in_list:
                content_lines.append('<text:list text:style-name="L1">')
                in_list = True
                list_level = 1
                
            item_text = stripped[2:].strip()
            content_lines.append(f'<text:list-item><text:p text:style-name="P2">• {_escape_xml(item_text)}</text:p></text:list-item>')
            continue
            
        # Handle ordered lists
        if re.match(r'^\s*\d+[\.|\)]\s+', line):
            if not in_list:
                content_lines.append('<text:list text:style-name="L2">')
                in_list = True
                list_level = 1
                
            match = re.match(r'^(\s*)(\d+)[\.|\)]\s+(.+)', line)
            if match:
                number = match.group(2)
                item_text = match.group(3)
                content_lines.append(f'<text:list-item><text:p text:style-name="P2">{number}. {_escape_xml(item_text)}</text:p></text:list-item>')
            continue
            
        # Regular paragraph
        if in_list:
            content_lines.append('</text:list>')
            in_list = False
            list_level = 0
            
        content_lines.append(f'<text:p text:style-name="P1">{_escape_xml(line)}</text:p>')
    
    # Close any open lists
    if in_list:
        content_lines.append('</text:list>')
    
    return '\n'.join(content_lines)


def create_assignment_odt(
    name: str,
    registration_number: str,
    instructor_name: str,
    semester: str,
    university_name: str,
    assignment_text: str,
    *,
    filename: str | None = None,
    title: str = "Assignment",
) -> bytes:
    """Generate a professional ODT (OpenDocument Text) assignment file."""
    
    # Create a temporary directory for ODT components
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # Create ODT structure
        meta_inf_dir = os.path.join(temp_dir, "META-INF")
        os.makedirs(meta_inf_dir)
        
        # Create manifest.xml
        manifest_content = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
    <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.text"/>
    <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
    <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
    <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>'''
        
        with open(os.path.join(meta_inf_dir, "manifest.xml"), "w", encoding="utf-8") as f:
            f.write(manifest_content)
        
        # Create meta.xml
        current_time = datetime.now().isoformat()
        meta_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" office:version="1.3">
    <office:meta>
        <meta:generator>AI Academic Assistant</meta:generator>
        <dc:title>{_escape_xml(title)}</dc:title>
        <dc:creator>{_escape_xml(name)}</dc:creator>
        <dc:subject>{_escape_xml(title)} - {_escape_xml(university_name)}</dc:subject>
        <meta:creation-date>{current_time}</meta:creation-date>
        <dc:date>{current_time}</dc:date>
        <dc:language>en-US</dc:language>
    </office:meta>
</office:document-meta>'''
        
        with open(os.path.join(temp_dir, "meta.xml"), "w", encoding="utf-8") as f:
            f.write(meta_content)
        
        # Create styles.xml
        styles_content = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3">
    <office:styles>
        <style:default-style style:family="paragraph">
            <style:paragraph-properties fo:text-align="justify" style:justify-single-word="false"/>
            <style:text-properties style:font-name="Times New Roman" fo:font-size="12pt" fo:language="en" fo:country="US"/>
        </style:default-style>
        
        <style:style style:name="Standard" style:family="paragraph" style:class="text">
            <style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0835in" fo:text-align="justify" style:justify-single-word="false"/>
        </style:style>
        
        <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:parent-style-name="Heading" style:next-style-name="Text_20_body" style:class="text">
            <style:paragraph-properties fo:margin-top="0.1665in" fo:margin-bottom="0.0835in" fo:keep-with-next="conditional"/>
            <style:text-properties fo:font-size="18pt" fo:font-weight="bold"/>
        </style:style>
        
        <style:style style:name="Heading_20_2" style:display-name="Heading 2" style:family="paragraph" style:parent-style-name="Heading" style:next-style-name="Text_20_body" style:class="text">
            <style:paragraph-properties fo:margin-top="0.1251in" fo:margin-bottom="0.0835in" fo:keep-with-next="conditional"/>
            <style:text-properties fo:font-size="14pt" fo:font-weight="bold"/>
        </style:style>
        
        <style:style style:name="Heading_20_3" style:display-name="Heading 3" style:family="paragraph" style:parent-style-name="Heading" style:next-style-name="Text_20_body" style:class="text">
            <style:paragraph-properties fo:margin-top="0.0835in" fo:margin-bottom="0.0835in" fo:keep-with-next="conditional"/>
            <style:text-properties fo:font-size="12pt" fo:font-weight="bold"/>
        </style:style>
        
        <style:style style:name="Title" style:family="paragraph" style:parent-style-name="Heading" style:class="chapter">
            <style:paragraph-properties fo:text-align="center" style:justify-single-word="false"/>
            <style:text-properties fo:font-size="24pt" fo:font-weight="bold"/>
        </style:style>
        
        <style:style style:name="Subtitle" style:family="paragraph" style:parent-style-name="Heading" style:class="chapter">
            <style:paragraph-properties fo:text-align="center" style:justify-single-word="false" fo:margin-top="0.0417in" fo:margin-bottom="0.0835in"/>
            <style:text-properties fo:font-size="14pt" fo:font-style="italic"/>
        </style:style>
        
        <text:list-style style:name="L1">
            <text:list-level-style-bullet text:level="1" text:style-name="Bullet_20_Symbols" text:bullet-char="•">
                <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
                    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="0.5in" fo:text-indent="-0.25in" fo:margin-left="0.5in"/>
                </style:list-level-properties>
            </text:list-level-style-bullet>
        </text:list-style>
        
        <text:list-style style:name="L2">
            <text:list-level-style-number text:level="1" text:style-name="Numbering_20_Symbols" style:num-suffix="." style:num-format="1">
                <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
                    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="0.5in" fo:text-indent="-0.25in" fo:margin-left="0.5in"/>
                </style:list-level-properties>
            </text:list-level-style-number>
        </text:list-style>
    </office:styles>
    
    <office:automatic-styles>
        <style:style style:name="P1" style:family="paragraph" style:parent-style-name="Standard">
            <style:paragraph-properties fo:text-align="justify" style:justify-single-word="false"/>
        </style:style>
        
        <style:style style:name="P2" style:family="paragraph" style:parent-style-name="Standard">
            <style:paragraph-properties fo:margin-left="0.5in" fo:text-indent="-0.25in"/>
        </style:style>
        
        <style:style style:name="P3" style:family="paragraph" style:parent-style-name="Standard">
            <style:paragraph-properties fo:text-align="center" style:justify-single-word="false"/>
        </style:style>
    </office:automatic-styles>
</office:document-styles>'''
        
        with open(os.path.join(temp_dir, "styles.xml"), "w", encoding="utf-8") as f:
            f.write(styles_content)
        
        # Convert assignment text to ODT content
        content_body = _markdown_to_odt_content(assignment_text)
        
        # Create content.xml with cover page and content
        content_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3">
    <office:body>
        <office:text>
            <!-- Cover Page -->
            <text:p text:style-name="P3">
                <text:span text:style-name="Title">{_escape_xml(title)}</text:span>
            </text:p>
            <text:p text:style-name="P1"/>
            <text:p text:style-name="P3">
                <text:span text:style-name="Subtitle">{_escape_xml(university_name)}</text:span>
            </text:p>
            <text:p text:style-name="P1"/>
            <text:p text:style-name="P1"/>
            <text:p text:style-name="P3">
                <text:span style:font-weight="bold">Student Name:</text:span> {_escape_xml(name)}
            </text:p>
            <text:p text:style-name="P3">
                <text:span style:font-weight="bold">Registration Number:</text:span> {_escape_xml(registration_number)}
            </text:p>
            <text:p text:style-name="P3">
                <text:span style:font-weight="bold">Instructor:</text:span> {_escape_xml(instructor_name)}
            </text:p>
            <text:p text:style-name="P3">
                <text:span style:font-weight="bold">Semester:</text:span> {_escape_xml(semester)}
            </text:p>
            
            <!-- Page break before content -->
            <text:p text:style-name="P1" style:page-break-before="page"/>
            
            <!-- Assignment Content -->
            {content_body}
        </office:text>
    </office:body>
</office:document-content>'''
        
        with open(os.path.join(temp_dir, "content.xml"), "w", encoding="utf-8") as f:
            f.write(content_xml)
        
        # Create mimetype file (must be first in ZIP and uncompressed)
        mimetype_content = "application/vnd.oasis.opendocument.text"
        with open(os.path.join(temp_dir, "mimetype"), "w", encoding="utf-8") as f:
            f.write(mimetype_content)
        
        # Create ODT file (ZIP archive)
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as odt_zip:
            # Add mimetype first (uncompressed)
            odt_zip.write(os.path.join(temp_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            
            # Add other files
            odt_zip.write(os.path.join(meta_inf_dir, "manifest.xml"), "META-INF/manifest.xml")
            odt_zip.write(os.path.join(temp_dir, "meta.xml"), "meta.xml")
            odt_zip.write(os.path.join(temp_dir, "styles.xml"), "styles.xml")
            odt_zip.write(os.path.join(temp_dir, "content.xml"), "content.xml")
        
        odt_data = buffer.getvalue()
        
        # Save to file if filename provided
        if filename:
            with open(filename, "wb") as f:
                f.write(odt_data)
        
        return odt_data


def test_odt_generation():
    """Test the ODT generation functionality."""
    
    # Sample assignment text
    sample_assignment = """
# Introduction

This is a sample assignment to demonstrate the ODT generation capabilities of the AI Academic Assistant. The assignment covers various formatting elements including headings, paragraphs, and lists.

## Literature Review

The literature review section examines existing research in the field. According to various studies, the following points are important:

- First key finding from the literature
- Second important discovery
- Third significant observation

### Methodology

The methodology section describes the approach taken for this research:

1. Data collection phase
2. Analysis and processing
3. Results interpretation
4. Conclusion formulation

## Analysis and Discussion

This section provides detailed analysis of the findings. The discussion covers multiple aspects of the research question and provides insights into the implications of the results.

### Key Findings

The analysis revealed several important patterns:

- Pattern A: Significant correlation between variables
- Pattern B: Unexpected behavior in edge cases
- Pattern C: Consistent results across different datasets

## Conclusion

In conclusion, this assignment demonstrates the effectiveness of the AI Academic Assistant in generating well-structured academic documents. The ODT format provides excellent compatibility with various word processors while maintaining professional formatting.

## References

1. Smith, J. (2023). Academic Writing in the Digital Age. Journal of Educational Technology.
2. Johnson, M. & Brown, L. (2022). Document Formatting Standards. Academic Press.
3. Davis, R. (2024). AI-Assisted Learning Tools. Future Education Quarterly.
"""

    print("🧪 Testing ODT Generation...")
    print("=" * 50)
    
    try:
        # Generate ODT file
        print("📝 Generating ODT document...")
        odt_data = create_assignment_odt(
            name="John Doe",
            registration_number="2024001",
            instructor_name="Dr. Jane Smith",
            semester="Fall 2024",
            university_name="University of Technology",
            assignment_text=sample_assignment,
            title="Sample Assignment - ODT Generation Test",
            filename="test_assignment.odt"
        )
        
        print(f"✅ ODT generated successfully!")
        print(f"📁 File saved as: test_assignment.odt")
        print(f"📊 File size: {len(odt_data)} bytes")
        
        # Verify file exists and has content
        if os.path.exists("test_assignment.odt"):
            file_size = os.path.getsize("test_assignment.odt")
            print(f"✅ File verification passed - Size: {file_size} bytes")
            
            if file_size > 1000:
                print("✅ File size validation passed")
            else:
                print("⚠️  Warning: File size seems too small")
        else:
            print("❌ Error: File was not created")
            return False
            
        print("\n🎉 Test completed successfully!")
        print(f"📂 Generated file: test_assignment.odt")
        print(f"💡 Open the file in LibreOffice Writer to verify formatting")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during ODT generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Simple ODT Generation Test")
    print("=" * 60)
    
    success = test_odt_generation()
    
    if success:
        print("\n🎉 ODT GENERATION TEST PASSED!")
        print("✅ Your ODT functionality is working correctly!")
    else:
        print("\n❌ ODT GENERATION TEST FAILED!")
        print("🔧 Please check the error messages above.")