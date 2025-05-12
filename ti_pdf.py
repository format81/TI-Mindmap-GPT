import requests
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageTemplate, Frame, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import blue, grey, black, HexColor, beige, lightgrey, darkblue, dimgrey
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
    """
    if not graph or not graph.strip():
        st.warning(f"Mermaid graph data for {context} is empty. Cannot generate image.")
        return None
        
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    mermaid_ink_url = f"https://mermaid.ink/img/{base64_string}"
    
    try:
        response = requests.get(mermaid_ink_url, timeout=30)
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.exceptions.Timeout:
        st.error(f"Mermaid image generation for {context} timed out contacting mermaid.ink.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Mermaid image generation for {context} failed. HTTP status: {e.response.status_code}. URL: {mermaid_ink_url}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Mermaid image generation request for {context} failed: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Mermaid image generation for {context}: {e}")
        return None

def remove_first_non_empty_line_if_mermaid(mermaid_code):
    if not mermaid_code: return ""
    lines = mermaid_code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "mermaid":
            lines.pop(i)
            break
    return '\n'.join(lines)

def fit_image_to_page(image_data_bytesio, page_width, page_height, margin=0.75*inch):
    if not image_data_bytesio: return None
    try:
        image_data_bytesio.seek(0)
        img_reader = ImageReader(image_data_bytesio)
    except Exception as e:
        st.error(f"Error reading image data for fitting: {e}.")
        return None
    img_width, img_height = img_reader.getSize()
    if img_height == 0 or img_width == 0: return None
    aspect_ratio = img_width / img_height
    available_width = page_width - (2 * margin)
    available_height = page_height - (2 * margin)
    if available_width <= 0 or available_height <= 0: return None
    if aspect_ratio == 0: return None

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

    if not table_lines or len(table_lines) < 2: # Need at least a header and a separator or data row
        # Check if it's just a single line table without separator (less common but possible for simple LLM outputs)
        if len(table_lines) == 1: 
             cells_str = [cell.strip() for cell in table_lines[0][1:-1].split('|')]
             if cells_str and any(c for c in cells_str): # If there are any non-empty cells
                 return [cells_str] # Return as a single row table (header only)
        return None


    separator_index = -1
    for i, line in enumerate(table_lines):
        # A separator line consists of '|', '-', ':'
        if all(c in '|-:' for c in line):
            cells = [cell.strip() for cell in line[1:-1].split('|')]
            if all(all(sc in '-:' for sc in cell) and cell for cell in cells): # Ensure cells are not empty and contain only - or :
                separator_index = i
                break
    
    data = []
    header_processed = False
    num_cols = 0

    for i, line in enumerate(table_lines):
        if i == separator_index: # Skip the separator line itself
            continue

        cells_str = [cell.strip() for cell in line[1:-1].split('|')]

        if not header_processed: # Assume first valid line is header
            num_cols = len(cells_str)
            if num_cols == 0: return None # Invalid table
            data.append(cells_str)
            header_processed = True
        elif len(cells_str) == num_cols: # Ensure data rows have same number of columns as header
            data.append(cells_str)
        # else: # Mismatched column count - for now, we are strict.
            # Consider adding logging or more lenient parsing if needed.

    if not data or not data[0]: # No header or data found
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
    
    content_frame = Frame(left_margin, bottom_margin, frame_width, current_pagesize[1] - top_margin - bottom_margin, id='content_frame')
    page_template = PageTemplate(id='main_template', frames=[content_frame], onPage=footer_canvas, pagesize=current_pagesize)

    doc = SimpleDocTemplate(pdf_bytes_io, pagesize=current_pagesize,
                            title="TI Mindmap Report", author="TI-Mindmap-GPT",
                            leftMargin=left_margin, rightMargin=right_margin,
                            topMargin=top_margin, bottomMargin=bottom_margin)
    doc.addPageTemplates([page_template])

    styles = getSampleStyleSheet()
    
    # --- Define Diverse Paragraph Styles ---
    main_title_style = ParagraphStyle('MainTitle', parent=styles['h1'], fontSize=20, leading=24, spaceAfter=0.2*inch, alignment=TA_CENTER, textColor=HexColor("#2c3e50"))
    intro_style = ParagraphStyle('IntroStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=0.1*inch, textColor=HexColor("#555555"), alignment=TA_LEFT)
    link_style = ParagraphStyle('LinkStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=blue)
    section_header_style = ParagraphStyle('SectionHeader', parent=styles['h2'], fontSize=16, leading=20, spaceBefore=0.2*inch, spaceAfter=0.1*inch, textColor=HexColor("#34495e"), keepWithNext=1)
    sub_section_header_style = ParagraphStyle('SubSectionHeader', parent=styles['h3'], fontSize=13, leading=16, spaceBefore=0.15*inch, spaceAfter=0.05*inch, textColor=HexColor("#34495e"), keepWithNext=1)
    body_text_style = ParagraphStyle('BodyText', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=0.1*inch, alignment=TA_JUSTIFY)
    italic_content_style = ParagraphStyle('ItalicContent', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10, leading=14, spaceAfter=0.1*inch, textColor=HexColor("#4a4a4a"), alignment=TA_JUSTIFY)
    code_style = ParagraphStyle('CodeStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10, textColor=HexColor("#333333"), backColor=HexColor("#f4f4f4"), borderPadding=(2, 4), borderColor=HexColor("#dddddd"), borderWidth=0.5, leftIndent=10, rightIndent=10, spaceBefore=5, spaceAfter=5)
    
    ttp_execution_item_style = ParagraphStyle('TTPExecutionItem', parent=styles['Normal'], fontSize=9, leading=12, spaceBefore=0.05*inch, spaceAfter=0.05*inch, leftIndent=0.2*inch, bulletIndent=0)
    ttp_execution_tactic_style = ParagraphStyle('TTPExecutionTactic', parent=ttp_execution_item_style, fontName='Helvetica-Bold', textColor=darkblue)
    ttp_execution_technique_style = ParagraphStyle('TTPExecutionTechnique', parent=ttp_execution_item_style, leftIndent=0.4*inch)

    error_text_style = ParagraphStyle('ErrorText', parent=styles['Normal'], fontSize=9, leading=12, textColor=HexColor("#c0392b"), fontName='Helvetica-Oblique')
    table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER, textColor=black)
    table_body_style = ParagraphStyle('TableBody', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT, leading=10)
    
    # Styles for 5 Whats table (can be same as other tables or specialized)
    five_whats_table_header_style = ParagraphStyle('FiveWhatsTableHeader', parent=table_header_style, alignment=TA_LEFT) # Left align header for 5W
    five_whats_table_body_style = ParagraphStyle('FiveWhatsTableBody', parent=table_body_style)


    flowables = []
    
    # --- PDF Content Sections ---
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

    if mindmap_mermaid_code: 
        flowables.append(Paragraph("MIND MAP VISUALIZATION", section_header_style))
        if not mindmap_mermaid_code.strip():
            flowables.append(Paragraph("Skipped: Provided main mind map code was empty or only whitespace.", error_text_style))
        else:
            try:
                processed_mm_code = remove_first_non_empty_line_if_mermaid(mindmap_mermaid_code)
                if not processed_mm_code.strip(): raise ValueError("Main mind map code is empty after processing.")
                mindmap_img_data = image_from_mermaid(processed_mm_code, context="Main Mind Map")
                if mindmap_img_data:
                    img_fitted = fit_image_to_page(mindmap_img_data, current_pagesize[0], current_pagesize[1])
                    if img_fitted: flowables.append(img_fitted)
                    else: raise ValueError("Main mind map image fitting failed.")
                else: raise ValueError("Main mind map image data could not be fetched (check Streamlit logs for details from mermaid.ink).")
            except Exception as e:
                st.warning(f"Main Mind Map image generation/processing failed in PDF: {e}")
                flowables.append(Paragraph(f"Could not generate main mind map image: {e}", error_text_style))
                flowables.append(Paragraph("<b>Mermaid Code Used (Main Mind Map):</b>", body_text_style))
                for line in mindmap_mermaid_code.splitlines(): flowables.append(Paragraph(line if line.strip() else " ", code_style))
        flowables.append(Spacer(1, 0.2 * inch))
    
    if iocs_data is not None:
        flowables.append(Paragraph("INDICATORS OF COMPROMISE (IOCs)", section_header_style))
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
        
        if ttps_overview_data and ttps_overview_data.strip():
            flowables.append(Paragraph("TTPs Overview", sub_section_header_style))
            parsed_ttp_table_data = parse_markdown_table(ttps_overview_data)
            if parsed_ttp_table_data and len(parsed_ttp_table_data) > 0:
                styled_ttp_table_data = []
                try:
                    # Use table_header_style for the first row (headers)
                    styled_ttp_table_data.append([Paragraph(str(cell), table_header_style) for cell in parsed_ttp_table_data[0]])
                    # Use table_body_style for subsequent rows (data)
                    for row in parsed_ttp_table_data[1:]:
                        styled_ttp_table_data.append([Paragraph(str(cell), table_body_style) for cell in row])
                    
                    if styled_ttp_table_data:
                        num_cols_ttp = len(styled_ttp_table_data[0])
                        # Auto-adjust column widths based on content, or distribute evenly
                        # For simplicity, distributing evenly:
                        col_widths_ttp = [frame_width / num_cols_ttp] * num_cols_ttp if num_cols_ttp > 0 else None
                        
                        ttp_table_obj = Table(styled_ttp_table_data, repeatRows=1, colWidths=col_widths_ttp)
                        ttp_ts = TableStyle([
                            ('GRID', (0,0), (-1,-1), 0.5, grey),
                            ('BACKGROUND', (0,0), (-1,0), lightgrey), # Header background
                            ('TEXTCOLOR', (0,0), (-1,0), black),      # Header text color
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),        # Left align all cells by default
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Header font
                            ('FONTSIZE', (0,0), (-1,0), 9),                # Header font size
                            ('BOTTOMPADDING', (0,0), (-1,0), 6),           # Header padding
                            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),     # Body font
                            ('FONTSIZE', (0,1), (-1,-1), 8),                # Body font size
                            ('TOPPADDING', (0,1), (-1,-1), 4),
                            ('BOTTOMPADDING', (0,1), (-1,-1), 4),
                        ])
                        ttp_table_obj.setStyle(ttp_ts)
                        flowables.append(ttp_table_obj)
                    else: # Should not happen if parsed_ttp_table_data is valid and non-empty
                        flowables.append(Paragraph("Could not prepare TTPs overview table data for styling.", error_text_style))
                except Exception as e_table_render:
                    st.warning(f"Error rendering TTPs overview table: {e_table_render}")
                    flowables.append(Paragraph(f"Error rendering TTPs table: {e_table_render}. Displaying as text:", error_text_style))
                    for line in ttps_overview_data.splitlines(): flowables.append(Paragraph(line, body_text_style))
            else: 
                flowables.append(Paragraph("TTPs overview data is not in a recognized table format or is empty. Displaying as text:", body_text_style))
                for line in ttps_overview_data.splitlines():
                    if line.strip(): flowables.append(Paragraph(line, body_text_style))
            flowables.append(Spacer(1, 0.1 * inch))

        if attack_path_data and attack_path_data.strip():
            flowables.append(Paragraph("TTPs Ordered by Execution Time", sub_section_header_style))
            for i, line in enumerate(attack_path_data.splitlines()):
                line_stripped = line.strip()
                if line_stripped:
                    parts = re.split(r'\s*[:—-]\s*', line_stripped, 1) 
                    if len(parts) > 1:
                        flowables.append(Paragraph(f"<b>{parts[0].strip()}:</b> {parts[1].strip()}", ttp_execution_item_style))
                    else:
                        flowables.append(Paragraph(line_stripped, ttp_execution_item_style))
            flowables.append(Spacer(1, 0.1 * inch))

        if mermaid_timeline_code: 
            flowables.append(Paragraph("TTPs Graphic Timeline", sub_section_header_style))
            if not mermaid_timeline_code.strip():
                flowables.append(Paragraph("Skipped: Provided TTP timeline code was empty or only whitespace.", error_text_style))
            else:
                try:
                    processed_ttp_timeline_code = remove_first_non_empty_line_if_mermaid(mermaid_timeline_code)
                    if not processed_ttp_timeline_code.strip(): raise ValueError("TTP timeline code is empty after processing.")
                    ttp_timeline_img_data = image_from_mermaid(processed_ttp_timeline_code, context="TTP Timeline")
                    if ttp_timeline_img_data:
                        img_fitted = fit_image_to_page(ttp_timeline_img_data, current_pagesize[0], current_pagesize[1])
                        if img_fitted: flowables.append(img_fitted)
                        else: raise ValueError("TTP timeline image fitting failed.")
                    else: raise ValueError("TTP timeline image data could not be fetched (check Streamlit logs for details from mermaid.ink).")
                except Exception as e:
                    st.warning(f"TTP Timeline image generation/processing failed in PDF: {e}")
                    flowables.append(Paragraph(f"Could not generate TTP timeline image: {e}", error_text_style))
                    flowables.append(Paragraph("<b>Mermaid Code Used (TTP Timeline):</b>", body_text_style))
                    for line in mermaid_timeline_code.splitlines(): flowables.append(Paragraph(line if line.strip() else " ", code_style))
        flowables.append(Spacer(1, 0.2 * inch))

    # Threat Scope Report (5 Whats) Section - Corrected to use parse_markdown_table
    if five_whats_data and five_whats_data.strip():
        flowables.append(Paragraph("THREAT SCOPE REPORT (THE 5 WHATS)", section_header_style))
        parsed_5w_table_data = parse_markdown_table(five_whats_data) # Use the markdown table parser

        if parsed_5w_table_data and len(parsed_5w_table_data) > 0:
            styled_5w_table_data = []
            try:
                # Assume first row is header, rest is data.
                # If the 5W table has a specific structure (e.g., Question | Answer), adjust styles.
                # For a generic table, use standard table styles.
                styled_5w_table_data.append([Paragraph(str(cell), five_whats_table_header_style) for cell in parsed_5w_table_data[0]])
                for row in parsed_5w_table_data[1:]:
                    styled_5w_table_data.append([Paragraph(str(cell), five_whats_table_body_style) for cell in row])
                
                if styled_5w_table_data:
                    num_cols_5w = len(styled_5w_table_data[0])
                    # Example: Make first column narrower if it's typically questions
                    if num_cols_5w == 2: # Common for Q&A
                        col_widths_5w = [frame_width * 0.3, frame_width * 0.68]
                    else: # Distribute evenly
                        col_widths_5w = [frame_width / num_cols_5w] * num_cols_5w if num_cols_5w > 0 else None
                    
                    five_whats_table_obj = Table(styled_5w_table_data, repeatRows=1, colWidths=col_widths_5w)
                    five_whats_ts = TableStyle([
                        ('GRID', (0,0), (-1,-1), 0.5, grey),
                        ('BACKGROUND', (0,0), (-1,0), lightgrey),
                        ('TEXTCOLOR', (0,0), (-1,0), black),
                        ('ALIGN', (0,0), (-1,0), 'LEFT'), # Header left aligned for 5W
                        ('ALIGN', (0,1), (-1,-1), 'LEFT'), # Body left aligned
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), # Top align content in cells
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,0), 10), # Slightly larger header for 5W
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,1), (-1,-1), 9), # Slightly larger body for 5W
                        ('TOPPADDING', (0,1), (-1,-1), 4),
                        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
                        ('SPAN', (0,0), (0,0)) if num_cols_5w > 1 else None, # Example: Span first header cell if it's a title
                    ])
                    # Remove None from styles if num_cols_5w <=1 to avoid error
                    if num_cols_5w <= 1:
                        five_whats_ts.commands = [cmd for cmd in five_whats_ts.commands if cmd[0] != 'SPAN']

                    five_whats_table_obj.setStyle(five_whats_ts)
                    flowables.append(five_whats_table_obj)
                else:
                    flowables.append(Paragraph("Could not parse '5 Whats' report table data.", error_text_style))
            except Exception as e_5w_table_render:
                st.warning(f"Error rendering '5 Whats' report table: {e_5w_table_render}")
                flowables.append(Paragraph(f"Error rendering '5 Whats' table: {e_5w_table_render}. Displaying as text:", error_text_style))
                for line in five_whats_data.splitlines(): 
                    if line.strip(): flowables.append(Paragraph(line, body_text_style))
        else: 
            flowables.append(Paragraph("'5 Whats' report data is not in a recognized table format or is empty. Displaying as text:", body_text_style))
            for line in five_whats_data.splitlines():
                if line.strip(): flowables.append(Paragraph(line, body_text_style))
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
    ])
    
    dummy_ttps_overview_markdown = """
