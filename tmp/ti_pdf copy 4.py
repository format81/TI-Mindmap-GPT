import requests
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageTemplate, Frame, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import blue, grey, black, HexColor, beige, lightgrey # Import specific colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from io import BytesIO
import base64
import streamlit as st
from reportlab.lib.utils import ImageReader
import datetime
import pandas as pd
import re # For Markdown table parsing

# --- Helper Functions ---

def image_from_mermaid(graph, context="Mind Map"):
    """
    Fetches an image representation of Mermaid code from the mermaid.ink service.

    Args:
        graph (str): The Mermaid code string.
        context (str): A string describing the context (e.g., "Mind Map", "TTP Timeline") for error messages.

    Returns:
        BytesIO: A BytesIO object containing the image data, or None if generation fails.
    """
    if not graph or not graph.strip():
        st.warning(f"Mermaid graph data for {context} is empty. Cannot generate image.") # Streamlit log
        return None
        
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    
    mermaid_ink_url = f"https://mermaid.ink/img/{base64_string}"
    
    try:
        # st.info(f"Requesting Mermaid image for {context} from: {mermaid_ink_url}") # For Streamlit debugging
        response = requests.get(mermaid_ink_url, timeout=30) # Increased timeout slightly
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        return BytesIO(response.content)
    except requests.exceptions.Timeout:
        st.error(f"Mermaid image generation for {context} timed out contacting mermaid.ink.") # Streamlit log
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Mermaid image generation for {context} failed. HTTP status: {e.response.status_code}. URL: {mermaid_ink_url}") # Streamlit log
        # st.error(f"Response content from mermaid.ink: {e.response.text[:500]}") # Uncomment for more debug info
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Mermaid image generation request for {context} failed: {e}") # Streamlit log
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Mermaid image generation for {context}: {e}") # Streamlit log
        return None


def remove_first_non_empty_line_if_mermaid(mermaid_code):
    """
    Removes the first line containing only "mermaid" (case-insensitive) from the code.
    """
    if not mermaid_code: return ""
    lines = mermaid_code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "mermaid":
            lines.pop(i)
            break
    return '\n'.join(lines)

def fit_image_to_page(image_data_bytesio, page_width, page_height, margin=0.75*inch):
    """
    Fits an image (from BytesIO) to the available page width/height, maintaining aspect ratio.
    """
    if not image_data_bytesio:
        return None
    try:
        image_data_bytesio.seek(0)
        img_reader = ImageReader(image_data_bytesio)
    except Exception as e:
        st.error(f"Error reading image data for fitting: {e}. Image data might be corrupted or empty.")
        return None
        
    img_width, img_height = img_reader.getSize()
    if img_height == 0 or img_width == 0:
        st.error("Image height or width is zero, cannot calculate aspect ratio or fit image.")
        return None
    aspect_ratio = img_width / img_height

    available_width = page_width - (2 * margin)
    available_height = page_height - (2 * margin)
    
    if available_width <= 0 or available_height <= 0:
        st.error("Available width or height for image is zero or negative after applying margins.")
        return None

    if aspect_ratio == 0: # Should be caught by img_width == 0 but as an extra check
        st.error("Image aspect ratio is zero, cannot fit image.")
        return None

    if (available_width / aspect_ratio) <= available_height:
        new_width = available_width
        new_height = new_width / aspect_ratio
    else:
        new_height = available_height
        new_width = new_height * aspect_ratio
        
    image_data_bytesio.seek(0)
    return Image(image_data_bytesio, width=new_width, height=new_height)

def parse_markdown_table(markdown_string):
    """
    Parses a simple Markdown table string into a list of lists (rows and cells).
    Returns None if parsing fails or input is not a valid table structure.
    """
    if not markdown_string or not markdown_string.strip():
        return None

    lines = [line.strip() for line in markdown_string.strip().split('\n')]
    table_lines = [line for line in lines if line.startswith('|') and line.endswith('|')]

    if not table_lines or len(table_lines) < 2: 
        return None

    separator_index = -1
    for i, line in enumerate(table_lines):
        if all(c in '|-:' for c in line):
            cells = [cell.strip() for cell in line[1:-1].split('|')]
            if all(all(sc in '-:' for sc in cell) and cell for cell in cells):
                separator_index = i
                break
    
    data = []
    header_processed = False
    num_cols = 0

    for i, line in enumerate(table_lines):
        if i == separator_index: 
            continue
        cells_str = [cell.strip() for cell in line[1:-1].split('|')]
        if not header_processed:
            num_cols = len(cells_str)
            if num_cols == 0: return None
            data.append(cells_str)
            header_processed = True
        elif len(cells_str) == num_cols:
            data.append(cells_str)

    if not data or not data[0]:
        return None
    return data

