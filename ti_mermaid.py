import re

def mermaid_chart(mindmap_code):
    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid">{mindmap_code}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    return html_code

# with save to SVG capability
def mermaid_chart_svg(mindmap_code):
    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid" id="mermaidChart">{mindmap_code}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
    mermaid.initialize({{startOnLoad:true}});
    function downloadSVG() {{
        var svg = document.querySelector("#mermaidChart svg");
        var serializer = new XMLSerializer();
        var source = serializer.serializeToString(svg);
        var a = document.createElement("a");
        a.href = 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(source);
        a.download = 'mindmap.svg';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }}
    </script>
    <button onclick="downloadSVG()">Save Mindmap</button>
    """
    return html_code

# with save to PNG capability
def mermaid_chart_png(mindmap_code):
    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid" id="mermaidChart">{mindmap_code}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
    mermaid.initialize({{startOnLoad:true}});
    function downloadPNG() {{
        var svg = document.querySelector("#mermaidChart svg");
        var canvas = document.createElement('canvas');
        var ctx = canvas.getContext('2d');
        var data = (new XMLSerializer()).serializeToString(svg);
        var DOMURL = window.URL || window.webkitURL || window;
        
        var img = new Image();
        var svgBlob = new Blob([data], {{type: 'image/svg+xml;charset=utf-8'}});
        var url = DOMURL.createObjectURL(svgBlob);
        
        img.onload = function () {{
            ctx.canvas.width = svg.getBoundingClientRect().width;
            ctx.canvas.height = svg.getBoundingClientRect().height;
            ctx.drawImage(img, 0, 0);
            DOMURL.revokeObjectURL(url);
            
            var imgURI = canvas
                .toDataURL('image/png')
                .replace('image/png', 'image/octet-stream');
            
            var evt = new MouseEvent('click', {{
                view: window,
                bubbles: false,
                cancelable: true
            }});
            
            var a = document.createElement('a');
            a.setAttribute('download', 'mindmap.png');
            a.setAttribute('href', imgURI);
            a.setAttribute('target', '_blank');
            
            a.dispatchEvent(evt);
        }};
        
        img.src = url;
    }}
    </script>
    <button onclick="downloadPNG()">Save Mindmap as PNG</button>
    """
    return html_code


def mermaid_timeline_graph(mindmap_code_timeline):
    """
    Renders a Mermaid timeline graph from the given Mermaid code.

    Args:
        mindmap_code_timeline (str): The Mermaid code for the timeline graph.

    Returns:
        str: The HTML code for the Mermaid timeline graph.
    """

    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid">{mindmap_code_timeline}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    return html_code

#Function to remove nested parentheses if present in LLM generated mermaid code
def remove_nested_parentheses(mindmap_code):
    # Find all occurrences of nested parentheses
    matches = re.findall(r'\(([^()]*\([^()]*\)[^()]*)\)', mindmap_code)
    for match in matches:
        # Replace the nested parentheses with a single hyphen
        mindmap_code = mindmap_code.replace(f'({match})', match.replace('(', '').replace(')', '-'))
    return mindmap_code