import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from openai import AzureOpenAI
import streamlit as st
from streamlit.components.v1 import html
import pandas as pd
import urllib.parse
import os
import json
from uuid import uuid4
from ti_mermaid import mermaid_timeline_graph, mermaid_chart_png, markmap_to_html_with_png
from ti_mermaid_live import genPakoLink
from ti_ai import ai_check_content_relevance, ai_extract_iocs, ai_get_response, ai_process_text, ai_run_models_tweet, ai_summarise, ai_summarise_tweet, ai_run_models,ai_run_models_markmap, ai_ttp, ai_ttp_graph_timeline, ai_ttp_list
import ti_pdf
import ti_mermaid
import ti_navigator
import ti_5whats
from mistralai.client import MistralClient
from github import Github

from streamlit_markmap import markmap
import streamlit.components.v1 as components


# GitHub credentials
GITHUB_TOKEN = st.secrets["api_keys"]["github_accesstoken"]
REPO_NAME = "format81/ti-mindmap-storage"

# Check if static directory exists, if not, create it  
if not os.path.exists('./static'):  
    os.makedirs('./static')

def scrape_text(url):
    """
    Scrapes the text content from a given URL.

    This function sends a GET request to the specified URL and parses the HTML content
    to extract the text. It uses the BeautifulSoup library to parse the HTML and extract
    the text. If the GET request is successful (HTTP status code 200), the function
    returns the extracted text. Otherwise, it returns an error message indicating
    that the scraping operation failed.

    Parameters:
    url (str): The URL of the webpage from which to scrape the text.

    Returns:
    str: The extracted text content from the webpage.
    """

    # Add user-agent to avoid issue when scrapping most website
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    # Send a GET request to the URL	
    response = requests.get(url, headers=headers)
    
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


def remove_first_non_empty_line_if_mermaid(mermaid_code):
    """
    Removes the first line of the given mermaid code if it is empty or contains the string "mermaid".

    Parameters:
    mermaid_code (str): The mermaid code to process.

    Returns:
    str: The processed mermaid code without the first line.
    """
    lines = mermaid_code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "mermaid":
            lines.pop(i)  # Remove the line
            break  # Exit the loop after removing the first matching line
    return '\n'.join(lines)


def add_mermaid_theme(mermaid_code, selected_theme):
    """
    Adds a Mermaid theme to the given Mermaid code.

    Parameters:
    mermaid_code (str): The Mermaid code to add the theme to.
    selected_theme (str): The name of the Mermaid theme to use.

    Returns:
    str: The Mermaid code with the specified theme applied.

    Raises:
    ValueError: If the selected theme is not supported.
    """

    if selected_theme == 'Default':
        theme = 'default'
    elif selected_theme == 'Neutral':
        theme = 'neutral'
    elif selected_theme == 'Dark':
        theme = 'dark'
    elif selected_theme == 'Forest':
        theme = 'forest'
    elif selected_theme == 'Custom':
        # Add custom theme handling here if needed
        theme = 'base'
    else:
        theme = 'default'  # Default theme if selected theme is not recognized
    
    return f"%%{{ init: {{'theme': '{theme}'}}}}%%\n{mermaid_code}"

def upload_to_github(json_content):
    """
    Uploads JSON content to a specified GitHub repository.

    This function takes JSON content, converts it to a string, and uploads it to a GitHub
    repository. If the file with the specified path exists, it updates the file; otherwise,
    it creates a new file. The function uses a unique identifier to generate the file name
    to avoid conflicts. After uploading, it returns the raw URL of the uploaded JSON file.

    Parameters:
    json_content (dict): The JSON content to be uploaded to GitHub.

    Returns:
    str: The raw URL of the uploaded JSON file.
    """
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    commit_message = "Updated via Streamlit app"

    # Generate a unique file name
    unique_id = str(uuid4())
    file_path = f"mitre-navigator/{unique_id}.json"

    # Convert JSON to string
    json_str = json.dumps(json_content, indent=4)

    try:
        # Get the file contents from GitHub
        contents = repo.get_contents(file_path)
        sha = contents.sha
        # Update the file
        repo.update_file(contents.path, commit_message, json_str, sha)
        st.success("File updated successfully.")
    except:
        # If file does not exist, create it
        repo.create_file(file_path, commit_message, json_str)
        st.success("File created successfully.")

    # Return the raw URL of the uploaded JSON file
    raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path}"
    st.write("URL to json Mitre Navigator file:")
    st.write(raw_url)
    return raw_url