# --- PDF Structure Elements ---
REPORT_GENERATION_DATE = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def footer_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_width = doc.pagesize[0]
    canvas.drawRightString(page_width - 0.75 * inch, 0.75 * inch, f"Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.75 * inch, f"Report Generated: {REPORT_GENERATION_DATE}")
    canvas.restoreState()

# --- Main PDF Creation Function ---
def create_pdf_bytes(url, summary_content, mindmap_mermaid_code, 
                     iocs_data=None, ttps_overview_data=None, attack_path_data=None, 
                     mermaid_timeline_code=None, five_whats_data=None, 
                     orientation='portrait'):
    pdf_bytes_io = BytesIO()
    current_pagesize = A4 if orientation == 'portrait' else landscape(A4)
    left_margin, right_margin = 0.75 * inch, 0.75 * inch
    top_margin, bottom_margin = 1.0 * inch, 1.25 * inch
    frame_width = current_pagesize[0] - left_margin - right_margin
    frame_height = current_pagesize[1] - top_margin - bottom_margin
    frame = Frame(left_margin, bottom_margin, frame_width, frame_height, id='normal_frame')
    page_template = PageTemplate(id='main_template', frames=[frame], onPage=footer_canvas, pagesize=current_pagesize)
    doc = SimpleDocTemplate(pdf_bytes_io, pagesize=current_pagesize,
                            title="TI Mindmap Report", author="TI-Mindmap-GPT",
                            leftMargin=left_margin, rightMargin=right_margin,
                            topMargin=top_margin, bottomMargin=bottom_margin)
    doc.addPageTemplates([page_template])
    styles = getSampleStyleSheet()
    
    main_title_style = ParagraphStyle('MainTitle', parent=styles['h1'], fontSize=20, leading=24, spaceAfter=0.2*inch, alignment=TA_CENTER, textColor=HexColor("#2c3e50"))
    intro_style = ParagraphStyle('IntroStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=0.1*inch, textColor=HexColor("#555555"), alignment=TA_LEFT)
    link_style = ParagraphStyle('LinkStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=blue)
    section_header_style = ParagraphStyle('SectionHeader', parent=styles['h2'], fontSize=16, leading=20, spaceBefore=0.2*inch, spaceAfter=0.1*inch, textColor=HexColor("#34495e"))
    sub_section_header_style = ParagraphStyle('SubSectionHeader', parent=styles['h3'], fontSize=13, leading=16, spaceBefore=0.15*inch, spaceAfter=0.05*inch, textColor=HexColor("#34495e"))
    body_text_style = ParagraphStyle('BodyText', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=0.1*inch, alignment=TA_JUSTIFY)
    italic_content_style = ParagraphStyle('ItalicContent', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10, leading=14, spaceAfter=0.1*inch, textColor=HexColor("#4a4a4a"), alignment=TA_JUSTIFY)
    code_style = ParagraphStyle('CodeStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10, textColor=HexColor("#333333"), backColor=HexColor("#f4f4f4"), borderPadding=(2, 4), borderColor=HexColor("#dddddd"), borderWidth=0.5, leftIndent=10, rightIndent=10, spaceBefore=5, spaceAfter=5)
    ttp_list_style = ParagraphStyle('TTPListStyle', parent=styles['Normal'], fontSize=9, leading=12, leftIndent=0.25*inch, bulletIndent=0.1*inch, spaceAfter=0.05*inch)
    error_text_style = ParagraphStyle('ErrorText', parent=styles['Normal'], fontSize=9, leading=12, textColor=HexColor("#c0392b"), fontName='Helvetica-Oblique')
    table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER, textColor=black)
    table_body_style = ParagraphStyle('TableBody', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT, leading=10)

    flowables = []
    flowables.append(Paragraph("Threat Intelligence Mindmap Report", main_title_style))
    flowables.append(Paragraph("AI-powered tool for Threat Intelligence summaries, mind maps, and IOC extraction.", intro_style))
    flowables.append(Paragraph(f'App URL: <a href="https://ti-mindmap-gpt.streamlit.app/">ti-mindmap-gpt.streamlit.app</a>', link_style))
    flowables.append(Paragraph(f'GitHub: <a href="https://github.com/format81/TI-Mindmap-GPT">github.com/format81/TI-Mindmap-GPT</a>', link_style))
    flowables.append(Spacer(1, 0.2 * inch))
    flowables.append(Paragraph("SOURCE INFORMATION", section_header_style))
    flowables.append(Paragraph(f'Original Source: <a href="{url}">{url}</a>', link_style))
    flowables.append(Spacer(1, 0.1 * inch))

    flowables.append(Paragraph("WEBSITE SCREENSHOT", section_header_style))
    try:
        api_key_thumbnail = st.secrets.get("api_keys", {}).get("thumbnail")
        if not api_key_thumbnail: raise ValueError("Thumbnail API key missing.")
        screenshot_response = requests.get(f"https://api.thumbnail.ws/api/{api_key_thumbnail}/thumbnail/get?url={url}&width=1280&delay=2500", timeout=35)
        screenshot_response.raise_for_status()
        img_fitted = fit_image_to_page(BytesIO(screenshot_response.content), current_pagesize[0], current_pagesize[1])
        if img_fitted: flowables.append(img_fitted)
        else: flowables.append(Paragraph("Could not process screenshot image.", error_text_style))
    except Exception as e:
        st.warning(f"Screenshot generation/processing failed: {e}")
        flowables.append(Paragraph(f"Screenshot could not be generated or processed: {e}", error_text_style))
    flowables.append(Spacer(1, 0.1 * inch))

    if summary_content and summary_content.strip():
        flowables.append(Paragraph("AI-GENERATED SUMMARY & ANALYSIS", section_header_style))
        flowables.append(Paragraph(summary_content, italic_content_style))
        flowables.append(Spacer(1, 0.2 * inch))

    # Main Mind Map Section - Enhanced Error Handling
    if mindmap_mermaid_code: # Process only if code is provided
        flowables.append(Paragraph("MIND MAP VISUALIZATION", section_header_style))
        if not mindmap_mermaid_code.strip():
            flowables.append(Paragraph("Skipped: Provided main mind map code was empty or only whitespace.", error_text_style))
        else:
            try:
                processed_mm_code = remove_first_non_empty_line_if_mermaid(mindmap_mermaid_code)
                if not processed_mm_code.strip():
                    st.warning("Main Mind Map code became empty after processing line removal.")
                    raise ValueError("Main mind map code is empty after processing.")

                mindmap_img_data = image_from_mermaid(processed_mm_code, context="Main Mind Map")
                if mindmap_img_data:
                    img_fitted = fit_image_to_page(mindmap_img_data, current_pagesize[0], current_pagesize[1])
                    if img_fitted: flowables.append(img_fitted)
                    else:
                        st.warning("Main Mind Map image fitting failed (fit_image_to_page returned None).")
                        raise ValueError("Main mind map image fitting failed.")
                else: 
                    st.warning("image_from_mermaid returned None for Main Mind Map (check Streamlit logs for mermaid.ink issues).")
                    raise ValueError("Main mind map image data could not be fetched (check Streamlit logs for details from mermaid.ink).")
            except Exception as e:
                st.warning(f"Main Mind Map image generation/processing failed in PDF: {e}")
                flowables.append(Paragraph(f"Could not generate main mind map image: {e}", error_text_style))
                flowables.append(Paragraph("<b>Mermaid Code Used (Main Mind Map):</b>", body_text_style))
                for line in mindmap_mermaid_code.splitlines(): flowables.append(Paragraph(line if line.strip() else " ", code_style))
        flowables.append(Spacer(1, 0.2 * inch))
    
    # IOCs Section
    if iocs_data is not None:
        flowables.append(Paragraph("INDICATORS OF COMPROMISE (IOCs)", section_header_style))
        # ... (rest of IOCs table logic remains the same) ...
        try:
            data_for_table = []
            if isinstance(iocs_data, pd.DataFrame):
                if not iocs_data.empty:
                    data_for_table.append([Paragraph(str(col), table_header_style) for col in iocs_data.columns]) 
                    for index, row in iocs_data.iterrows():
                        data_for_table.append([Paragraph(str(item), table_body_style) for item in row])
                else:
                    flowables.append(Paragraph("No IOCs found or provided.", body_text_style))
            elif isinstance(iocs_data, list) and iocs_data: 
                header_row = [Paragraph(str(cell), table_header_style) for cell in iocs_data[0]]
                body_rows = [[Paragraph(str(cell), table_body_style) for cell in row] for row in iocs_data[1:]]
                data_for_table = [header_row] + body_rows
            
            if data_for_table:
                num_cols = len(data_for_table[0])
                col_widths = [frame_width / num_cols] * num_cols if num_cols > 0 else None
                ioc_table = Table(data_for_table, repeatRows=1, colWidths=col_widths)
                ts = TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, grey), ('BACKGROUND', (0,0), (-1,0), lightgrey), 
                    ('TEXTCOLOR', (0,0), (-1,0), black), ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), 
                    ('FONTSIZE', (0,0), (-1,0), 9), ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 8),
                    ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4),
                ])
                ioc_table.setStyle(ts)
                flowables.append(ioc_table)
            elif not (isinstance(iocs_data, pd.DataFrame) and not iocs_data.empty): 
                 flowables.append(Paragraph("No IOCs data available or data is empty.", body_text_style))
        except Exception as e:
            st.warning(f"Error processing IOCs for PDF: {e}")
            flowables.append(Paragraph(f"Could not display IOCs: {e}", error_text_style))
        flowables.append(Spacer(1, 0.2 * inch))

    # TTPs Sections
    if ttps_overview_data or attack_path_data or mermaid_timeline_code:
        flowables.append(Paragraph("TACTICS, TECHNIQUES, AND PROCEDURES (TTPs)", section_header_style))
        # TTPs Overview Table
        if ttps_overview_data and ttps_overview_data.strip():
            flowables.append(Paragraph("TTPs Overview", sub_section_header_style))
            # ... (rest of TTPs overview table logic remains the same) ...
            parsed_ttp_table_data = parse_markdown_table(ttps_overview_data)
            if parsed_ttp_table_data and len(parsed_ttp_table_data) > 0:
                styled_ttp_table_data = []
                try:
                    styled_ttp_table_data.append([Paragraph(str(cell), table_header_style) for cell in parsed_ttp_table_data[0]])
                    for row in parsed_ttp_table_data[1:]:
                        styled_ttp_table_data.append([Paragraph(str(cell), table_body_style) for cell in row])
                    if styled_ttp_table_data:
                        num_cols_ttp = len(styled_ttp_table_data[0])
                        col_widths_ttp = [frame_width / num_cols_ttp] * num_cols_ttp if num_cols_ttp > 0 else None
                        ttp_table_obj = Table(styled_ttp_table_data, repeatRows=1, colWidths=col_widths_ttp)
                        ttp_ts = TableStyle([
                            ('GRID', (0,0), (-1,-1), 0.5, grey), ('BACKGROUND', (0,0), (-1,0), lightgrey),
                            ('TEXTCOLOR', (0,0), (-1,0), black), ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,0), 9), ('BOTTOMPADDING', (0,0), (-1,0), 6),
                            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 8),
                            ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4),
                        ])
                        ttp_table_obj.setStyle(ttp_ts)
                        flowables.append(ttp_table_obj)
                    else:
                        flowables.append(Paragraph("Could not parse TTPs overview table data.", error_text_style))
                except Exception as e_table_render:
                    st.warning(f"Error rendering TTPs overview table: {e_table_render}")
                    flowables.append(Paragraph(f"Error rendering TTPs table: {e_table_render}. Displaying as text:", error_text_style))
                    for line in ttps_overview_data.splitlines(): flowables.append(Paragraph(line, body_text_style))
            else: 
                flowables.append(Paragraph("TTPs overview data is not in a recognized table format. Displaying as text:", body_text_style))
                for line in ttps_overview_data.splitlines(): flowables.append(Paragraph(line, body_text_style))
            flowables.append(Spacer(1, 0.1 * inch))

        # TTPs Ordered by Execution Time
        if attack_path_data and attack_path_data.strip():
            flowables.append(Paragraph("TTPs Ordered by Execution Time", sub_section_header_style))
            # ... (rest of attack_path_data logic remains the same) ...
            for line in attack_path_data.splitlines():
                if line.strip():
                    flowables.append(Paragraph(f"•  {line.strip()}", ttp_list_style))
            flowables.append(Spacer(1, 0.1 * inch))

        # TTPs Graphic Timeline - Enhanced Error Handling
        if mermaid_timeline_code: # Process only if code is provided
            flowables.append(Paragraph("TTPs Graphic Timeline", sub_section_header_style))
            if not mermaid_timeline_code.strip():
                flowables.append(Paragraph("Skipped: Provided TTP timeline code was empty or only whitespace.", error_text_style))
            else:
                try:
                    processed_ttp_timeline_code = remove_first_non_empty_line_if_mermaid(mermaid_timeline_code)
                    if not processed_ttp_timeline_code.strip():
                        st.warning("TTP timeline code became empty after processing line removal.")
                        raise ValueError("TTP timeline code is empty after processing.")

                    ttp_timeline_img_data = image_from_mermaid(processed_ttp_timeline_code, context="TTP Timeline")
                    if ttp_timeline_img_data:
                        img_fitted = fit_image_to_page(ttp_timeline_img_data, current_pagesize[0], current_pagesize[1])
                        if img_fitted: flowables.append(img_fitted)
                        else:
                            st.warning("TTP Timeline image fitting failed (fit_image_to_page returned None).")
                            raise ValueError("TTP timeline image fitting failed.")
                    else:
                        st.warning("image_from_mermaid returned None for TTP Timeline (check Streamlit logs for mermaid.ink issues).")
                        raise ValueError("TTP timeline image data could not be fetched (check Streamlit logs for details from mermaid.ink).")
                except Exception as e:
                    st.warning(f"TTP Timeline image generation/processing failed in PDF: {e}")
                    flowables.append(Paragraph(f"Could not generate TTP timeline image: {e}", error_text_style))
                    flowables.append(Paragraph("<b>Mermaid Code Used (TTP Timeline):</b>", body_text_style))
                    for line in mermaid_timeline_code.splitlines(): flowables.append(Paragraph(line if line.strip() else " ", code_style))
        flowables.append(Spacer(1, 0.2 * inch))

    # 5 Whats Section
    if five_whats_data and five_whats_data.strip():
        flowables.append(Paragraph("THREAT SCOPE REPORT (THE 5 WHATS)", section_header_style))
        # ... (rest of 5 whats logic remains the same) ...
        for line in five_whats_data.splitlines():
            if line.startswith("## "): flowables.append(Paragraph(line[3:], sub_section_header_style))
            elif line.startswith("# "): flowables.append(Paragraph(line[2:], section_header_style))
            elif line.startswith("**") and line.endswith("**") and len(line) > 4 : flowables.append(Paragraph(f"<b>{line[2:-2]}</b>", body_text_style))
            elif line.startswith("__") and line.endswith("__") and len(line) > 4 : flowables.append(Paragraph(f"<b>{line[2:-2]}</b>", body_text_style))
            else: flowables.append(Paragraph(line, body_text_style))
        flowables.append(Spacer(1, 0.2 * inch))
    
    try:
        doc.build(flowables)
        pdf_bytes = pdf_bytes_io.getvalue()
        pdf_bytes_io.close()
        return pdf_bytes
    except Exception as e:
        st.error(f"CRITICAL: Failed to build PDF document: {e}")
        pdf_bytes_io.close()
        return None

