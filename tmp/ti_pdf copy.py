import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import base64
import streamlit as st

from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader


mermaid_code_example = """
mermaid
mindmap
root(Midnight Blizzard Attack Chain)
  (Initial Access)
    (Password spray compromised test account)
    (Used error code 50126 for detection)
    (Monitored distinct user-IP combinations)
    (Detection of authentication spikes)
  (Credential Access)
    (Compromised legacy OAuth application with elevated access)
    (Added new credentials to application registration)
    (Monitored "Update application" events)
    (Authentications as Service Principal detected)
  (Privilege Escalation)
    (Escalation based on high-level permissions)
    (Monitored critical roles and sensitive API permissions)
    (Examined 'Add member to role' events)
    (Focused on crucial roles and permissions adjustments)
  (Persistence)
    (Creation of additional malicious OAuth applications)
    (Monitored 'Add Application' and 'Add Service Principal' events)
    (Tracked multiple applications created quickly)
    (Differentiated creations by users or service principals)
  (Collection)
    (Authenticated to Microsoft Exchange Online)
    (Targeted Microsoft corporate email accounts)
    (Used 'Mailitemsaccessed' event for tracking)
    (Identified OAuth applications accessing mailboxes)
"""

def image_from_mermaid(graph):
    # Convert the Mermaid code to an image
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
  
    # Open the image with PIL
    return BytesIO(requests.get("https://mermaid.ink/img/" + base64_string).content)


def remove_first_non_empty_line_if_mermaid(mermaid_code):
    lines = mermaid_code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "mermaid":
            lines.pop(i)  # Remove the line
            break  # Exit the loop after removing the first matching line
    return '\n'.join(lines)

def download_image(url):
    response = requests.get(url)
    return BytesIO(response.content)

def fit_image_to_page(image_data):
    # Convert the BytesIO object to a reportlab.platypus.Image object
    img = ImageReader(image_data)
    img_width, img_height = img.getSize()
    aspect_ratio = img_width / img_height

    # Calculate the aspect ratio of the A4 page
    page_width, page_height = A4
    page_aspect_ratio = page_width / page_height

    # Adjust the image dimensions to fit the page
    if aspect_ratio > page_aspect_ratio:
        # Image is wider than the page, adjust width
        new_width = page_width
        new_height = new_width / aspect_ratio
    else:
        # Image is taller than the page, adjust height
        new_height = page_height
        new_width = new_height * aspect_ratio

    # Create a new Image object with the adjusted dimensions
    img = Image(image_data, width=new_width, height=new_height)
    return img

def create_pdf_bytes(url, content, mermaid_code, attackpath=None):
    # Create a BytesIO object to hold the PDF data
    pdf_bytes_io = BytesIO()

    doc = SimpleDocTemplate(pdf_bytes_io, pagesize=A4)
    styles = getSampleStyleSheet()
    header1_style = styles["Heading1"]
    header2_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Add content to the PDF
    flowables = []
    flowables.append(Spacer(1, 0.1 * inch))  # Add some space after header
    flowables.append(Paragraph("TI MINDMAP", header1_style))
    flowables.append(Paragraph("TI MINDMAP, an AI-powered tool designed to help producing Threat Intelligence summaries, Mindmap and IOCs extraction and more.", normal_style))
    flowables.append(Paragraph("APP url: <link href='https://ti-mindmap-gpt.streamlit.app/'>https://ti-mindmap-gpt.streamlit.app/</link>", normal_style))
    flowables.append(Paragraph("GitHub: <link href='https://github.com/format81/TI-Mindmap-GPT'>https://github.com/format81/TI-Mindmap-GPT</link>", normal_style))
    #flowables.append(PageBreak())  # Move to the next page
    flowables.append(Spacer(1, 0.1 * inch))  # Add some space after header
    # Page 2: Agenda
    flowables.append(Paragraph("REPORT", header1_style))
    flowables.append(Paragraph(f"Original source: <link href='{url}'>{url}</link>", normal_style))  # Adding original source link
    
    # Make a request to get the screenshot image
    api_key_thumbnail = st.secrets["api_keys"]["thumbnail"]
    screenshot = requests.get(f"https://api.thumbnail.ws/api/{api_key_thumbnail}/thumbnail/get?url={url}&width=640&delay=1500")

    # Debugging: Print the content of the screenshot
    print("Screenshot content:", screenshot.content)

    # If the request is successful, add the image to the PDF
    if screenshot.status_code == 200:
        screenshot_data_pdf = screenshot.content  # Store the screenshot image data
        st.write("Screenshot added to PDF successfully")

        # Add the screenshot image to the PDF
        flowables.append(Paragraph("SCREENSHOT", header1_style))
        img = fit_image_to_page(BytesIO(screenshot_data_pdf))
        flowables.append(img)  # Add the image to the list of flowables
    else:
        st.write(f"Failed to get the image. Status code: {screenshot.status_code}")
        screenshot_data_pdf = None
    
    italic_style = ParagraphStyle(
        name='ItalicText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',  # Use a font that supports italic
        fontSize=12,
        leading=14
    )
    
    # Assuming image_from_mermaid returns a BytesIO object
    image_data = image_from_mermaid(remove_first_non_empty_line_if_mermaid(mermaid_code))
    img = fit_image_to_page(image_data)
    flowables.append(img)
    flowables.append(Spacer(1, 0.1 * inch))  # Add some space after header
    flowables.append(Paragraph(content, italic_style)) 
    # Split the attackpath into a list of lines  
    #attackpath_lines = attackpath.split('\n')  
    if attackpath:  # Check if attackpath is not None
        attackpath_lines = attackpath.split('\n')  
    else:
        attackpath_lines = []
    # Add attackpath to the PDF  
    flowables.append(Paragraph("TTPs ordered by execution time", header1_style))  
    for line in attackpath_lines:  
        flowables.append(Paragraph(line, normal_style)) 

    doc.build(flowables)

     # Get the PDF bytes
    pdf_bytes = pdf_bytes_io.getvalue()

    # Close the BytesIO object
    pdf_bytes_io.close()

    return pdf_bytes