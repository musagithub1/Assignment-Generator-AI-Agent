# 🚀 Installation Guide - Enhanced AI Academic Assistant

## 📋 Quick Setup Instructions

### 1. **Download and Extract**
- Extract the downloaded ZIP file to your desired directory
- Navigate to the `enhanced_ai_assistant` folder

### 2. **Install Python Requirements**
```bash
pip install -r enhanced_requirements.txt
```

### 3. **Set Up OpenRouter API Key**

**Option A: Environment Variable**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

**Option B: Create .env file**
Create a file named `.env` in the project directory:
```
OPENROUTER_API_KEY=your-api-key-here
```

### 4. **Test ODT Functionality**
```bash
python simple_odt_test.py
```

### 5. **Run the Application**
```bash
streamlit run enhanced_streamlit_app.py
```

## 🔧 Troubleshooting

### Missing Dependencies
If you get import errors, install missing packages:
```bash
pip install streamlit langchain langchain-openai langgraph PyPDF2 matplotlib Pillow lxml
```

### OpenRouter API Issues
1. Sign up at [OpenRouter.ai](https://openrouter.ai/)
2. Get your API key from the dashboard
3. Make sure you have credits/quota available

### ODT Files Won't Open
1. Try opening with LibreOffice Writer first
2. If you only have Microsoft Word, it should still work
3. The files can be converted to DOCX if needed

## 📊 What You Get

- **enhanced_agent.py**: Core AI agent with ODT support
- **enhanced_streamlit_app.py**: Web interface with dual format support
- **simple_odt_test.py**: Standalone ODT testing (no AI required)
- **examples/sample_assignment.odt**: Example generated ODT file
- **README.md**: Comprehensive documentation

## 🎯 Next Steps

1. **Test the ODT generation**: Run `simple_odt_test.py`
2. **Start the web app**: Run `streamlit run enhanced_streamlit_app.py`
3. **Upload a PDF**: Try the full workflow
4. **Generate both formats**: Download PDF and ODT versions

## 💡 Tips

- Keep your original files in the `original_files` folder for backup
- The ODT files work best with LibreOffice Writer
- You can convert ODT files to DOCX, PDF, or other formats as needed
- The system supports both free and paid OpenRouter models

**🎉 You're ready to go! Enjoy your enhanced AI Academic Assistant!**