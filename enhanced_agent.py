"""
enhanced_agent.py
===============

Enhanced version of the AI academic assistant with ODT (OpenDocument Text) support.
This module adds ODT generation functionality while maintaining all existing PDF features.
The ODT format provides better compatibility with LibreOffice Writer and Microsoft Word.

This module defines the core logic for the AI academic assistant.  It uses
LangChain, LangGraph and the OpenRouter API (via a custom `ChatOpenRouter`
class) to analyse uploaded documents and generate structured academic
assignments.  The module exposes helper functions for extracting text from
PDFs as well as high‑level functions for running an analysis pass and
for generating a complete assignment in both PDF and ODT formats.

To run this code you must set the environment variable `OPENROUTER_API_KEY`
to your personal OpenRouter API key.  See the README for more details.
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import Dict, Any, Optional, TypedDict
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
import re

from pydantic import Field, SecretStr

from langchain_openai import ChatOpenAI
from langchain_core.utils.utils import secret_from_env
from langgraph.graph import StateGraph

try:
    # PyPDF2 is used for extracting text from PDFs.  If it isn't installed
    # streamlit will inform the user via dependency resolution in
    # requirements.txt.
    from PyPDF2 import PdfReader
except ImportError as e:
    raise ImportError(
        "PyPDF2 is required for PDF parsing. Please install it via 'pip install PyPDF2'."
    ) from e


class ChatOpenRouter(ChatOpenAI):
    """A thin wrapper around LangChain's ChatOpenAI class to target the
    OpenRouter endpoint instead of the default OpenAI API.  It reads
    `OPENROUTER_API_KEY` from the environment by default and exposes it as
    `openai_api_key` for compatibility with LangChain.

    OpenRouter sits on top of the OpenAI API and accepts the same payloads.
    See the OpenRouter documentation for full details on available models
    and usage policies.
    """

    # declare that the API key is a secret so LangChain knows not to log it
    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key", default_factory=secret_from_env("OPENROUTER_API_KEY", default=None)
    )

    @property
    def lc_secrets(self) -> Dict[str, str]:
        """Expose environment variable mapping for LangChain.

        Returns
        -------
        Dict[str, str]
            A mapping telling LangChain which environment variable holds
            sensitive information.  Without this mapping LangChain may
            inadvertently include secrets when tracing or logging.
        """

        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(self, openai_api_key: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize the ChatOpenRouter client.

        Parameters
        ----------
        openai_api_key : Optional[str], optional
            An explicit API key.  If omitted the key will be taken from
            the `OPENROUTER_API_KEY` environment variable.
        **kwargs : Any
            Additional keyword arguments passed to the underlying
            ChatOpenAI class (e.g. model_name, temperature).
        """

        # Fall back to environment variable if the caller didn't supply a key
        openai_api_key = openai_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY must be set in your environment or passed explicitly "
                "to ChatOpenRouter."
            )

        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs,
        )


def extract_pdf_text(file_data: bytes) -> str:
    """Extract all text from a PDF given its binary data.

    This helper function uses PyPDF2 to iterate over every page in a PDF and
    concatenate the extracted text into a single string.  It gracefully
    handles encrypted PDFs by attempting to decrypt with an empty password.

    Parameters
    ----------
    file_data : bytes
        Raw binary content of the PDF file.

    Returns
    -------
    str
        Concatenated text from all pages of the PDF.  Pages for which text
        extraction fails (for example due to scanning) will simply be
        skipped.
    """

    # Use BytesIO so PyPDF2 can treat the incoming bytes like a file
    reader = PdfReader(BytesIO(file_data))
    text: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            # Some PDFs require decryption even if not password protected
            if reader.is_encrypted:
                reader.decrypt("")
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        except Exception:
            # Skip pages that can't be read
            continue
    return "\n\n".join(text)


class ProcessState(TypedDict, total=False):
    """State type for the LangGraph workflow.

    Fields
    ------
    pdf_text : str
        The full textual content extracted from the uploaded PDF.
    questions : str
        User‑provided questions or assignment instructions.
    clarifications : Optional[str]
        Clarifications supplied by the user after the analysis phase.
    analysis : Optional[str]
        The output of the analysis phase (summary, topics, ambiguities).
    assignment : Optional[str]
        The final generated assignment.
    """

    pdf_text: str
    questions: str
    clarifications: Optional[str]
    analysis: Optional[str]
    assignment: Optional[str]


