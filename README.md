# 🎓 Enhanced AI Academic Assistant

An intelligent academic writing assistant that analyzes PDF documents and generates professional assignments in both **PDF** and **ODT** formats.

## ✨ New Features

### 📝 ODT Format Support
- **OpenDocument Text (.odt)** output for maximum compatibility
- Works with LibreOffice Writer, Microsoft Word, and Google Docs
- Fully editable documents with professional formatting
- Maintains proper heading hierarchy and list formatting

### 📄 Dual Format Output
- **PDF**: Perfect for final submission and printing
- **ODT**: Ideal for further editing and collaboration

## 🚀 Features

- **Document Analysis**: Intelligent analysis of uploaded PDF documents
- **Content Extraction**: Extracts key topics, instructions, and identifies ambiguities
- **Professional Formatting**: Clean, academic-style document generation
- **Customizable Cover Pages**: Include student details, instructor info, and university logos
- **Multiple Export Formats**: Generate both PDF and ODT versions
- **Interactive Web Interface**: User-friendly Streamlit application

## 📋 Requirements

- Python 3.8+
- OpenRouter API key
- Required packages (see `enhanced_requirements.txt`)

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r enhanced_requirements.txt
   ```

3. **Set up your OpenRouter API key:**
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```
   
   Or create a `.env` file:
   ```
   OPENROUTER_API_KEY=your-api-key-here
   ```

## 🚀 Quick Start

### Using the Streamlit Application

```bash
streamlit run enhanced_streamlit_app.py
```

Then:
1. 📤 Upload your PDF document
2. 📝 Add assignment instructions (optional)
3. 🔍 Review the document analysis
4. ✏️ Provide clarifications if needed
5. 📄 Generate your assignment
6. 💾 Download in PDF or ODT format

### Using the API Directly

```python
import enhanced_agent as agent

# Extract text from PDF
with open('document.pdf', 'rb') as f:
    pdf_data = f.read()
pdf_text = agent.extract_pdf_text(pdf_data)

# Run analysis
analysis = agent.run_analysis(pdf_text, "Your assignment instructions")
print(analysis)

# Generate assignment
assignment = agent.run_assignment(pdf_text, "Your instructions", "Clarifications")

# Create ODT file
odt_data = agent.create_assignment_odt(
    name="John Doe",
    registration_number="12345",
    instructor_name="Dr. Smith",
    semester="Fall 2024",
    university_name="University of Technology",
    assignment_text=assignment,
    title="My Assignment"
)

# Save ODT file
with open('assignment.odt', 'wb') as f:
    f.write(odt_data)

# Create PDF file (existing functionality)
pdf_data = agent.create_assignment_pdf(
    name="John Doe",
    registration_number="12345",
    instructor_name="Dr. Smith",
    semester="Fall 2024",
    university_name="University of Technology",
    assignment_text=assignment,
    title="My Assignment"
)

# Save PDF file
with open('assignment.pdf', 'wb') as f:
    f.write(pdf_data)
```

## 🧪 Testing

Test the ODT generation functionality:

```bash
python test_odt_generation.py
```

This will:
- Generate sample ODT files
- Test various formatting elements
- Verify file creation and content
- Provide validation results

## 📊 Format Comparison

| Feature | PDF | ODT |
|---------|-----|-----|
| **Fixed Layout** | ✅ Yes | ❌ No |
| **Editable** | ❌ Limited | ✅ Full |
| **Print Quality** | ✅ Excellent | ✅ Good |
| **Collaboration** | ❌ Limited | ✅ Excellent |
| **Logo Support** | ✅ Yes | ❌ Not yet |
| **File Size** | 📊 Larger | 📊 Smaller |
| **Compatibility** | 🌐 Universal | 🌐 Word Processors |

## 📁 Project Structure

```
enhanced-ai-assistant/
├── enhanced_agent.py              # Core agent with ODT support
├── enhanced_streamlit_app.py      # Enhanced Streamlit interface
├── enhanced_requirements.txt      # Updated dependencies
├── test_odt_generation.py        # ODT testing script
├── README.md                     # This file
├── original_files/               # Your original files
│   ├── agentz.py
│   ├── streamlit_app.py
│   ├── assignment_template.html
│   ├── requirements.txt
│   └── other_files...
└── examples/                     # Sample generated files
    ├── sample_assignment.odt
    └── sample_assignment.pdf
```

## 🔧 Configuration

### OpenRouter Models

The system uses OpenRouter API with these default settings:
- **Model**: `z-ai/glm-4.5-air:free` (can be changed)
- **Temperature**: 0.0 (deterministic output)

You can modify the model in the function calls:

```python
analysis = agent.run_analysis(
    pdf_text, 
    questions, 
    model_name="anthropic/claude-3-sonnet",
    temperature=0.1
)
```

### Supported Models
- `z-ai/glm-4.5-air:free` (default, free tier)
- `openai/gpt-3.5-turbo`
- `openai/gpt-4`
- `anthropic/claude-3-sonnet`
- And many more on OpenRouter

## 🎨 Formatting Features

### ODT Format Support
- **Headings**: H1, H2, H3 with proper styling
- **Paragraphs**: Justified text with appropriate spacing
- **Lists**: Both bulleted and numbered lists
- **Cover Page**: Professional layout with student information
- **Styles**: Academic formatting with Times New Roman font

### PDF Format Support (Existing)
- Professional cover page with optional logo
- Proper margins and spacing
- Page numbers
- Academic formatting
- Fixed layout for consistent appearance

## 🐛 Troubleshooting

### Common Issues

1. **ODT files won't open**
   - Ensure the file has `.odt` extension
   - Try opening with LibreOffice Writer first
   - Check file size (should be > 1KB)

2. **Missing dependencies**
   ```bash
   pip install --upgrade -r enhanced_requirements.txt
   ```

3. **OpenRouter API issues**
   - Verify your API key is set correctly
   - Check your OpenRouter account quota
   - Try a different model

4. **Formatting issues in ODT**
   - ODT formatting may vary between applications
   - LibreOffice Writer provides the best compatibility
   - Consider converting to DOCX if needed

## 🔄 Migration from Original

If you're upgrading from the original version:

1. **Backup your original files**
2. **Replace the agent module**: Use `enhanced_agent.py` instead of `agentz.py`
3. **Update Streamlit app**: Use `enhanced_streamlit_app.py`
4. **Install new dependencies**: `pip install -r enhanced_requirements.txt`
5. **Test ODT functionality**: Run `python test_odt_generation.py`

## 🤝 Contributing

To add more features:

1. **Add new export formats** in `enhanced_agent.py`
2. **Enhance UI** in `enhanced_streamlit_app.py`
3. **Add tests** in `test_odt_generation.py`
4. **Update documentation** in this README

## 📄 License

This enhanced version maintains compatibility with your original code while adding ODT functionality. Feel free to modify and distribute according to your needs.

## 🙋 Support

For issues or questions:
1. Check the troubleshooting section above
2. Run the test script to verify functionality
3. Check the generated files to ensure quality
4. Review the console output for error messages

## 🎯 Future Enhancements

Planned features:
- **DOCX format support**
- **Logo support in ODT files**
- **Advanced styling options**
- **Template customization**
- **Batch processing**
- **Cloud storage integration**

---

**🎉 Enjoy your enhanced AI Academic Assistant with dual-format support!**