# --- Example usage (for testing) ---
if __name__ == '__main__':
    # ... (Example usage block remains the same as previous version) ...
    class MockSecrets(dict):
        def get(self, key, default=None): return super().get(key, default if default is not None else {})

    if not hasattr(st, 'secrets'):
        st.secrets = MockSecrets(api_keys={"thumbnail": "YOUR_THUMBNAIL_API_KEY_HERE_OR_MOCK"})
        def mock_st_method(message): print(f"ST_MOCK: {message}")
        st.error = mock_st_method; st.warning = mock_st_method; st.info = mock_st_method; st.json = mock_st_method

    dummy_url = "https://www.examplethreatreport.com/report123"
    dummy_summary = "This is a detailed AI-generated summary..."
    dummy_mindmap_mermaid = "mindmap\n  root((Main Threat))\n    (Actor A)\n    (Victim B)"
    
    dummy_iocs_df = pd.DataFrame([
        {"Type": "IPv4", "Value": "192.168.1.100", "Description": "C2 Server"},
        {"Type": "Domain", "Value": "malicious-domain.com", "Description": "Phishing Site"},
        {"Type": "File Hash (SHA256)", "Value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "Description": "Malware Sample"},
    ])
    
    dummy_ttps_overview_markdown = """
| Tactic         | Technique ID | Technique Name        | Description                                  |
|----------------|--------------|-----------------------|----------------------------------------------|
| Initial Access | T1566        | Phishing              | Emails with malicious links or attachments.  |
| Execution      | T1059.001    | PowerShell            | Execution of PowerShell scripts.             |
| Persistence    | T1053.005    | Scheduled Task/Job    | Creating scheduled tasks for persistence.    |
"""
    dummy_ttps_overview_text_fallback = "The threat actor utilized spear-phishing emails for initial access.\nPost-compromise, PowerShell was used for execution and persistence was achieved via scheduled tasks."

    dummy_attack_path = "1. Spear-phishing email delivered.\n2. User clicks malicious link.\n3. PowerShell payload executed.\n4. Scheduled task created for persistence."
    dummy_ttp_timeline_mermaid = "timeline\n  title TTP Execution Timeline\n  section Initial Access\n    Phishing : Step 1\n  section Execution\n    PowerShell : Step 2\n  section Persistence\n    Scheduled Task : Step 3"
    dummy_5_whats = """
## What happened?
A security incident involving data exfiltration.
## What was the impact?
Sensitive customer data was compromised.
## What was the cause?
A phishing attack that led to credential theft.
## What are we doing about it?
Implementing MFA, user training, and enhanced email filtering.
## What did we learn?
The importance of rapid detection and response, and continuous security awareness.
"""

    print("Generating Portrait PDF with all sections (Markdown TTP Table)...")
    pdf_data = create_pdf_bytes(
        dummy_url, dummy_summary, dummy_mindmap_mermaid,
        iocs_data=dummy_iocs_df, 
        ttps_overview_data=dummy_ttps_overview_markdown, 
        attack_path_data=dummy_attack_path,
        mermaid_timeline_code=dummy_ttp_timeline_mermaid,
        five_whats_data=dummy_5_whats,
        orientation='portrait'
    )
    if pdf_data:
        with open("ti_mindmap_full_report_portrait_md_ttp.pdf", "wb") as f: f.write(pdf_data)
        print("Portrait PDF 'ti_mindmap_full_report_portrait_md_ttp.pdf' generated.")
    else: print("Failed to generate portrait PDF with Markdown TTP table.")
    
    print("\nGenerating Portrait PDF with all sections (Plain Text TTP Fallback)...")
    pdf_data_text_ttp = create_pdf_bytes(
        dummy_url, dummy_summary, dummy_mindmap_mermaid,
        iocs_data=dummy_iocs_df, 
        ttps_overview_data=dummy_ttps_overview_text_fallback, 
        attack_path_data=dummy_attack_path,
        mermaid_timeline_code=dummy_ttp_timeline_mermaid,
        five_whats_data=dummy_5_whats,
        orientation='portrait'
    )
    if pdf_data_text_ttp:
        with open("ti_mindmap_full_report_portrait_txt_ttp.pdf", "wb") as f: f.write(pdf_data_text_ttp)
        print("Portrait PDF 'ti_mindmap_full_report_portrait_txt_ttp.pdf' generated.")
    else: print("Failed to generate portrait PDF with plain text TTP.")


    print("\nGenerating Landscape PDF with all sections (Markdown TTP Table)...")
    pdf_data_land = create_pdf_bytes(
        dummy_url, dummy_summary, dummy_mindmap_mermaid,
        iocs_data=dummy_iocs_df, 
        ttps_overview_data=dummy_ttps_overview_markdown,
        attack_path_data=dummy_attack_path,
        mermaid_timeline_code=dummy_ttp_timeline_mermaid,
        five_whats_data=dummy_5_whats,
        orientation='landscape'
    )
    if pdf_data_land:
        with open("ti_mindmap_full_report_landscape_md_ttp.pdf", "wb") as f: f.write(pdf_data_land)
        print("Landscape PDF 'ti_mindmap_full_report_landscape_md_ttp.pdf' generated.")
    else: print("Failed to generate landscape PDF.")