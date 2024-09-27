import streamlit as st
import base64

def markmap_to_html_with_png(markmap_code):
    # Escape any backticks in the markmap_code
    markmap_code_escaped = markmap_code.replace("`", "\\`")
    
    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Markmap Mindmap</title>
        <script src="https://cdn.jsdelivr.net/npm/markmap-view"></script>
        <script src="https://cdn.jsdelivr.net/npm/html-to-image"></script>
    </head>
    <body>
        <div id="mindmap" style="width: 100%; height: 600px;"></div>
        <script>
            const {{ Markmap, loadCSS, loadJS }} = window.markmap;
            const markmapCode = `{markmap_code_escaped}`;
            
            (async () => {{
                await loadCSS('https://cdn.jsdelivr.net/npm/katex/dist/katex.min.css');
                await loadJS('https://cdn.jsdelivr.net/npm/katex/dist/katex.min.js');
                
                const svgElement = document.getElementById('mindmap');
                Markmap.create(svgElement, null, markmapCode);
            }})();
        </script>
    </body>
    </html>
    """
    return html_code

# Your Markmap code
mindmap_code = """
# Assassination Attempts on J. Kennedy

## Cold War Tensions
- Fear of communist influence
- CIA and anti-Castro operations
- Soviet Union perceived threat

## Organized Crime Retaliation
- Kennedy administration's crackdown on organized crime
- Possible mob connections to CIA operations
- Loss of influence in Cuba after Castro's rise

## Political Opposition
- Civil rights initiatives
- Economic policies
- Foreign policy decisions
"""

# Generate the HTML
html_output = markmap_to_html_with_png(mindmap_code)

# Display the HTML in Streamlit
st.components.v1.html(html_output, width=800, height=600)