def _analysis_node(state: ProcessState, *, llm: ChatOpenRouter) -> ProcessState:
    """Perform an analysis of the provided PDF and questions.

    This node instructs the LLM to summarise the document, identify key
    topics and instructions, and surface any ambiguities or potential
    clarifications required from the user.  The result is stored on the
    state's `analysis` field.

    Parameters
    ----------
    state : ProcessState
        The current state passed through the LangGraph workflow.
    llm : ChatOpenRouter
        The language model used to perform analysis.

    Returns
    -------
    ProcessState
        Updated state with an `analysis` field containing the model's
        response.
    """

    pdf_text = state.get("pdf_text", "")
    questions = state.get("questions", "")
    clarifications = state.get("clarifications", "") or ""

    # System prompt instructs the model how to behave during the analysis phase
    system_prompt = (
        "You are a specialized AI academic assistant designed to analyse uploaded "
        "documents and instructions in order to prepare high‑quality assignments. "
        "During this analysis step you must carefully read the provided PDF "
        "content and any user questions or instructions. Extract and summarise "
        "the key topics, definitions, and explicit instructions found in the "
        "document. Also identify any ambiguous or unclear instructions that "
        "require clarification. Your output should be structured as follows:\n\n"
        "1. Summary: A concise summary of the document.\n"
        "2. Key Topics: A bulleted list of the main topics and subtopics found in the document.\n"
        "3. Explicit Instructions: Any explicit assignment instructions extracted verbatim from the document.\n"
        "4. Ambiguities: A list of questions for the user about parts of the document or instructions that are unclear or ambiguous.\n\n"
        "If there are no ambiguities, write 'None' under the Ambiguities section."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Document Content:\n{pdf_text}\n\n"
                f"User Questions/Instructions:\n{questions}\n"
                f"Existing Clarifications (if any):\n{clarifications}"
            ),
        },
    ]

    # Invoke the model and capture the analysis text
    response = llm.invoke(messages)
    analysis_text = response.content.strip() if hasattr(response, "content") else str(response)
    state["analysis"] = analysis_text
    return state


def _assignment_node(state: ProcessState, *, llm: ChatOpenRouter) -> ProcessState:
    """Generate the final assignment based on PDF, questions and clarifications.

    This node calls the LLM with instructions to build a structured academic
    assignment suitable for university submission.  It pulls the PDF text,
    user questions and any clarifications from the state.  The resulting
    assignment is stored on the state's `assignment` field.

    Parameters
    ----------
    state : ProcessState
        The current state passed through the LangGraph workflow.
    llm : ChatOpenRouter
        The language model used to generate the assignment.

    Returns
    -------
    ProcessState
        Updated state with an `assignment` field containing the model's
        generated assignment.
    """

    pdf_text = state.get("pdf_text", "")
    questions = state.get("questions", "")
    clarifications = state.get("clarifications", "") or ""

    system_prompt = (
        "You are a specialized AI academic assistant designed to generate high‑quality "
        "assignments based on provided documents and user instructions.  Use the "
        "content extracted from the PDF and any clarifications to create a well‑"
        "structured assignment suitable for university submission.  Your response "
        "must adhere to the following format:\n\n"
        "# Introduction\nProvide a brief overview of the topic and its significance.\n\n"
        "# Body\nOrganise the main body into logical sections with headings.  Provide "
        "detailed explanations, analysis and relevant examples derived from the "
        "source material.\n\n"
        "# Conclusion\nSummarise the key points discussed and offer any conclusions or "
        "recommendations based on the analysed content.\n\n"
        "# References\nIf applicable, list all sources referenced.  Use any citation details "
        "available in the document (e.g. authors, titles, publication dates) or, "
        "if none are present, leave this section empty.\n\n"
        "Ensure the assignment is coherent, logically organised and free from "
        "plagiarism.  Write in formal academic language."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Document Content:\n{pdf_text}\n\n"
                f"User Questions/Instructions:\n{questions}\n\n"
                f"Clarifications (if provided):\n{clarifications}"
            ),
        },
    ]

    response = llm.invoke(messages)
    assignment_text = response.content.strip() if hasattr(response, "content") else str(response)
    state["assignment"] = assignment_text
    return state


