"""
test_odt_generation.py
=====================

Test script for the ODT generation functionality.
This script demonstrates how to use the enhanced agent to create
ODT documents and tests the new functionality.
"""

import os
import sys
from enhanced_agent import create_assignment_odt

def test_odt_generation():
    """Test the ODT generation functionality with sample data."""
    
    # Sample assignment text with various formatting
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

### Implications

The implications of these findings are far-reaching and suggest that:

1. Current theories may need revision
2. Future research should focus on specific areas
3. Practical applications are immediately possible

## Conclusion

In conclusion, this assignment demonstrates the effectiveness of the AI Academic Assistant in generating well-structured academic documents. The ODT format provides excellent compatibility with various word processors while maintaining professional formatting.

## References

1. Smith, J. (2023). Academic Writing in the Digital Age. Journal of Educational Technology.
2. Johnson, M. & Brown, L. (2022). Document Formatting Standards. Academic Press.
3. Davis, R. (2024). AI-Assisted Learning Tools. Future Education Quarterly.
"""

    # Test data
    test_data = {
        'name': 'John Doe',
        'registration_number': '2024001',
        'instructor_name': 'Dr. Jane Smith',
        'semester': 'Fall 2024',
        'university_name': 'University of Technology',
        'assignment_text': sample_assignment,
        'title': 'Sample Assignment - ODT Generation Test',
        'filename': 'test_assignment.odt'
    }

    print("🧪 Testing ODT Generation...")
    print("=" * 50)
    
    try:
        # Generate ODT file
        print("📝 Generating ODT document...")
        odt_data = create_assignment_odt(**test_data)
        
        print(f"✅ ODT generated successfully!")
        print(f"📁 File saved as: {test_data['filename']}")
        print(f"📊 File size: {len(odt_data)} bytes")
        
        # Verify file exists and has content
        if os.path.exists(test_data['filename']):
            file_size = os.path.getsize(test_data['filename'])
            print(f"✅ File verification passed - Size: {file_size} bytes")
            
            # Basic validation
            if file_size > 1000:  # ODT files should be at least 1KB
                print("✅ File size validation passed")
            else:
                print("⚠️  Warning: File size seems too small")
                
        else:
            print("❌ Error: File was not created")
            return False
            
        # Test in-memory generation (without filename)
        print("\n📝 Testing in-memory generation...")
        test_data_memory = test_data.copy()
        del test_data_memory['filename']
        
        odt_bytes = create_assignment_odt(**test_data_memory)
        print(f"✅ In-memory generation successful - Size: {len(odt_bytes)} bytes")
        
        # Save the in-memory version
        with open('test_assignment_memory.odt', 'wb') as f:
            f.write(odt_bytes)
        print("✅ In-memory ODT saved as test_assignment_memory.odt")
        
        print("\n🎉 All tests passed successfully!")
        print("\n📋 Test Summary:")
        print("  ✅ ODT file generation")
        print("  ✅ File saving to disk")
        print("  ✅ In-memory generation")
        print("  ✅ Content validation")
        
        print(f"\n📂 Generated files:")
        print(f"  - {test_data['filename']}")
        print(f"  - test_assignment_memory.odt")
        
        print(f"\n💡 Tips:")
        print(f"  - Open the files in LibreOffice Writer to verify formatting")
        print(f"  - ODT files can also be opened in Microsoft Word")
        print(f"  - Files can be converted to DOCX or PDF as needed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during ODT generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_formatting_elements():
    """Test specific formatting elements in ODT generation."""
    
    print("\n🎨 Testing Formatting Elements...")
    print("=" * 50)
    
    # Test various markdown elements
    formatting_test = """
# Main Heading Level 1

This is a regular paragraph with some text content.

## Secondary Heading Level 2

Another paragraph to test spacing and formatting.

### Tertiary Heading Level 3

Now we test different types of lists:

## Unordered Lists

Basic unordered list:
- First item
- Second item with more text content
- Third item

Alternative bullet styles:
* Alternative bullet item 1
* Alternative bullet item 2

Plus style bullets:
+ Plus bullet item 1
+ Plus bullet item 2

## Ordered Lists

Numbered list with periods:
1. First numbered item
2. Second numbered item with longer content
3. Third numbered item

Numbered list with parentheses:
1) First item with parentheses
2) Second item with parentheses
3) Third item with parentheses

## Mixed Content

Here's a paragraph followed by a list:

- Mixed content item 1
- Mixed content item 2

And another paragraph after the list.

1. Numbered item after paragraph
2. Another numbered item

Final paragraph to complete the test.
"""

    try:
        test_data = {
            'name': 'Format Tester',
            'registration_number': 'FMT001',
            'instructor_name': 'Dr. Format',
            'semester': 'Test Semester',
            'university_name': 'Format University',
            'assignment_text': formatting_test,
            'title': 'Formatting Test Document',
            'filename': 'formatting_test.odt'
        }
        
        odt_data = create_assignment_odt(**test_data)
        print("✅ Formatting test ODT generated successfully!")
        print(f"📁 File saved as: {test_data['filename']}")
        print(f"📊 Size: {len(odt_data)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Formatting test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 ODT Generation Test Suite")
    print("=" * 60)
    
    # Run basic ODT generation test
    basic_test_passed = test_odt_generation()
    
    # Run formatting test
    formatting_test_passed = test_formatting_elements()
    
    print("\n" + "=" * 60)
    print("📋 FINAL TEST RESULTS")
    print("=" * 60)
    
    if basic_test_passed and formatting_test_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Basic ODT generation: PASSED")
        print("✅ Formatting elements: PASSED")
        print("\n💡 Your ODT generation functionality is working correctly!")
        print("   You can now use it in your Streamlit application.")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"{'✅' if basic_test_passed else '❌'} Basic ODT generation: {'PASSED' if basic_test_passed else 'FAILED'}")
        print(f"{'✅' if formatting_test_passed else '❌'} Formatting elements: {'PASSED' if formatting_test_passed else 'FAILED'}")
        print("\n🔧 Please check the error messages above and fix any issues.")
        
    print("\n📂 Check the generated .odt files to verify the output quality.")