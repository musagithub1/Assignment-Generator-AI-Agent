"""
enhanced_streamlit_app.py
=========================

Enhanced Streamlit application with ODT support for the AI academic assistant.
This version adds OpenDocument Text (.odt) format generation alongside the
existing PDF functionality, providing better compatibility with LibreOffice
Writer and Microsoft Word.

Users can upload a PDF, provide assignment instructions, and generate both
PDF and ODT versions of their academic assignments with professional formatting.

Before running this application, ensure you have set the
`OPENROUTER_API_KEY` environment variable to your personal API key and
installed all dependencies listed in `requirements.txt`.
"""

from __future__ import annotations

import streamlit as st
import os
import tempfile

import enhanced_agent as agent  # Import our enhanced agent module


def main() -> None:
    """Main entry point for the enhanced Streamlit app."""
    st.set_page_config(page_title="AI Academic Assistant", layout="wide")
    st.title("🎓 AI Academic Assistant – Assignment Generator")
    st.markdown("### Generate professional assignments in PDF and ODT formats")

    st.write(
        """
        Upload a PDF document and optionally provide assignment questions or instructions.
        The assistant will analyse the document to extract key topics and any
        ambiguities, then generate a high‑quality assignment based on the
        content. You can download your assignment in both **PDF** and **ODT** formats
        for maximum compatibility with different word processors.
        
        **📄 PDF Format**: Perfect for submission and printing with fixed formatting  
        **📝 ODT Format**: Ideal for further editing in LibreOffice Writer, Microsoft Word, or Google Docs
        """
    )

    # Initialise session state variables on first load
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None
    if "pdf_text" not in st.session_state:
        st.session_state["pdf_text"] = None

    # Create two columns for better layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader for PDFs
        uploaded_file = st.file_uploader(
            "📎 Upload a PDF document", 
            type=["pdf"], 
            accept_multiple_files=False,
            help="Select a PDF file containing the source material for your assignment"
        )
        
        questions = st.text_area(
            "📝 Assignment questions or instructions (optional)",
            value="",
            height=150,
            help="Provide specific instructions, questions, or requirements for the assignment"
        )

    with col2:
        st.info(
            "**How it works:**\n\n"
            "1. 📤 Upload your PDF document\n"
            "2. 🔍 Review the analysis\n"
            "3. ✏️ Add clarifications if needed\n"
            "4. 📄 Generate your assignment\n"
            "5. 💾 Download in PDF or ODT format"
        )

    if uploaded_file is not None:
        # Extract text only when a new file is uploaded
        if st.session_state.get("uploaded_filename") != uploaded_file.name:
            with st.spinner("📖 Extracting text from PDF..."):
                pdf_bytes = uploaded_file.getvalue()
                pdf_text = agent.extract_pdf_text(pdf_bytes)
                st.session_state["pdf_text"] = pdf_text
                st.session_state["analysis_result"] = None
                st.session_state["uploaded_filename"] = uploaded_file.name
                st.success(f"✅ Successfully loaded: {uploaded_file.name}")

        # Analysis section
        st.markdown("---")
        st.subheader("🔍 Document Analysis")
        
        # Analysis button
        if st.button("🚀 Analyse Document", type="primary"):
            with st.spinner("🔍 Analysing document content and structure..."):
                analysis = agent.run_analysis(
                    st.session_state["pdf_text"] or "",
                    questions,
                )
                st.session_state["analysis_result"] = analysis
                st.success("✅ Analysis completed!")

    # Display analysis results if available
    if st.session_state.get("analysis_result"):
        st.markdown("### 📊 Analysis Results")
        with st.expander("View Analysis Details", expanded=True):
            st.markdown(st.session_state["analysis_result"])
        
        st.markdown("---")
        st.subheader("✏️ Clarifications")
        st.write(
            """
            Based on the analysis above, please provide any clarifications or
            additional instructions necessary to resolve ambiguities. If no
            clarifications are needed, you can leave this field blank.
            """
        )
        
        clarifications = st.text_area(
            "Additional clarifications (optional)", 
            value="", 
            height=100,
            help="Add any specific clarifications or additional requirements"
        )

        # Assignment generation
        st.markdown("---")
        if st.button("📝 Generate Assignment", type="primary"):
            """
            When the user requests to generate the assignment, run the
            underlying model and persist the result in the session state.
            Storing the assignment in `st.session_state` ensures that it
            persists across reruns triggered by subsequent user input.
            """
            with st.spinner("🤖 Generating your assignment..."):
                assignment = agent.run_assignment(
                    st.session_state["pdf_text"] or "",
                    questions,
                    clarifications,
                )
                # Persist the generated assignment so it survives re-runs
                st.session_state["generated_assignment"] = assignment
                st.success("🎉 Assignment generated successfully!")

        # If we've already generated an assignment, display it and allow file export
        if st.session_state.get("generated_assignment"):
            assignment = st.session_state["generated_assignment"]
            
            st.markdown("---")
            st.subheader("📄 Generated Assignment")
            
            # Show a preview of the assignment
            with st.expander("📖 Preview Assignment Content", expanded=False):
                st.markdown(assignment)

            # ------------------------------------------------------------------
            # Enhanced export options with both PDF and ODT
            # ------------------------------------------------------------------
            st.markdown("### 💾 Download Options")
            st.write("Choose your preferred format and customize the document details:")
            
            # Create tabs for different export formats
            tab_pdf, tab_odt = st.tabs(["📄 PDF Format", "📝 ODT Format"])
            
            with tab_pdf:
                st.write("**Perfect for:** Final submission, printing, fixed formatting")
                with st.form(key="pdf_form"):
                    st.markdown("#### Document Information")
                    col1, col2 = st.columns(2)
                    with col1:
                        student_name = st.text_input("👤 Student Name", value="", placeholder="Enter your full name")
                        reg_no = st.text_input("🆔 Registration Number", value="", placeholder="Student ID or registration number")
                        instructor_name = st.text_input("👨‍🏫 Instructor Name", value="", placeholder="Course instructor's name")
                    with col2:
                        semester = st.text_input("📅 Semester", value="", placeholder="e.g., Fall 2024")
                        university = st.text_input("🏫 University Name", value="", placeholder="Your institution's name")
                        assignment_title = st.text_input("📋 Assignment Title", value="Assignment", placeholder="Title for the assignment")
                    
                    # Allow optional logo upload (PNG/JPG)
                    logo_file = st.file_uploader(
                        "🖼️ University/Institute Logo (optional)",
                        type=["png", "jpg", "jpeg"],
                        accept_multiple_files=False,
                        key="logo_uploader",
                        help="Upload your institution's logo to include on the cover page"
                    )
                    
                    submit_pdf = st.form_submit_button("📄 Generate PDF", type="primary")
                
                # Handle PDF generation after the form is submitted
                if submit_pdf:
                    logo_path = None
                    if logo_file is not None:
                        tmp_dir = tempfile.mkdtemp()
                        logo_path = os.path.join(tmp_dir, logo_file.name)
                        with open(logo_path, "wb") as out_file:
                            out_file.write(logo_file.getvalue())
                    
                    with st.spinner("📄 Creating PDF document..."):
                        try:
                            pdf_bytes = agent.create_assignment_pdf(
                                name=student_name or "Student Name",
                                registration_number=reg_no or "N/A",
                                instructor_name=instructor_name or "Instructor",
                                semester=semester or "N/A",
                                university_name=university or "University",
                                assignment_text=assignment,
                                title=assignment_title or "Assignment",
                                logo_path=logo_path,
                            )
                            
                            st.success("✅ PDF generated successfully!")
                            st.download_button(
                                label="📥 Download PDF", 
                                data=pdf_bytes,
                                file_name=f"{assignment_title or 'assignment'}.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"❌ Error generating PDF: {str(e)}")
            
            with tab_odt:
                st.write("**Perfect for:** Further editing, collaboration, document sharing")
                with st.form(key="odt_form"):
                    st.markdown("#### Document Information")
                    col1, col2 = st.columns(2)
                    with col1:
                        odt_student_name = st.text_input("👤 Student Name", value="", placeholder="Enter your full name", key="odt_name")
                        odt_reg_no = st.text_input("🆔 Registration Number", value="", placeholder="Student ID or registration number", key="odt_reg")
                        odt_instructor_name = st.text_input("👨‍🏫 Instructor Name", value="", placeholder="Course instructor's name", key="odt_instructor")
                    with col2:
                        odt_semester = st.text_input("📅 Semester", value="", placeholder="e.g., Fall 2024", key="odt_semester")
                        odt_university = st.text_input("🏫 University Name", value="", placeholder="Your institution's name", key="odt_university")
                        odt_assignment_title = st.text_input("📋 Assignment Title", value="Assignment", placeholder="Title for the assignment", key="odt_title")
                    
                    submit_odt = st.form_submit_button("📝 Generate ODT", type="primary")
                
                # Handle ODT generation after the form is submitted
                if submit_odt:
                    with st.spinner("📝 Creating ODT document..."):
                        try:
                            odt_bytes = agent.create_assignment_odt(
                                name=odt_student_name or "Student Name",
                                registration_number=odt_reg_no or "N/A",
                                instructor_name=odt_instructor_name or "Instructor",
                                semester=odt_semester or "N/A",
                                university_name=odt_university or "University",
                                assignment_text=assignment,
                                title=odt_assignment_title or "Assignment",
                            )
                            
                            st.success("✅ ODT generated successfully!")
                            st.download_button(
                                label="📥 Download ODT", 
                                data=odt_bytes,
                                file_name=f"{odt_assignment_title or 'assignment'}.odt",
                                mime="application/vnd.oasis.opendocument.text",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"❌ Error generating ODT: {str(e)}")
            
            # Format comparison info
            st.markdown("---")
            st.markdown("### 📊 Format Comparison")
            
            comparison_col1, comparison_col2 = st.columns(2)
            with comparison_col1:
                st.markdown("""
                **📄 PDF Format**
                - ✅ Fixed formatting and layout
                - ✅ Ideal for final submission
                - ✅ Consistent appearance across platforms
                - ✅ Includes university logo support
                - ✅ Professional print output
                - ❌ Limited editing capabilities
                """)
            
            with comparison_col2:
                st.markdown("""
                **📝 ODT Format**
                - ✅ Fully editable in word processors
                - ✅ Compatible with LibreOffice, MS Word, Google Docs
                - ✅ Collaborative editing friendly
                - ✅ Can be converted to other formats
                - ✅ Professional styling maintained
                - ❌ Layout may vary between applications
                """)

    elif uploaded_file is None:
        st.info("📤 Please upload a PDF document to begin the analysis process.")


if __name__ == "__main__":
    main()