def _build_analysis_graph(llm: ChatOpenRouter):
    """Build a simple LangGraph for the analysis phase.

    The graph consists of a single node (`analysis`) that processes the
    document and instructions and populates the `analysis` field of the
    state.

    Parameters
    ----------
    llm : ChatOpenRouter
        A configured language model instance.

    Returns
    -------
    langgraph.graph.Graph
        A compiled graph ready to be invoked.
    """

    builder = StateGraph(ProcessState)
    # Use a lambda to curry the llm into the node
    builder.add_node("analysis", lambda state: _analysis_node(state, llm=llm))
    builder.set_entry_point("analysis")
    return builder.compile()


def _build_assignment_graph(llm: ChatOpenRouter):
    """Build a simple LangGraph for the assignment generation phase.

    This graph has a single node (`assignment`) that takes the state (with
    pdf_text, questions and optional clarifications) and writes the generated
    assignment into the `assignment` field.

    Parameters
    ----------
    llm : ChatOpenRouter
        A configured language model instance.

    Returns
    -------
    langgraph.graph.Graph
        A compiled graph ready to be invoked.
    """

    builder = StateGraph(ProcessState)
    builder.add_node("assignment", lambda state: _assignment_node(state, llm=llm))
    builder.set_entry_point("assignment")
    return builder.compile()


def run_analysis(pdf_text: str, questions: str, *, model_name: str = "z-ai/glm-4.5-air:free", temperature: float = 0.0) -> str:
    """Run the analysis phase and return the analysis output.

    This helper function wraps the analysis graph, instantiates the LLM and
    invokes the graph with the provided PDF text and user questions.

    Parameters
    ----------
    pdf_text : str
        The full text extracted from a PDF.
    questions : str
        User‑provided questions or assignment instructions.
    model_name : str, optional
        The model identifier to use on OpenRouter.  Defaults to
        ``"openai/gpt-3.5-turbo"`` which is widely available.  You can choose
        any other model supported by OpenRouter, e.g. ``"anthropic/claude-3-7-sonnet"``.
    temperature : float, optional
        Sampling temperature for the LLM.  Defaults to 0.0 for deterministic
        output.

    Returns
    -------
    str
        The analysis output containing summary, key topics, explicit
        instructions and any detected ambiguities.
    """

    llm = ChatOpenRouter(model_name=model_name, temperature=temperature)
    graph = _build_analysis_graph(llm)
    initial_state: ProcessState = {
        "pdf_text": pdf_text,
        "questions": questions,
        "clarifications": None,
        "analysis": None,
        "assignment": None,
    }
    result_state = graph.invoke(initial_state)
    return result_state.get("analysis", "") or ""


def run_assignment(
    pdf_text: str,
    questions: str,
    clarifications: Optional[str] = None,
    *,
    model_name: str = "z-ai/glm-4.5-air:free",
    temperature: float = 0.0,
) -> str:
    """Run the assignment generation phase and return the assignment output.

    This helper function wraps the assignment graph, instantiates the LLM and
    invokes the graph with the provided PDF text, questions and optional
    clarifications.

    Parameters
    ----------
    pdf_text : str
        The full text extracted from a PDF.
    questions : str
        User‑provided questions or assignment instructions.
    clarifications : Optional[str], optional
        Additional clarifications provided by the user after reviewing the
        analysis.  Defaults to ``None``.
    model_name : str, optional
        The model identifier to use on OpenRouter.  Defaults to
        ``"openai/gpt-3.5-turbo"``.
    temperature : float, optional
        Sampling temperature for the LLM.  Defaults to 0.0 for deterministic
        output.

    Returns
    -------
    str
        A complete academic assignment conforming to the structure defined in
        the system prompt.
    """

    llm = ChatOpenRouter(model_name=model_name, temperature=temperature)
    graph = _build_assignment_graph(llm)
    initial_state: ProcessState = {
        "pdf_text": pdf_text,
        "questions": questions,
        "clarifications": clarifications,
        "analysis": None,
        "assignment": None,
    }
    result_state = graph.invoke(initial_state)
    return result_state.get("assignment", "") or ""

# -----------------------------------------------------------------------------
# ODT Generation - NEW FUNCTIONALITY
# -----------------------------------------------------------------------------

def _markdown_to_odt_content(text: str) -> str:
    """Convert Markdown-like text to ODT XML content.
    
    This function converts simple Markdown formatting to OpenDocument Text XML.
    It handles headings, paragraphs, lists, and basic formatting.
    
    Parameters
    ----------
    text : str
        Input text with Markdown-like formatting
        
    Returns
    -------
    str
        ODT XML content as a string
    """
    
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


