import requests
from bs4 import BeautifulSoup
import openai
from openai import OpenAI
import streamlit as st
from streamlit.components.v1 import html

def scrape_text(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # If the GET request is successful, the status code will be 200
    if response.status_code == 200:
        # Get the content of the response
        page_content = response.content
        # Create a BeautifulSoup object and specify the parser
        soup = BeautifulSoup(page_content, "html.parser")
        # Get the text of the soup object
        text = soup.get_text()
        # Return the text
        return text
    else:
        return "Failed to scrape the website"

def mermaid_chart(mindmap_code):
    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid">{mindmap_code}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    return html_code

# Function to summarize the blog
def summarise(input_text, client):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages= [
            {
                "role": "system",
                "content":"You are responsible for summarizing a threat report for a Threat Analyst. Write a paragraph that will summarize the main topic, the key findings, and all the detailed information relevant for a threat analyst such as detection opportunity iocs and TTPs. Use the title and add an emoji. Do not generate a bullet points list but rather multiple paragraphs."
            },
            {"role": "user", "content": input_text},
        ],
    )
    return response.choices[0].message.content 

# Function to check if content is related to cybersecurity
def check_content_relevance(input_text, client):
    prompt = "Determine if the following text is related to cybersecurity: \n" + input_text
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content

# Function to generate a mindmap
def run_models(input_text, client):
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {
                "role": "system",
                "content": "You are tasked with creating an in-depth mindmap designed specifically for a threat analyst. This mindmap aims to visually organize key findings and crucial highlights from the text. Please adhere to the following guidelines: \n1. Avoid using hyphens in the text, as they cause errors in the Mermaid.js code 2. Limit the number of primary nodes branching from the main node to four. These primary nodes should encapsulate the top four main themes. Add detailed sub-nodes to elaborate on these themes \n3. Incorporate icons where suitable to enhance readability and comprehension\n4. Use single parentheses around each node to give them a rounded shape.\n5. avoid using icons and emoji\n6. Do not insert spaces after the text of each line and do not use parentheses or special characters for the names of the chart fields.\n7 Start mermaid code with 'mindmap', not use as first line \n8 Don't write ``` as last line. \n9 Avoid use line with style root. \n10 Avoid close with any comment starting with # . \n11 not use theme as second line, second line must start with root syntax. \n12 special characters need to be escaped or avoided, like brackets in domain. Example: not use mail[.]kz but use mail.kz"
            },
			{
				 "role":"user",
				 "content":"Title:  Threat Report Summary: Kazakhstan-associated YoroTrooper disguises origin of attacks as Azerbaijan\n\nThreat actors known as YoroTrooper, presumably originating from Kazakhstan, have been conducting cyber espionage activities, largely focusing on Commonwealth of Independent States (CIS) countries. These actors mask their origins, making their attacks appear to come from Azerbaijan. Several tactics, techniques, and procedures (TTPs) were used, including using VPN exit points in Azerbaijan and spear phishing via credential-harvesting sites. They have infiltrated websites and accounts of several government officials between May and August 2023.\n\nThe information supporting that YoroTrooper is likely based in Kazakhstan includes the use of Kazakh currency, fluency in Kazakh and Russian, and the limited targeting of Kazakh entities. Interestingly, YoroTrooper has shown a defensive interest in the website of the Kazakhstani state-owned email service (mail[.]kz), taking precautions to ensure it is not exposed to potential security vulnerabilities. The only Kazakh institution targeted was the government’s Anti-Corruption Agency.\n\nYoroTrooper subtly alters its actions to blur its origin, using various tactics to point to Azerbaijan. In addition to routinely rerouting its operations via Azerbaijan, the threat actors frequently translate Azerbaijani to Russian and draft lures in Russian before converting them to Azerbaijani for their phishing attacks. The addition of Uzbek language in their payloads since June 2023 poses another layer of obfuscation, but is likely a demonstration of the actors' multilingual abilities rather than an attempt to mask as an Uzbek adversary.\n\nIn terms of malware use, YoroTrooper has evolved from relying heavily on commodity malware to also using custom-built malware across platforms such as Python, PowerShell, GoLang, and Rust. There is evidence that this threat actor continues to learn and adapt. There has been successful intrusion into several CIS government entities, indicating possible state-backing or state interests serving as motivation.\n\nInvestigations into YoroTrooper are ongoing to determine the extent of potential state sponsorship and additionally whether there is another motivator or objective, such as financial gain through the sale of state-held information. Protective countermeasures have been highlighted. Various IOCs are listed on GitHub for public access."
			},
			{
				 "role":"assistant",
				 "content":"mindmap\nroot(YoroTrooper Threat Analysis)\n    (Origin and Target)\n      ::icon(fa fa-crosshairs)\n      (Likely originates from Kazakhstan)\n      (Mainly targets CIS countries)\n      (Attempts to make attacks appear from Azerbaijan)\n    (TTPs)\n      ::icon(fa fa-tactics)\n      (Uses VPN exit points in Azerbaijan)\n      (Spear phishing via credential-harvesting sites)\n      (Infiltrates websites and accounts of government officials)\n      (Subtly alters actions to blur origin)\n    (Language Proficiency)\n      ::icon(fa fa-language)\n      (Fluency in Kazakh and Russian)\n      (Translates Azerbaijani to Russian for phishing attacks)\n      (Uses Uzbek language in payloads)\n    (Malware Use)\n      ::icon(fa fa-bug)\n      (Evolved from commodity malware to custom-built malware)\n      (Uses Python, PowerShell, GoLang, and Rust platforms)\n    (Investigations and Countermeasures)\n      ::icon(fa fa-search)\n      (Ongoing investigations into potential state sponsorship)\n      (Protective countermeasures highlighted)\n      (IOCs listed on GitHub for public access)"
			},
		    {"role": "user", "content": input_text},
        ],
    )
    return response.choices[0].message.content

