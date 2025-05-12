import requests
from reportlab.lib.pagesizes import A4, landscape # Import landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm # Import cm for easier footer positioning
from reportlab.lib.colors import blue, grey, black, HexColor # Import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT # For text alignment
from io import BytesIO
import base64
import streamlit as st
from reportlab.lib.utils import ImageReader
import datetime # To get the current date

# --- Helper Functions ---

def image_from_mermaid(graph):
    """
    Fetches an image representation of Mermaid code from the mermaid.ink service.

    Args:
        graph (str): The Mermaid code string.

    Returns:
        BytesIO: A BytesIO object containing the image data, or None if generation fails.
    """
    if not graph:
        st.warning("Mermaid graph data is empty.")
        return None
        
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    
    mermaid_ink_url = f"https://mermaid.ink/img/{base64_string}"
    
    try:
        # st.info(f"Requesting Mermaid image from: {mermaid_ink_url}") # For debugging
        response = requests.get(mermaid_ink_url, timeout=20) # Increased timeout
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        return BytesIO(response.content)
    except requests.exceptions.Timeout:
        st.error("Mermaid image generation timed out.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Mermaid image generation failed with HTTP status {e.response.status_code}.")
        # st.error(f"Response content: {e.response.text[:500]}") # Log part of the error response
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Mermaid image generation request failed: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Mermaid image generation: {e}")
        return None


def remove_first_non_empty_line_if_mermaid(mermaid_code):
    """
    Removes the first line containing only "mermaid" (case-insensitive) from the code.
    This is often needed as some renderers add it automatically, but mermaid.ink might not want it.
    """
    lines = mermaid_code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "mermaid":
            lines.pop(i)
            break
    return '\n'.join(lines)

def fit_image_to_page(image_data_bytesio, page_width, page_height, margin=0.75*inch):
    """
    Fits an image (from BytesIO) to the available page width/height, maintaining aspect ratio.
    page_width and page_height are the total dimensions of the page.
    margin is the margin on each side, so available width/height is reduced.
    """
    if not image_data_bytesio:
        return None
    try:
        # Ensure the BytesIO cursor is at the beginning
        image_data_bytesio.seek(0)
        img_reader = ImageReader(image_data_bytesio)
    except Exception as e:
        st.error(f"Error reading image data for fitting: {e}. Image data might be corrupted or empty.")
        # To debug, you could try saving the BytesIO content to a file here
        # with open("debug_image_data.bin", "wb") as f:
        #     image_data_bytesio.seek(0)
        #     f.write(image_data_bytesio.read())
        return None
        
    img_width, img_height = img_reader.getSize()
    if img_height == 0: # Avoid division by zero
        st.error("Image height is zero, cannot calculate aspect ratio.")
        return None
    aspect_ratio = img_width / img_height

    available_width = page_width - (2 * margin)
    available_height = page_height - (2 * margin)
    
    if available_width <= 0 or available_height <= 0:
        st.error("Available width or height for image is zero or negative after applying margins.")
        return None

    # Determine new dimensions
    if (available_width / aspect_ratio) <= available_height:
        new_width = available_width
        new_height = new_width / aspect_ratio
    else:
        new_height = available_height
        new_width = new_height * aspect_ratio
        
    # Ensure the BytesIO cursor is at the beginning for the Image object
    image_data_bytesio.seek(0)
    return Image(image_data_bytesio, width=new_width, height=new_height)

# --- PDF Structure Elements ---

# Global variable for report generation date (set once when the module is loaded)
REPORT_GENERATION_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

def footer_canvas(canvas, doc):
    """
    Function to draw the footer on each page.
    Includes report generation date and page number.
    Adjusts position for landscape mode.
    """
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    
    page_width = doc.pagesize[0] # Get current page width (handles portrait/landscape)

    # Page number (right-aligned)
    page_num_text = f"Page {doc.page}"
    canvas.drawRightString(page_width - 0.75 * inch, 0.75 * inch, page_num_text)
    
    # Generation date (left-aligned)
    date_text = f"Report Generated: {REPORT_GENERATION_DATE}"
    canvas.drawString(0.75 * inch, 0.75 * inch, date_text)
    
    canvas.restoreState()

# --- Main PDF Creation Function ---