| Tactic         | Technique ID | Technique Name        | Description                                  |
|----------------|--------------|-----------------------|----------------------------------------------|
| Initial Access | T1566        | Phishing              | Emails with malicious links or attachments.  |
| Execution      | T1059.001    | PowerShell            | Execution of PowerShell scripts.             |
"""
    dummy_attack_path = ("Initial Access: Phishing (T1566) - Malicious email sent to target.\n"
                         "Execution: PowerShell (T1059.001) - Payload executed via PowerShell.\n"
                         "Persistence: Scheduled Task (T1053.005) - Task created for autorun.")

    dummy_ttp_timeline_mermaid = "timeline\n  title TTP Execution Timeline\n  section Initial Access\n    Phishing : Step 1\n  section Execution\n    PowerShell : Step 2"
    
    dummy_5_whats_table_md = """
| Question                                       | Answer                                                                                                |
|------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| What was the primary objective?                | Data exfiltration of sensitive financial documents and intellectual property.                         |
| What initial access vector was utilized?       | A spear-phishing email containing a malicious macro-enabled document.                                 |
| How did the actor move laterally?              | Exploiting CVE-2023-XXXX on an internal web server and using stolen credentials.                      |
| What tools were observed?                      | Custom PowerShell scripts, Cobalt Strike for C2, and Mimikatz for credential harvesting.              |
| What was the overall impact?                   | Significant data loss, operational disruption for 48 hours, and reputational damage.                  |
"""
    dummy_5_whats_plain_fallback = "This is a block of text for the 5 whats if parsing fails. It contains important details that should be displayed clearly, even without Q&A structure."


    print("Generating Portrait PDF with Markdown Table for 5 Whats and enhanced TTP list...")
    pdf_data = create_pdf_bytes(
        dummy_url, dummy_summary, dummy_mindmap_mermaid,
        iocs_data=dummy_iocs_df, 
        ttps_overview_data=dummy_ttps_overview_markdown, 
        attack_path_data=dummy_attack_path,
        mermaid_timeline_code=dummy_ttp_timeline_mermaid,
        five_whats_data=dummy_5_whats_table_md, # Test with Markdown table style for 5W
        orientation='portrait'
    )
    if pdf_data:
        with open("ti_mindmap_report_v4_md_5w.pdf", "wb") as f: f.write(pdf_data)
        print("PDF 'ti_mindmap_report_v4_md_5w.pdf' generated.")
    else: print("Failed to generate PDF with Markdown Table 5 Whats.")

    print("\nGenerating PDF with Plain Text 5 Whats (fallback)...")
    pdf_data_plain_5w = create_pdf_bytes(
        dummy_url, dummy_summary, dummy_mindmap_mermaid,
        iocs_data=dummy_iocs_df, 
        ttps_overview_data=dummy_ttps_overview_markdown, 
        attack_path_data=dummy_attack_path,
        mermaid_timeline_code=dummy_ttp_timeline_mermaid,
        five_whats_data=dummy_5_whats_plain_fallback, # Test with plain text style
        orientation='portrait'
    )
    if pdf_data_plain_5w:
        with open("ti_mindmap_report_v4_plain_5w.pdf", "wb") as f: f.write(pdf_data_plain_5w)
        print("PDF 'ti_mindmap_report_v4_plain_5w.pdf' generated.")
    else: print("Failed to generate PDF with plain text 5 Whats.")