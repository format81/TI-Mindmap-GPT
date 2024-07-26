def markmap_editor():
    # HTML template for the MarkMap editor with code visualization
    html_template = """
    <div style="display: flex; flex-direction: row; height: 400px;">
        <div id="editor" style="width: 50%; height: 100%; border: 1px solid #ccc;"></div>
        <div id="codeViewer" style="width: 50%; height: 100%; border: 1px solid #ccc; overflow: auto; padding: 10px; font-family: monospace; white-space: pre;"></div>
    </div>
    <div id="mindmap" style="width: 100%; height: 400px;"></div>
    <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.2.7/dist/index.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js"></script>
    <script>
    const editor = ace.edit("editor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/markdown");
    editor.setValue(`# MarkMap Example
        ## Topic 1
        ### Subtopic 1.1
        ### Subtopic 1.2
        ## Topic 2
        ### Subtopic 2.1
        ### Subtopic 2.2`);

    const mm = markmap.Markmap.create("#mindmap");
    const codeViewer = document.getElementById("codeViewer");
    
    function updateMindmap() {
        const content = editor.getValue();
        mm.setData(markmap.transform(content));
        codeViewer.textContent = content;
    }

    editor.session.on('change', updateMindmap);
    updateMindmap();
    </script>
    """

    # Render the HTML template
    components.html(html_template, height=850)

# Streamlit app
st.title("MarkMap Live Editor")

markmap_editor()


st.markdown("""
### Instructions:
- Edit the markdown in the top text area
- The mind map will update in real-time below
- Use '#' for main topics, '##' for subtopics, and so on
""")