def create_pdf_bytes(url, content, mermaid_code, attackpath=None, orientation='portrait'):
    """
    Creates a PDF document with Threat Intelligence information.

    Args:
        url (str): The source URL for the report.
        content (str): The main textual content (e.g., AI summary).
        mermaid_code (str): The Mermaid syntax for the mind map.
        attackpath (str, optional): Text describing TTPs. Defaults to None.
        orientation (str, optional): 'portrait' or 'landscape'. Defaults to 'portrait'.

    Returns:
        bytes: A bytes object containing the generated PDF, or None if generation fails.
    """
    pdf_bytes_io = BytesIO()

    # Set page size based on orientation
    current_pagesize = A4
    if orientation == 'landscape':
        current_pagesize = landscape(A4)

    # Margins for the document content area
    left_margin, right_margin = 0.75 * inch, 0.75 * inch
    top_margin, bottom_margin = 1.0 * inch, 1.25 * inch # Increased bottom margin for footer

    # Create a Frame for the content area
    frame_width = current_pagesize[0] - left_margin - right_margin
    frame_height = current_pagesize[1] - top_margin - bottom_margin
    frame = Frame(left_margin, bottom_margin, frame_width, frame_height, id='normal_frame')
    
    # Create a PageTemplate that uses the footer_canvas function
    page_template = PageTemplate(id='main_template', frames=[frame], onPage=footer_canvas, pagesize=current_pagesize)

    doc = SimpleDocTemplate(pdf_bytes_io, pagesize=current_pagesize,
                            title="TI Mindmap Report",
                            author="TI-Mindmap-GPT",
                            leftMargin=left_margin, rightMargin=right_margin,
                            topMargin=top_margin, bottomMargin=bottom_margin)
    
    doc.addPageTemplates([page_template])

    styles = getSampleStyleSheet()
    
    # --- Define Diverse Paragraph Styles ---
    main_title_style = ParagraphStyle(
        'MainTitle', parent=styles['h1'], fontSize=20, leading=24,
        spaceAfter=0.2*inch, alignment=TA_CENTER, textColor=HexColor("#2c3e50")
    )
    intro_style = ParagraphStyle(
        'IntroStyle', parent=styles['Normal'], fontSize=10, leading=14,
        spaceAfter=0.1*inch, textColor=HexColor("#555555"), alignment=TA_LEFT
    )
    link_style = ParagraphStyle(
        'LinkStyle', parent=styles['Normal'], fontSize=9, leading=12,
        textColor=blue # ReportLab handles <a href> for underline
    )
    section_header_style = ParagraphStyle(
        'SectionHeader', parent=styles['h2'], fontSize=16, leading=20,
        spaceBefore=0.2*inch, spaceAfter=0.1*inch, textColor=HexColor("#34495e")
    )
    body_text_style = ParagraphStyle(
        'BodyText', parent=styles['Normal'], fontSize=10, leading=14,
        spaceAfter=0.1*inch, alignment=TA_LEFT
    )
    italic_content_style = ParagraphStyle(
        'ItalicContent', parent=styles['Normal'], fontName='Helvetica-Oblique',
        fontSize=10, leading=14, spaceAfter=0.1*inch, textColor=HexColor("#4a4a4a")
    )
    code_style = ParagraphStyle(
        'CodeStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10,
        textColor=HexColor("#333333"), backColor=HexColor("#f4f4f4"),
        borderPadding=(2, 4), borderColor=HexColor("#dddddd"), borderWidth=0.5,
        leftIndent=10, rightIndent=10, spaceBefore=5, spaceAfter=5
    )
    ttp_list_style = ParagraphStyle(
        'TTPListStyle', parent=styles['Normal'], fontSize=9, leading=12,
        leftIndent=0.25*inch, bulletIndent=0.1*inch, spaceAfter=0.05*inch
    )
    error_text_style = ParagraphStyle( # Style for error messages in PDF
        'ErrorText', parent=styles['Normal'], fontSize=9, leading=12,
        textColor=HexColor("#c0392b"), fontName='Helvetica-Oblique' # Red, italic
    )
    # --- End of Style Definitions ---

    flowables = []
    
    # Main Title and Intro
    flowables.append(Paragraph("Threat Intelligence Mindmap Report", main_title_style))
    flowables.append(Paragraph("AI-powered tool for Threat Intelligence summaries, mind maps, and IOC extraction.", intro_style))
    flowables.append(Paragraph(f'App URL: <a href="https://ti-mindmap-gpt.streamlit.app/">ti-mindmap-gpt.streamlit.app</a>', link_style))
    flowables.append(Paragraph(f'GitHub: <a href="https://github.com/format81/TI-Mindmap-GPT">github.com/format81/TI-Mindmap-GPT</a>', link_style))
    flowables.append(Spacer(1, 0.2 * inch))

    # Report Section
    flowables.append(Paragraph("SOURCE INFORMATION", section_header_style))
    flowables.append(Paragraph(f'Original Source: <a href="{url}">{url}</a>', link_style))
    flowables.append(Spacer(1, 0.1 * inch))

    # Screenshot Section
    flowables.append(Paragraph("WEBSITE SCREENSHOT", section_header_style))
    try:
        api_key_thumbnail = st.secrets.get("api_keys", {}).get("thumbnail")
        if not api_key_thumbnail:
            st.warning("Thumbnail API key not found in Streamlit secrets.")
            raise ValueError("Thumbnail API key missing.")

        screenshot_response = requests.get(
            f"https://api.thumbnail.ws/api/{api_key_thumbnail}/thumbnail/get?url={url}&width=1280&delay=2500",
            timeout=35
        )
        screenshot_response.raise_for_status()
        
        screenshot_img_data = BytesIO(screenshot_response.content)
        img_fitted = fit_image_to_page(screenshot_img_data, current_pagesize[0], current_pagesize[1]) 
        if img_fitted:
            flowables.append(img_fitted)
        else:
            flowables.append(Paragraph("Could not process screenshot image (fit_image_to_page returned None).", error_text_style))
        flowables.append(Spacer(1, 0.1 * inch))

    except ValueError as ve:
         flowables.append(Paragraph(f"Screenshot generation skipped: {ve}", error_text_style))
    except requests.exceptions.Timeout:
        st.warning("Screenshot generation timed out.")
        flowables.append(Paragraph("Screenshot generation timed out.", error_text_style))
    except requests.exceptions.HTTPError as e:
        st.warning(f"Failed to get screenshot. HTTP Status: {e.response.status_code}")
        flowables.append(Paragraph(f"Failed to retrieve screenshot. Status: {e.response.status_code}", error_text_style))
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get screenshot: {e}")
        flowables.append(Paragraph(f"Could not retrieve screenshot: {e}", error_text_style))
    except Exception as e:
        st.error(f"An error occurred while processing the screenshot: {e}")
        flowables.append(Paragraph(f"Error processing screenshot: {e}", error_text_style))

    # Mind Map Section
    flowables.append(Paragraph("MIND MAP VISUALIZATION", section_header_style))
    try:
        processed_mermaid_code = remove_first_non_empty_line_if_mermaid(mermaid_code)
        if not processed_mermaid_code.strip():
            raise ValueError("Mermaid code is empty after processing.")
            
        mindmap_img_data = image_from_mermaid(processed_mermaid_code)
        if mindmap_img_data:
            img_fitted = fit_image_to_page(mindmap_img_data, current_pagesize[0], current_pagesize[1])
            if img_fitted:
                flowables.append(img_fitted)
            else: # fit_image_to_page returned None
                flowables.append(Paragraph("Could not process mind map image (fit_image_to_page returned None).", error_text_style))
                raise ValueError("Mind map image fitting failed.") # Trigger code display
        else: # image_from_mermaid returned None
            raise ValueError("Mind map image data could not be fetched or is None.")
            
    except Exception as e:
        st.error(f"Failed to generate or add mind map image: {e}")
        flowables.append(Paragraph(f"Could not generate mind map image: {e}", error_text_style))
        flowables.append(Paragraph("<b>Mermaid Code Used:</b>", body_text_style))
        for line in mermaid_code.splitlines(): # Display original mermaid_code
            flowables.append(Paragraph(line if line.strip() else " ", code_style))
    flowables.append(Spacer(1, 0.2 * inch))
    
    # Generated Content Section
    flowables.append(Paragraph("AI-GENERATED SUMMARY & ANALYSIS", section_header_style))
    flowables.append(Paragraph(content if content and content.strip() else "No summary content provided.", italic_content_style))
    flowables.append(Spacer(1, 0.2 * inch))

    # Attack Path / TTPs Section
    if attackpath and attackpath.strip():
        flowables.append(Paragraph("TACTICS, TECHNIQUES, AND PROCEDURES (TTPs)", section_header_style))
        flowables.append(Paragraph("Ordered by perceived execution time:", intro_style))
        attackpath_lines = attackpath.split('\n')
        for line in attackpath_lines:
            if line.strip():
                flowables.append(Paragraph(f"•  {line.strip()}", ttp_list_style)) # Added bullet and strip
    
    try:
        doc.build(flowables)
        pdf_bytes = pdf_bytes_io.getvalue()
        pdf_bytes_io.close()
        return pdf_bytes
    except Exception as e:
        st.error(f"CRITICAL: Failed to build PDF document: {e}")
        # Potentially log the flowables list here for debugging if possible
        # For example: st.json([str(f) for f in flowables[:10]]) # Log first 10 flowables
        pdf_bytes_io.close()
        return None