# ------------------ Streamlit UI Configuration ------------------ #
st.set_page_config(
    page_title="Generative AI Threat Intelligence Mindmap",
    page_icon=":brain:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar for OpenAI API Key
with st.sidebar:
    st.markdown(
        "Welcome to TI MINDMAP GPT, an AI-powered tool designed to help producing Threat Intelligence Mindmap."
    )
    st.markdown("Created by [Antonio Formato](https://www.linkedin.com/in/antonioformato/).")
    # Add "Star on GitHub"
    st.sidebar.markdown(
        "⭐ Star on GitHub: [![Star on GitHub](https://img.shields.io/github/stars/format81/TI-Mindmap-GPT?style=social)](https://github.com/format81/TI-Mindmap-GPT)"
    )
    st.markdown("""---""")
st.sidebar.header("Setup")
with st.sidebar:
    st.markdown(
        "Bring your own OpenAI API key"
    )
openai_api_key = st.sidebar.text_input(
    "Enter your OpenAI API key:",
    type="password",
    help="You can find your OpenAI API key on the [OpenAI dashboard](https://platform.openai.com/account/api-keys).",
    )
st.markdown("""---""")

with st.sidebar:
    st.markdown(
        "Data stays active solely for the duration of the user's session and is erased when the page is refreshed."
    )
    st.markdown(
        "OpenAI model: gpt-4-1106-preview"
    )

# "About" section to the sidebar
st.sidebar.header("About")
with st.sidebar:
    st.markdown(
        "This project should be considered a proof of concept. You are welcome to contribute or give me feedback. Always keep in mind that AI-generated content may be incorrect."
    )
    st.markdown("""---""")

# "Example" section to the sidebar
st.sidebar.header("Usage example")
with st.sidebar:
    st.markdown(
        "Select a blog post or a Threat Intelligence article and insert it into the box. OpenAI will generate a summary and from it, a mind map."
    )
    st.markdown(
        "Suggestion: I recommend good starting points.\n" +
        "1) [Microsoft Threat Intelligence community](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/)\n" +
        "2) [Cisco Talos](https://blog.talosintelligence.com/)\n" +
        "3) [Check Point Research](https://research.checkpoint.com/)\n" +
        "4) [Secure List by Kaspersky](https://securelist.com/category/apt-reports/)\n" +
        "5) [Mandiant](https://www.mandiant.com/resources/blog/)\n" +
        "6) [Symantec](https://symantec-enterprise-blogs.security.com/blogs/threat-intelligence)\n" +
        "6) [SentinelOne](https://it.sentinelone.com/blog/)"
    )

# Initialize OpenAI client only if API key is provided
client = None
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)

# Main UI
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.title("TI MINDMAP GPT")
with col2:
    st.image("logoTIMINDMAPGPT.png", width=450)

# Form for URL input
form = st.form("Form to run", clear_on_submit=True)
url = form.text_input("Enter your URL below:", placeholder="Paste any URL of your choice")
submit_button = form.form_submit_button("Generate Summary and Mindmap")

if submit_button and client:
    text = scrape_text(url)
    # Check if the content is related to cybersecurity
    relevance_check = check_content_relevance(text, client)
    if "not related to cybersecurity" in relevance_check:
        st.write(f"**Content not related to cybersecurity**, It's about {relevance_check}")
    else:
        # If related, proceed with summary and mindmap generation
        input_text = "Generate a Mermaid.js mindmap only using the text below:\n" + text
        with st.expander("See full article"):
            st.write(text)
        with st.spinner("Generating Summary "):
            summary = summarise(text, client)
            st.write("### OpenAI Generated Summary")
            st.write(summary)
        with st.spinner("Generating Mermaid Code"):
            mindmap_code = run_models(input_text, client)
            with st.expander("See OpenAI Generated Mermaid Code"):
                st.code(mindmap_code)
            html(mermaid_chart(mindmap_code), width=1500, height=1500)
elif submit_button and not client:
    st.error("Please enter a valid OpenAI API key to generate the mindmap.")