#----------------------------------------------------------------#



#----------------------------------------------------------------#
# ------------------ Streamlit UI Configuration -----------------#
#----------------------------------------------------------------#

service_selection = ""
azure_api_key = ""
azure_endpoint = ""
embedding_deployment_name = "" 
openai_api_key = ""

st.set_page_config(
    page_title="TI Mindmap",
    page_icon="logoTIMINDMAPGPT-small.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar for OpenAI API Key

with st.sidebar:
    st.image("logoTIMINDMAPGPT.png", width=75)
    st.markdown(
        "Welcome to **TI MINDMAP**, an AI-powered tool designed to help producing Threat Intelligence summaries, Mindmap and IOCs extraction and more."
    )
    st.markdown("Created by [Antonio Formato](https://www.linkedin.com/in/antonioformato/).")
    st.markdown("Contributor [Oleksiy Meletskiy](https://www.linkedin.com/in/alecm/).")
    # Add "Star on GitHub"
    st.sidebar.markdown(
        "⭐ :orange[Star on GitHub:] [![Star on GitHub](https://img.shields.io/github/stars/format81/TI-Mindmap-GPT?style=social)](https://github.com/format81/TI-Mindmap-GPT)"
    )
    st.markdown("""---""")

st.sidebar.header("Visual Mindmap Theme")
with st.sidebar: 
    # Define the options for the dropdown list
    options = ['Default', 'Neutral', 'Dark', 'Forest', 'Custom']
    # Create the dropdown list with a default value
    selected_theme_option = st.selectbox('Select an MindMap theme:', options, index=0)


st.sidebar.header("Setup")
with st.sidebar: 
    # Define the options for the dropdown list
    options = ['Mermaid', 'Markmap']
    # Create the dropdown list with a default value
    selected_mindmap_option = st.selectbox('Select an MindMap type:', options, index=0)
    st.sidebar.markdown(selected_mindmap_option)

with st.sidebar: 
    # List of options for the language dropdown menu
    options = ["English", "Italian", "Spanish", "French", "Arabic"]
    # Create a multi-select dropdown menu
    selected_language = st.multiselect("Select the language into which you want to translate the recap and mindmap of your input:", options, default=["English"])

    mistral_api_key = "" 

    service_selection = st.sidebar.radio(
        ":orange[**Select AI Service**]",
        ("OpenAI", "Azure OpenAI", "MistralAI")
    )
    if service_selection == "Azure OpenAI":
       
#/////////////////     /////////////////     /////////////////     /////////////////     /////////////////     /////////////////     /////////////////       
       
        default_azure_api_key = "103f7546e09c4dd3bdde108fcba43525"
        default_azure_endpoint = "https://openaicanadaplayground.openai.azure.com/"
        default_deployment_name = "gpt4-af-demo"
        default_embedding_deployment_name = "ada-af-demo"

# /////////////////     /////////////////     /////////////////     /////////////////     /////////////////     /////////////////     /////////////////     
        azure_api_key = st.sidebar.text_input(
            "Enter your Azure OpenAI API key:", 
            type="password",
            value=default_azure_api_key,
            help="You can find your Azure OpenAI API key on the [Azure portal](https://portal.azure.com/).",
            )
        
        azure_endpoint = st.sidebar.text_input(
            "Enter your Azure OpenAI endpoint:",
            value=default_azure_endpoint,
            help="Example: https://YOUR_RESOURCE_NAME.openai.azure.com/",
            )
        deployment_name = st.sidebar.text_input(
            "Enter your Azure OpenAI deployment name:",
            value=default_deployment_name,
            help="The deployment name you chose when you deployed the model.",
            )
        embedding_deployment_name = st.sidebar.text_input(
            "(Optional if you want to use chatbot) Enter your Text Embedding Azure OpenAI deployment name:",
            help="The deployment name you chose when you deployed text-embedding-ada-002 model.",
            value=default_embedding_deployment_name,
            )
        st.markdown(
            "Data stays active solely for the duration of the user's session and is erased when the page is refreshed."
        )
        st.markdown(
            "Tested with Azure OpenAI model: gpt-4-32k, but it should work also with gpt-35-turbo"
        )

    

    if service_selection == "OpenAI":
        deployment_name = None
        openai_api_key = st.sidebar.text_input(
            "Enter your OpenAI API key:",
            type="password",
            help="You can find your OpenAI API key on the [OpenAI dashboard](https://platform.openai.com/account/api-keys).",
            )
        #with st.sidebar:
        st.markdown(
            "Data stays active solely for the duration of the user's session and is erased when the page is refreshed."
        )
        st.markdown(
            "OpenAI model: gpt-4-1106-preview"
        )
    if service_selection == "MistralAI":
        deployment_name = None
        mistral_api_key = st.sidebar.text_input(
            "Enter your MistralAI API key:",
            type="password",
            help="You can find your MistralAI API key on the [MistralAI platform](https://platform.mistralai.com/account/api-keys).",
        )
        mistral_model = st.sidebar.text_input(
            "Enter your MistralAI model:",
            help="Example: mistral-large-latest",
        )

# "About" section to the sidebar
st.sidebar.header("About")
with st.sidebar:
    st.markdown(
        "This project should be considered a proof of concept. You are welcome to contribute or give us feedback. *Always keep in mind that AI-generated content may be incorrect.*"
    )
    st.markdown("""---""")
    st.markdown(
        "This tool is a work in progress. If you want to report a malfunction or suggest an improvement, any feedback is welcome. Write to me <a href='mailto:antonio.formato@gmail.com'>here</a> or open an issue on GitHub.",
        unsafe_allow_html=True  # Enable HTML
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
        "6) [SentinelOne](https://it.sentinelone.com/blog/)\n" +
        "7) [Splunk Security Blog](https://www.splunk.com/en_us/blog/security.html)"
    )

# Initialize OpenAI/Azure OpenAI client only if API key is provided
client = None
if service_selection == "OpenAI" and openai_api_key:
    client = OpenAI(api_key=openai_api_key)
elif service_selection == "Azure OpenAI" and azure_api_key:
    client = AzureOpenAI(
        api_key = azure_api_key,
        azure_endpoint = azure_endpoint,
        api_version = "2023-05-15"
    )
elif service_selection == "MistralAI" and mistral_api_key:
    client = MistralClient(api_key=mistral_api_key)



def toggle_tabs():
    st.session_state.show_tabs = not st.session_state.show_tabs




# Main UI






if 'show_tabs' not in st.session_state:
    st.session_state.show_tabs = False


col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.image("empty.png", width=75)
    st.title(" ")
with col2:
    form = st.form("Form to scrape", clear_on_submit=False)
    default_url = "https://www.splunk.com/en_us/blog/security/splunk-security-content-for-impact-assessment-of-crowdstrike-windows-outage.html"
    url = form.text_input("", default_url, placeholder="Paste any URL of your choice")
    
    # Center the button using custom HTML/CSS
    form.markdown(
        """
        <style>
        div.stButton > button {
            display: block;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    scrape_button = form.form_submit_button(":orange[**Scrape it**]")
    form.write("*By clicking 'Scrape it,' the data from any previous session is deleted, and a new working session will be started.*")
    #st.markdown("*Session keys are retained until the entire page is refreshed.*")
    
    # Initialize variables in session state  
    if 'text' not in st.session_state:  
        st.session_state['text'] = ""
    if 'chat_history' not in st.session_state:    
        st.session_state['chat_history'] = []
    if 'input_key' not in st.session_state:
        st.session_state['input_key'] = 0
  
    if scrape_button and client:  
        toggle_tabs()
        st.session_state['text'] = scrape_text(url)
        st.session_state['url4'] = url
        st.session_state['chat_history'] = []  # Clear chat history when new URL is scraped 
        st.session_state['input_key'] += 1  # Increment input key to clear user input
        st.session_state['summary'] = ""  # Clear summary when new URL is scraped 
        st.session_state['summary_tweet'] = ""  # Clear summary_tweet when new URL is scraped  
        st.session_state['mindmap_code'] = ""  # Clear mindmap_code when new URL is scraped
        st.session_state['ttptable'] = "" # Clear ttptable
        st.session_state['attackpath'] = "" # Clear attackpath
        st.session_state['iocs_df'] = "" # Clear iocs_df
        st.session_state['5whats'] = ""


#Insert containers separated into tabs.
if st.session_state.show_tabs:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🗃 **Main**", "💾 **AI Chat with your data**", "**📈 Pdf Report**", "**📷 Screenshot**", "**📋STIX 2.1 generator - (future release🚧)**", "**🗃️ Conf file (future release🚧)**"])
    mindmap_code = ""

    # Form for URL input
    with tab1:  
        form = st.form("Form to run", clear_on_submit=True)  
    
        # Create columns for buttons and checkboxes  
        cols = form.columns(2)  
    
        with cols[1]:  
            submit_cb_summary = form.checkbox("🗺️Summary and MindMap",value=True)  
            submit_cb_tweet = form.checkbox("📺Tweet MindMap",value=True)  
            submit_cb_ioc = form.checkbox("🧐Extract IOCs (if present)",value=True)  
            submit_cb_ttps = form.checkbox("📊Extract adversary tactics, techniques, and procedures (TTPs)",value=True)  
            submit_cb_ttps_by_time = form.checkbox("🕰️TTPs ordered by execution time",value=True)  
            submit_cb_ttps_timeline = form.checkbox("📈TTPs graphic timeline",value=True) 
            submit_cb_navigator = form.checkbox("📈MITRE Navigator Layer *(The layer file is published on the [repository](https://github.com/format81/ti-mindmap-storage/) to be used by TI Mindmap.)*",value=True)
            submit_cb_5whats = form.checkbox("🗺️5 What",value=True) 

        with cols[0]:  
            submit_button = form.form_submit_button(":orange[**Generate**]")  

        if submit_button and client:
            text = st.session_state['text']  # Use the text stored in session state 
            # Check if the content is related to cybersecurity
            #relevance_check = ai_check_content_relevance(text, client, service_selection, deployment_name)
            if service_selection == "OpenAI" and openai_api_key:
                relevance_check = ai_check_content_relevance(text, client, service_selection)
            elif service_selection == "Azure OpenAI" and azure_api_key:
                relevance_check = ai_check_content_relevance(text, client, service_selection, deployment_name)
            elif service_selection == "MistralAI" and mistral_api_key:
                relevance_check = ai_check_content_relevance(text, client, service_selection, None)

            if "not related to cybersecurity" in relevance_check:
                st.write(f"**Content not related to cybersecurity**, It's about {relevance_check}")
            else:
                # If related, proceed with summary and mindmap generation
                if selected_mindmap_option == "Mermaid": 
                    input_text = "Generate a Mermaid.js MindMap only using the text below:\n" + text
                else:
                    input_text = "Generate a MarkMap.js MindMap only using the text below:\n" + text
                with st.expander("See full article"):
                    st.write(text)

                # Generate Summary and Mindmap
                if submit_cb_summary:    
                    with st.spinner("Generating Summary "):  
                        # Check if summary exists in session state  
                        if st.session_state['summary']:  
                            summary = st.session_state['summary']  
                        else:  
                            #summary = ai_summarise(text, client, service_selection, selected_language, deployment_name)
                            if service_selection == "OpenAI" and openai_api_key:
                                summary = ai_summarise(text, client, service_selection, selected_language)
                            elif service_selection == "Azure OpenAI" and azure_api_key:
                                summary = ai_summarise(text, client, service_selection, selected_language, deployment_name)
                            elif service_selection == "MistralAI" and mistral_api_key:
                                summary = ai_summarise(text, client, service_selection, selected_language, None)  
                            st.session_state['summary'] = summary  
                        st.write("### LLM Generated Summary")  
                        st.write(summary)
                        st.write(st.session_state['mindmap_code'])
    
                        with st.spinner("Generating Mermaid Code"):  
                            # Check if mindmap_code exists in session state  
                            if st.session_state['mindmap_code']:  
                                mindmap_code = st.session_state['mindmap_code']  
                            else:  
                                #mindmap_code = add_mermaid_theme(ai_run_models(input_text, client, selected_language,deployment_name, service_selection),selected_theme_option)
                                
                                if service_selection == "OpenAI" and openai_api_key:
                                    if selected_mindmap_option == "Mermaid":
                                        mindmap_code = add_mermaid_theme(ai_run_models(input_text, client, selected_language, service_selection), selected_theme_option)
                                    else:
                                        mindmap_code = ai_run_models_markmap(input_text, client, selected_language, service_selection)
                                
                                elif service_selection == "Azure OpenAI" and azure_api_key:
                                    if selected_mindmap_option == "Mermaid":
                                        
                                        mindmap_code = add_mermaid_theme(ai_run_models(input_text, client, selected_language, service_selection, deployment_name), selected_theme_option)
                                    else:
                                        
                                        mindmap_code = ai_run_models_markmap(input_text, client, selected_language, service_selection, deployment_name)

                                elif service_selection == "MistralAI" and mistral_api_key:
                                    mindmap_code = add_mermaid_theme(ai_run_models(input_text, client, selected_language, service_selection), selected_theme_option)  
                                    
                                st.session_state['mindmap_code'] = mindmap_code  
                            
                            if selected_mindmap_option == "Mermaid":
                                html(mermaid_chart_png(mindmap_code), width=1500, height=1500)  
                            else:
                                mm = markmap(mindmap_code, height=600)

                                # Create mind map button
                                #if st.button("Customize Mind Map"):
                                #    markmap(mindmap_code)

                                # Instructions
                                #st.markdown("""
                                ### Instructions:
                                #- Use '#' for the main topic
                                #- Use '##' for subtopics
                                #- Use '###' for further details, and so on
                                #- Each new line represents a new node in the mind map
                                #""")

                        with st.expander("See OpenAI Generated " + selected_mindmap_option + " Code"):  
                            st.code(mindmap_code) 
    
                mermaid_link1 = genPakoLink(mindmap_code)    
                st.link_button("Open code in Mermaid.live", mermaid_link1)  

                #Generate tweet
                if submit_cb_tweet:
                    with st.spinner("Generating Tweet"):
                        # Check if tweet exists in session state
                        if st.session_state['summary_tweet']:
                            tweet = st.session_state['summary_tweet']
                        else:
                            #summary_tweet = ai_summarise_tweet(text, client, service_selection, selected_language,deployment_name)
                            if service_selection == "OpenAI" and openai_api_key:
                                summary_tweet = ai_summarise_tweet(text, client, service_selection, selected_language)
                            elif service_selection == "Azure OpenAI" and azure_api_key:
                                summary_tweet = ai_summarise_tweet(text, client, service_selection, selected_language, deployment_name)
                            elif service_selection == "MistralAI" and mistral_api_key:
                                summary_tweet = ai_summarise_tweet(text, client, service_selection, selected_language, None)  
                            st.session_state['summary'] = summary 
                        st.write("### LLM Generated Tweet")
                        user_input = st.text_area("Edit your tweet:", summary_tweet, height=100)

                        if submit_cb_summary == False:
                            with st.spinner("Generating Mermaid Tweet Code"):
                                #mindmap_code = add_mermaid_theme(ai_run_models_tweet(input_text, client, selected_language,deployment_name,service_selection),selected_theme_option)
                                if service_selection == "OpenAI" and openai_api_key:
                                    mindmap_code = add_mermaid_theme(ai_run_models_tweet(input_text, client, selected_language,service_selection),selected_theme_option)
                                elif service_selection == "Azure OpenAI" and azure_api_key:
                                    mindmap_code = add_mermaid_theme(ai_run_models_tweet(input_text, client, selected_language,service_selection, deployment_name),selected_theme_option)
                                elif service_selection == "MistralAI" and mistral_api_key:
                                    mindmap_code = add_mermaid_theme(ai_run_models_tweet(input_text, client, selected_language,service_selection),selected_theme_option)
                                html(mermaid_chart_png(mindmap_code), width=600, height=600)
                            with st.expander("See LLM Generated Mermaid Code - sorter version"):
                                st.code(mindmap_code)                       

                        # URL you want to open
                        url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote((user_input+' '+url))}"
                        # Label for the button
                        button_label = "Tweet it"
                        # Text to display before the button
                        instruction_text = "1.Save Mindmap above<br>   2.Click it "
                        instruction_text2 = "<br> 3. Add saved mindmap to your tweet"
                        # Create text and a button in Streamlit to open the link
                        st.markdown(f'{instruction_text} <a href="{url}" target="_blank"><button>{button_label}</button></a>{instruction_text2}', unsafe_allow_html=True)
            
                if submit_cb_ioc:
                    with st.spinner("Extracting IOCs"):
                        # Check if IOCs exist in session state  
                        if st.session_state['iocs_df']:  
                            iocs_df = st.session_state['iocs_df']  
                        else:
                            iocs_df = ai_extract_iocs(text, client, service_selection, deployment_name)
                            if isinstance(iocs_df, pd.DataFrame):
                                st.write("### Extracted IOCs")
                                st.dataframe(iocs_df)
                            else:
                                st.error(iocs_df)

                # Extracting TTPs and displaying them as a table
                if submit_cb_ttps:
                    with st.spinner("Extracting TTPs (tactics, techniques, and procedures) table from the scraped text."):
                        ttptable = ai_ttp(text, client,service_selection, deployment_name)  # Assign the output of ttp to ttptable
                        st.session_state['ttptable'] = ttptable 
                        st.write("### TTPs table")
                        st.write(ttptable)
            
                #TTPs ordered by execution time
                if submit_cb_ttps_by_time:
                    with st.spinner("TTPs ordered by execution time"):
                        # Check if attackpath exists in session state 
                        if st.session_state['attackpath']:
                            attackpath = st.session_state['attackpath']  
                        else:
                            attackpath = ai_ttp_list(text, ttptable, client, service_selection, deployment_name)
                            st.session_state['attackpath'] = attackpath  
                        st.write("### TTPs ordered by execution time")  
                        st.write(attackpath)

                # Mermaid TTPs timeline
                if submit_cb_ttps_timeline:
                    with st.spinner("Mermaid TTPs Timeline"):
                        mermaid_timeline = ai_ttp_graph_timeline(text, client, service_selection, deployment_name)
                        with st.expander("See LLM Generated Mermaid TTPs Timeline"):
                            st.code(mermaid_timeline)
                        html(mermaid_timeline_graph(mermaid_timeline), width=1500, height=1500)
                        mermaid_link2 = genPakoLink(mermaid_timeline)
                        st.link_button("Open code in Mermaid.live", mermaid_link2)

                #5whats
                if submit_cb_5whats:
                    with st.spinner("5 whats"):
                        # Check if attackpath exists in session state 
                        if st.session_state['5whats']:
                            fivewhats = st.session_state['5whats']  
                        else:
                            fivewhats = ti_5whats.ai_fivewhats(text, client, service_selection, deployment_name)
                            st.session_state['5whats'] = fivewhats  
                        st.write("### 5 whats")  
                        st.write(fivewhats)


                #Mitre Navigator layer
                if submit_cb_navigator:
                    with st.spinner("MITRE Navigator Layer"):
                        mitre_layer = ti_navigator.attack_layer(text, ttptable, client, service_selection, deployment_name)
                        # Check if mitre_layer is valid JSON
                        try:
                            json.loads(mitre_layer)
                        except json.JSONDecodeError:
                            st.error("The generated layer is not a valid JSON file.")
                            if st.button("Click here to regenerate the layer"):
                                mitre_layer = ti_navigator.attack_layer(text, client, service_selection, deployment_name)
                                try:
                                    json.loads(mitre_layer)
                                except json.JSONDecodeError:
                                    st.error("Failed to regenerate the layer. Please try again.")
                                    st.stop()  # Stop further execution
                                else:
                                    st.success("Layer regenerated successfully.")
                            
                    st.write("### MITRE ATT&CK Navigator layer json")
                    unique_id = str(uuid4())  # Create a unique ID  
                    file_name = f"./static/{unique_id}.json"  # Create a file name using the unique ID and specify directory

                    # Write the layer data to a file  
                    with open(file_name, 'w') as f:  
                        f.write(mitre_layer) 
                    
                    # Display the JSON content
                    st.json(json.loads(mitre_layer))

                    # Upload the layer data to GitHub and get the raw URL
                    raw_url = upload_to_github(json.loads(mitre_layer))

                    # Embed the Navigator in an iframe
                    navigator_iframe_url = f"https://mitre-attack.github.io/attack-navigator/#layerURL={raw_url}"
                    iframe_navigator_html = f"""
                    <iframe src="{navigator_iframe_url}" width="1200" height="800" frameborder="0"></iframe>
                    """
                    st.write("## Mitre Navigator ##")
                    st.markdown(iframe_navigator_html, unsafe_allow_html=True)  
                    
                elif submit_button and not client:
                    st.error("Please enter a valid OpenAI API key to generate the mindmap.")

        #TAB2   
        with tab2:
            st.header("💾 AI Chat with your data")
            # Process the text using the selected service
            knowledge_base = ai_process_text(st.session_state['text'], service_selection, azure_api_key, azure_endpoint, embedding_deployment_name, openai_api_key, mistral_api_key)
            # Initialize chat history in session state if it does not exist
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []

            # Display the chat history
            for message in st.session_state['chat_history']:
                if message['sender'] == 'user':
                    st.write('User: ', message['message'])
                else:
                    st.write('AI: ', message['message'])

            # Input field for user's message
            user_message = st.text_input("Your message:")

            if st.button('Send'):
                # Update the chat history with the user's message
                st.session_state['chat_history'].append({'sender': 'user', 'message': user_message})

                # Get response from the AI service
                ai_response = ai_get_response(knowledge_base, user_message, service_selection, azure_api_key, azure_endpoint, deployment_name, openai_api_key, mistral_api_key)

                # Update the chat history with the AI's response
                st.session_state['chat_history'].append({'sender': 'ai', 'message': ai_response})

                # Display the AI's response
                st.write('AI: ', ai_response)

    #TAB3
    with tab3:
        st.header("📈 Pdf Report")
        form4 = st.form("Form to run pdf", clear_on_submit=False)
        cols4 = form4.columns(2)
            
        with cols4[1]:
            submit_cb_summary4 = form4.checkbox("🗺️Add Summary and MindMap",value=True)
            #submit_cb_ioc4 = form4.checkbox("🧐I want to extract and add IOCs (if present)",value=True)
            #submit_cb_ttps4 = form4.checkbox("📊Extract adversary tactics, techniques, and procedures (TTPs)",value=True)
            submit_cb_ttps_by_time4 = form4.checkbox("🕰️TTPs ordered by execution time",value=True)
            #submit_cb_ttps_timeline4 = form4.checkbox("📈TTPs (Tactics, Techniques, and Procedures) graphic timeline",value=True)
        #user_input=""
            
        with cols[0]:
            submit_button4 = form4.form_submit_button(":orange[**Generate PDF**]")

        if submit_button4 and client:  
            text = st.session_state['text']  # Use the text stored in session state  
            relevance_check4 = ai_check_content_relevance(text, client, service_selection, deployment_name)  
            if "not related to cybersecurity" in relevance_check4:  
                st.write(f"**Content not related to cybersecurity**, It's about {relevance_check}")  
            else:  
                input_text = "Generate a Mermaid.js MindMap only using the text below:\n" + text  
                with st.expander("See full article"):  
                    st.write(text)  
    
                # Generate Summary and Mindmap  
                if submit_cb_summary4:  
                    with st.spinner("Generating Summary "):  
                        # Check if summary exists in session state  
                        if st.session_state['summary']:  
                            summary = st.session_state['summary']  
                        else:  
                            summary = ai_summarise(text, client, service_selection, selected_language, deployment_name)  
                            st.session_state['summary'] = summary  
                        st.write("### OpenAI Generated Summary")  
                        st.write(summary)   
    
                        with st.spinner("Generating Mermaid Code"):  
                            # Check if mindmap_code exists in session state  
                            if st.session_state['mindmap_code']:  
                                mindmap_code = st.session_state['mindmap_code']  
                            else:  
                                mindmap_code = add_mermaid_theme(ai_run_models(input_text, client, selected_language, deployment_name, service_selection),selected_theme_option)  
                                st.session_state['mindmap_code'] = mindmap_code  
                            html(mermaid_chart_png(mindmap_code), width=1500, height=1500)  
                        with st.expander("See OpenAI Generated Mermaid Code"):  
                            st.code(mindmap_code)  
            
                # Extracting TTPs 
                if submit_cb_ttps_by_time4:  
                    with st.spinner("TTPs ordered by execution time"):  
                        # Check if ttptable exists in session state  
                        if st.session_state['ttptable']:
                            ttptable = st.session_state['ttptable']  
                        else:  
                            ttptable = ai_ttp(text, client, service_selection,  deployment_name, input_text)  # Assign the output of ttp to ttptable  
                            st.session_state['ttptable'] = ttptable   
                        st.write("### TTPs table")  
                        st.write(ttptable)  
    
                        # Check if attackpath exists in session state 
                        if st.session_state['attackpath']:
                            attackpath = st.session_state['attackpath']  
                        else:
                            attackpath = ai_ttp_list(text, ttptable, client, service_selection, deployment_name)
                            st.session_state['attackpath'] = attackpath  
                        st.write("### TTPs ordered by execution time")  
                        st.write(attackpath)

                pdf_bytes = ti_pdf.create_pdf_bytes(st.session_state['url4'], summary, mindmap_code, attackpath=None)

                st.download_button(label="Save report to disk",
                            data=pdf_bytes,
                            file_name="ti-mindmap-gpt.streamlit.app.pdf",
                            mime='application/octet-stream')
                
    #TAB4
    with tab4:
        st.write("📷 Screenshot")
        # Access the secret API key
        api_key_thumbnail = st.secrets["api_keys"]["thumbnail"]
        # Make a request to the API
        screenshot = requests.get(f"https://api.thumbnail.ws/api/{api_key_thumbnail}/thumbnail/get?url={url}&width=840&delay=1500")

        # If the request is successful, display the image
        if screenshot.status_code == 200:
            screenshot_data = screenshot.content  # Store the screenshot image data
            st.image(screenshot_data)
            st.session_state['screenshot_data'] = screenshot_data  # Save to session state
        else:
            st.write(f"Failed to get the image. Status code: {screenshot.status_code}")
            st.session_state['screenshot_data'] = None  # Ensure there's a default value
        
    #TAB5
    with tab5:
        st.write("📋 STIX 2.1 generator - future release🚧")
        st.write("***Work in progress***")
        st.write("We are working on an initial version of a STIX 2.1 report generator. We will release the functionality as soon as it is tested and operational. Stay tuned.")

    #TAB6
    with tab6:
        st.write("🗃️ Conf file - future release🚧")
        st.write("***Work in progress***")