def _escape_xml(text: str) -> str:
    """Escape XML special characters in text.
    
    Parameters
    ----------
    text : str
        Text to escape
        
    Returns
    -------
    str
        XML-escaped text
    """
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))


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
    """
    Generate a professional ODT (OpenDocument Text) assignment file.
    
    This function creates a well-formatted ODT document with a cover page
    and properly styled content. The ODT format is compatible with LibreOffice
    Writer, Microsoft Word, and other word processors.
    
    Parameters
    ----------
    name : str
        The student's full name
    registration_number : str
        The student's registration or ID number
    instructor_name : str
        The course instructor's name
    semester : str
        The semester or term
    university_name : str
        The university or institution name
    assignment_text : str
        The assignment content in Markdown format
    filename : Optional[str], optional
        If provided, saves the ODT to this file path
    title : str, optional
        The assignment title, defaults to "Assignment"
        
    Returns
    -------
    bytes
        The ODT file as bytes
    """
    
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


# -----------------------------------------------------------------------------
# PDF Generation - EXISTING FUNCTIONALITY (KEPT FOR COMPATIBILITY)
# -----------------------------------------------------------------------------

def create_assignment_pdf(
    name: str,
    registration_number: str,
    instructor_name: str,
    semester: str,
    university_name: str,
    assignment_text: str,
    *,
    filename: str | None = None,
    include_page_numbers: bool = True,
    title: str = "Assignment",
    logo_path: str | None = None,
) -> bytes:
    """
    Generate a cleanly formatted assignment PDF with a professional look.

    This helper produces a multi‑page PDF with a cover sheet followed by
    neatly typeset content pages.  It aims to mimic the appearance of a
    submitted university assignment: headings are clearly distinguished,
    paragraphs are aligned with appropriate margins, bulleted and numbered
    lists are indented consistently and page numbers are centred at the
    bottom of every page.  A university logo may optionally appear on the
    cover page and the title text is customisable.

    Parameters
    ----------
    name : str
        The student's full name (e.g. "Jane Doe").
    registration_number : str
        The student's registration or roll number.
    instructor_name : str
        The name of the course instructor.
    semester : str
        The semester or term for which the assignment is being prepared.
    university_name : str
        The name of the university or institution.
    assignment_text : str
        The assignment body in simple Markdown‑like format.  Lines beginning
        with one or more ``#`` characters are treated as headings, while
        lines beginning with ``- ``, ``* `` or numeric lists (e.g. ``1. ``)
        are rendered as bullet points.  Other lines become normal
        paragraphs.
    filename : Optional[str], optional
        If provided, the PDF will be written directly to this path in
        addition to being returned as a byte string.  When omitted the
        PDF is generated entirely in memory.
    include_page_numbers : bool, optional
        Whether to include page numbers on the content pages.  Defaults
        to ``True``.
    title : str, optional
        The cover page heading.  Defaults to ``"Assignment"``.
    logo_path : Optional[str], optional
        A path to a PNG or JPEG image to display on the cover sheet.  If
        omitted or invalid the logo will be skipped gracefully.

    Returns
    -------
    bytes
        The generated PDF data.
    """
    # Import here to avoid pulling heavy dependencies at import time when
    # end‑users do not generate PDFs.
    from io import BytesIO
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore

    from typing import Any
    import re

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    # Use a serif font by default for a more formal look
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 12,
    })

    # Define page size (A4 portrait) in inches
    width, height = 8.27, 11.69

    # ------------------------------------------------------------------
    # Layout and spacing - FIXED MARGINS
    # ------------------------------------------------------------------
    left_margin_in = 1.0
    right_margin_in = 1.0
    top_margin_in = 1.0
    bottom_margin_in = 1.0
    
    # Convert margins from inches to axes fraction
    left_margin = left_margin_in / width
    right_margin = right_margin_in / width
    top_margin = top_margin_in / height
    bottom_margin = bottom_margin_in / height

    # Line spacing - FIXED to prevent overlap
    base_line_height_in = 0.2  # Base line height in inches
    base_line_height = base_line_height_in / height

    # Helper to load logo if provided
    logo_img = None
    if logo_path and Image is not None:
        try:
            logo_img = Image.open(logo_path)
        except Exception:
            logo_img = None

    # Buffer for in‑memory PDF
    buffer = BytesIO()

    with PdfPages(buffer if filename is None else filename) as pdf:
        # --------------------------------------------------------------
        # Cover Page
        # --------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(width, height))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        
        # Draw a proper border around the entire page
        border_pad = 0.00
        rect = plt.Rectangle(
            (border_pad, border_pad),
            1 - 2 * border_pad,
            1 - 2 * border_pad,
            linewidth=2,
            edgecolor='black',
            facecolor='none',
        )
        ax.add_patch(rect)

        # Place logo at the top if available
        y_offset = 0.85
        if logo_img is not None:
            max_logo_height = 0.15
            img_w, img_h = logo_img.size
            aspect = img_h / img_w
            logo_h_rel = min(max_logo_height, aspect * 0.3)
            logo_w_rel = logo_h_rel / aspect
            
            # Center the logo
            logo_x = 0.5 - logo_w_rel / 2
            ax.imshow(
                logo_img,
                aspect='auto',
                extent=[logo_x, logo_x + logo_w_rel, y_offset - logo_h_rel, y_offset],
                zorder=1,
            )
            y_offset -= logo_h_rel + 0.05

        # Title text on the cover
        ax.text(
            0.5,
            y_offset,
            title,
            ha='center',
            va='center',
            transform=ax.transAxes,
            fontsize=24,
            fontweight='bold',
        )
        y_offset -= 0.15

        # Student and course details
        details = [
            ("Student Name", name),
            ("Registration Number", registration_number),
            ("Instructor Name", instructor_name),
            ("Semester", semester),
            ("University", university_name),
        ]
        
        for label, value in details:
            if value:
                ax.text(
                    0.5,
                    y_offset,
                    f"{label}: {value}",
                    ha='center',
                    va='center',
                    transform=ax.transAxes,
                    fontsize=12,
                )
                y_offset -= 0.06

        pdf.savefig(fig, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)

        # --------------------------------------------------------------
        # Parse assignment text into styled lines - IMPROVED
        # --------------------------------------------------------------
        def parse_lines(text: str) -> list[tuple[str, dict[str, Any]]]:
            parsed: list[tuple[str, dict[str, Any]]] = []
            lines = text.strip().split("\n")
            
            for raw in lines:
                line = raw.rstrip()
                if not line:
                    # Empty line - add small spacing
                    parsed.append(("", {
                        'fontsize': 12, 
                        'weight': 'normal', 
                        'indent': 0.0, 
                        'line_height_multiplier': 0.5
                    }))
                    continue
                
                # Detect headings
                stripped = line.lstrip()
                if stripped.startswith('#'):
                    level = len(stripped) - len(stripped.lstrip('#'))
                    content = stripped[level:].strip()
                    if level == 1:
                        size, weight, multiplier = 18, 'bold', 2.0
                    elif level == 2:
                        size, weight, multiplier = 16, 'bold', 1.8
                    else:
                        size, weight, multiplier = 14, 'bold', 1.6
                    parsed.append((content, {
                        'fontsize': size, 
                        'weight': weight, 
                        'indent': 0.0, 
                        'line_height_multiplier': multiplier
                    }))
                    continue
                
                # Detect unordered list
                if stripped.startswith(('- ', '* ', '+ ')):
                    content = stripped[2:].strip()
                    parsed.append((f"• {content}", {
                        'fontsize': 12, 
                        'weight': 'normal', 
                        'indent': 0.03, 
                        'line_height_multiplier': 1.2
                    }))
                    continue
                
                # Detect ordered list
                if re.match(r"^\d+[\.|\)]\s+", stripped):
                    match = re.match(r"^(\d+)[\.|\)]\s+", stripped)
                    if match:
                        number = match.group(1)
                        content = re.sub(r"^\d+[\.|\)]\s+", "", stripped)
                        parsed.append((f"{number}. {content}", {
                            'fontsize': 12, 
                            'weight': 'normal', 
                            'indent': 0.03, 
                            'line_height_multiplier': 1.2
                        }))
                    continue
                
                # Plain paragraph
                parsed.append((line.strip(), {
                    'fontsize': 12, 
                    'weight': 'normal', 
                    'indent': 0.0, 
                    'line_height_multiplier': 1.3
                }))
            
            return parsed

        parsed_lines = parse_lines(assignment_text)

        # --------------------------------------------------------------
        # Improved text wrapping - COMPLETELY REWRITTEN
        # --------------------------------------------------------------
        def wrap_text_simple(text: str, max_chars_per_line: int) -> list[str]:
            """Simple character-based wrapping that prevents overlap"""
            if not text.strip():
                return [""]
            
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                word_length = len(word)
                space_length = 1 if current_line else 0
                
                if current_length + space_length + word_length <= max_chars_per_line:
                    current_line.append(word)
                    current_length += space_length + word_length
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = word_length
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines if lines else [""]

        # Calculate max characters based on available width
        available_width = 1.0 - left_margin - right_margin
        # Rough estimate: 12pt font can fit about 90-100 chars in our page width
        base_max_chars = int(available_width * 120)

        # Apply wrapping to all parsed lines
        wrapped: list[tuple[str, dict[str, Any]]] = []
        for text_line, style in parsed_lines:
            if text_line == "":
                wrapped.append(("", style))
            else:
                # Adjust max chars based on font size and indent
                fs = style['fontsize']
                indent = style.get('indent', 0.0)
                size_factor = 12.0 / fs
                indent_factor = (available_width - indent) / available_width
                max_chars = int(base_max_chars * size_factor * indent_factor)
                
                lines = wrap_text_simple(text_line, max_chars)
                for i, line in enumerate(lines):
                    # Only the last line of a paragraph gets full spacing
                    line_style = style.copy()
                    if i < len(lines) - 1:
                        line_style['line_height_multiplier'] = 1.0
                    wrapped.append((line, line_style))

        # --------------------------------------------------------------
        # Render content pages - FIXED Y-POSITION CALCULATION
        # --------------------------------------------------------------
        page_number = 1

        def render_page(lines: list[tuple[str, dict[str, Any]]]):
            """Render a single content page with proper spacing"""
            nonlocal page_number
            
            fig, ax = plt.subplots(figsize=(width, height))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            # Draw page border
            border_pad = 0.02
            rect = plt.Rectangle(
                (border_pad, border_pad),
                1 - 2 * border_pad,
                1 - 2 * border_pad,
                linewidth=1,
                edgecolor='black',
                facecolor='none',
            )
            ax.add_patch(rect)

            # Start position (top of content area)
            y_position = 1.0 - top_margin

            # Render lines with FIXED spacing
            for text_line, style in lines:
                fs = style['fontsize']
                weight = style['weight']
                indent = style.get('indent', 0.0)
                multiplier = style.get('line_height_multiplier', 1.3)
                
                # Calculate actual line height
                line_height = base_line_height * multiplier * (fs / 12.0)
                
                # Move down by line height FIRST to position baseline correctly
                y_position -= line_height
                
                # Check if we're still in valid area
                if y_position < bottom_margin:
                    break
                
                # Render text at this position (using 'bottom' alignment)
                if text_line:  # Only render non-empty lines
                    ax.text(
                        left_margin + indent,
                        y_position,
                        text_line,
                        ha='left',
                        va='bottom',  # CRITICAL: Changed from 'top' to 'bottom'
                        transform=ax.transAxes,
                        fontsize=fs,
                        fontweight=weight,
                        wrap=False,
                    )

            # Add page number
            if include_page_numbers:
                ax.text(
                    0.5,
                    bottom_margin / 2,
                    f"Page {page_number}",
                    ha='center',
                    va='center',
                    transform=ax.transAxes,
                    fontsize=10,
                    color='gray',
                )

            pdf.savefig(fig, bbox_inches='tight', pad_inches=0.1)
            plt.close(fig)
            page_number += 1

        # Paginate content with FIXED height calculation
        current_page_content = []
        current_y = 1.0 - top_margin
        
        for text_line, style in wrapped:
            fs = style['fontsize']
            multiplier = style.get('line_height_multiplier', 1.3)
            line_height = base_line_height * multiplier * (fs / 12.0)
            
            # Check if line fits on current page
            if current_y - line_height < bottom_margin:
                if current_page_content:
                    render_page(current_page_content)
                    current_page_content = []
                    current_y = 1.0 - top_margin
            
            current_page_content.append((text_line, style))
            current_y -= line_height

        # Render the final page
        if current_page_content:
            render_page(current_page_content)

    # Return PDF data
    if filename is not None:
        with open(filename, 'rb') as f:
            data = f.read()
        return data
    return buffer.getvalue()