# --- Example usage (for testing, not part of the Streamlit app flow directly) ---
if __name__ == '__main__':
    # This is a dummy example for local testing of create_pdf_bytes
    # In your Streamlit app, you'll call create_pdf_bytes with actual data
    
    # Mock st.secrets for local testing if not running in Streamlit
    class MockSecrets(dict):
        def get(self, key, default=None):
            return super().get(key, default if default is not None else {})

    # Check if st.secrets exists (i.e., running in Streamlit)
    # If not, create a mock. This allows running the script locally.
    if not hasattr(st, 'secrets'):
        st.secrets = MockSecrets(api_keys={"thumbnail": "YOUR_THUMBNAIL_API_KEY_HERE_OR_MOCK"})
        # You might need to mock st.error, st.warning, st.info as well if they are called
        def mock_st_method(message): print(f"ST_MOCK: {message}")
        st.error = mock_st_method
        st.warning = mock_st_method
        st.info = mock_st_method


    dummy_url = "https://www.example.com"
    dummy_content = (
        "This is a detailed AI-generated summary about the threat landscape observed from the source. "
        "It highlights key actors, vulnerabilities exploited, and recommended mitigations. "
        "The analysis focuses on the strategic implications for organizations in the targeted sector.\n\n"
        "Further points include:\n"
        "- Point Alpha\n- Point Beta\n- Point Gamma"
    )
    dummy_mermaid_code = """
    mindmap
      root((Example Threat))
        (Initial Access)
          (Phishing Campaign)
            (Spearphishing Link)
            (Credential Harvesting)
        (Execution)
          (PowerShell Scripts)
            (Obfuscated Commands)
        (Persistence)
          (Scheduled Tasks)
          (Registry Run Keys)
        (Impact)
          (Data Exfiltration)
          (Ransomware Deployment)
    """
    dummy_attackpath = (
        "Phishing Campaign (Targeting Finance Department)\n"
        "Execution of PowerShell Script (Downloads further payload)\n"
        "Creation of Scheduled Task (For persistence every hour)\n"
        "Lateral Movement (Using stolen credentials)\n"
        "Data Exfiltration (Sensitive documents uploaded to C2)"
    )
    
    print("Generating Portrait PDF...")
    pdf_data_portrait = create_pdf_bytes(dummy_url, dummy_content, dummy_mermaid_code, dummy_attackpath, orientation='portrait')
    if pdf_data_portrait:
        with open("ti_mindmap_report_portrait.pdf", "wb") as f:
            f.write(pdf_data_portrait)
        print("Portrait PDF 'ti_mindmap_report_portrait.pdf' generated successfully.")
    else:
        print("Failed to generate portrait PDF.")

    print("\nGenerating Landscape PDF...")
    pdf_data_landscape = create_pdf_bytes(dummy_url, dummy_content, dummy_mermaid_code, dummy_attackpath, orientation='landscape')
    if pdf_data_landscape:
        with open("ti_mindmap_report_landscape.pdf", "wb") as f:
            f.write(pdf_data_landscape)
        print("Landscape PDF 'ti_mindmap_report_landscape.pdf' generated successfully.")
    else:
        print("Failed to generate landscape PDF.")

    # Test with empty mermaid code
    print("\nGenerating PDF with empty Mermaid code (expecting error handling)...")
    pdf_data_empty_mermaid = create_pdf_bytes(dummy_url, dummy_content, " ", dummy_attackpath, orientation='portrait')
    if pdf_data_empty_mermaid:
        with open("ti_mindmap_report_empty_mermaid.pdf", "wb") as f:
            f.write(pdf_data_empty_mermaid)
        print("PDF with empty mermaid 'ti_mindmap_report_empty_mermaid.pdf' generated (check content for error message).")
    else:
        print("Failed to generate PDF for empty mermaid test (as expected if build fails).")