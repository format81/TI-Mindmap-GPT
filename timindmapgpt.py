import requests
from bs4 import BeautifulSoup
from openai import OpenAI, AzureOpenAI # Combined imports
import streamlit as st
from streamlit.components.v1 import html as st_html # Alias to avoid conflict
import pandas as pd
import urllib.parse
import os
import json
from uuid import uuid4
import datetime # For PDF filename timestamp

# --- NEW IMPORTS for PDF and text input ---
import PyPDF2 # For PDF text extraction
import io      # For handling uploaded file bytes
# --- END NEW IMPORTS ---

# Custom module imports
from ti_mermaid import mermaid_timeline_graph, mermaid_chart_png # Assuming markmap_to_html_with_png is used if selected
from ti_mermaid_live import genPakoLink
from ti_ai import (
    ai_check_content_relevance, ai_extract_iocs, ai_get_response,
    ai_process_text, ai_run_models_tweet, ai_summarise,
    ai_summarise_tweet, ai_run_models, ai_run_models_markmap,
    ai_ttp, ai_ttp_graph_timeline, ai_ttp_list
)
import ti_pdf
# import ti_mermaid # Already imported specific functions
import ti_navigator
import ti_5whats
import ti_stix
from mistralai.client import MistralClient
from github import Github
from markdownify import markdownify as md_markdownify # Alias to avoid conflict if any

from streamlit_markmap import markmap # For Markmap visualization
# import streamlit.components.v1 as components # Already imported st_html for components.v1.html

# --- Constants and Configuration ---
GITHUB_TOKEN_SECRET = "github_accesstoken" # Key for GitHub token in st.secrets.api_keys
REPO_NAME = "format81/ti-mindmap-storage"
STATIC_DIR = './static'

# Check if static directory exists, if not, create it
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# --- Helper Functions ---
def scrape_text(url):
    """Scrapes text from a URL and converts to Markdown."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        main_content = soup.find('main') or soup.body
        if main_content:
            # Convert to Markdown
            # Forcing heading_style='atx' and other options for cleaner markdown
            text = md_markdownify(str(main_content), heading_style='atx', bullets='-', code_language_callback=lambda el: el.get('class', [None])[0])
            return text
        return "Could not extract main content from the page."
    except requests.exceptions.Timeout:
        return f"Failed to scrape the website: Request timed out for URL {url}"
    except requests.exceptions.RequestException as e:
        return f"Failed to scrape the website: {e}"

def extract_text_from_pdf(uploaded_file_bytes):
    """Extracts text from an uploaded PDF file's bytes."""
    try:
        pdf_file_object = io.BytesIO(uploaded_file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file_object)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            if page_text: # Ensure text was actually extracted
                text += page_text + "\n" # Add a newline after each page's text
        
        if not text.strip():
            return "Could not extract any text from the PDF. The PDF might be image-based (requiring OCR, which is not implemented) or protected.", None
        # We return raw text. If Markdown conversion is needed, it can be done selectively later.
        return text, None # Return raw text and no error
    except Exception as e:
        return None, f"Failed to process PDF: {str(e)}"

def add_mermaid_theme(mermaid_code, selected_theme_name):
    """Adds a Mermaid theme to the given Mermaid code."""
    theme_map = {
        'Default': 'default', 'Neutral': 'neutral', 'Dark': 'dark',
        'Forest': 'forest', 'Custom': 'base' # 'base' for custom, can be expanded
    }
    theme = theme_map.get(selected_theme_name, 'default')
    return f"%%{{ init: {{'theme': '{theme}'}}}}%%\n{mermaid_code}"

def upload_to_github(json_content_dict, file_prefix="mitre-navigator"):
    """Uploads JSON content to GitHub and returns the raw URL."""
    if not GITHUB_TOKEN:
        st.error("GitHub token not configured in secrets. Cannot upload.")
        return None
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        commit_message = "Updated via TI-Mindmap-GPT Streamlit app"
        unique_id = str(uuid4())
        file_path = f"{file_prefix}/{unique_id}.json"
        json_str = json.dumps(json_content_dict, indent=4)

        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, json_str, contents.sha)
            st.success(f"GitHub: File '{file_path}' updated successfully.")
        except Exception: # Broad exception for file not found or other issues
            repo.create_file(file_path, commit_message, json_str)
            st.success(f"GitHub: File '{file_path}' created successfully.")
        
        raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path}"
        st.info(f"URL to JSON file on GitHub: {raw_url}")
        return raw_url
    except Exception as e:
        st.error(f"Failed to upload to GitHub: {e}")
        return None

# --- Session State Initialization ---
def initialize_session_state():
    defaults = {
        'show_tabs': False,
        'text': "", # This will hold the (potentially truncated) text for AI processing
        'full_original_text': "", # This will hold the original full text from any source
        'url4': "", # Stores the source identifier (URL, PDF name, "Pasted Text")
        'chat_history': [],
        'input_key': 0, # For resetting chat input
        'summary': "",
        'summary_tweet': "",
        'mindmap_code': "",
        'tweet_mindmap_code': "", # Initialized for tweet mindmap feature
        'ttptable': "", # For TTPs overview table (Markdown string)
        'attackpath': "", # For TTPs ordered by execution time (string)
        'iocs_df': None, # For IOCs DataFrame
        '5whats': "", # For 5 Whats report string
        'stix_sdo': "", 'stix_sco': "", 'stix_sro': "", 'stix_bundle': "", # For STIX data
        'mermaid_timeline': "", # For TTP timeline Mermaid code
        'mitre_layer_json_str': "", # For MITRE layer JSON string
        'mitre_navigator_raw_url': "", # For raw URL of uploaded MITRE layer
        'selected_mindmap_option': 'Mermaid', # Default from sidebar
        'selected_theme_option': 'Default',   # Default from sidebar
        'selected_language': ["English"],     # Default from sidebar
        'service_selection': 'OpenAI',        # Default from sidebar
        'pdf_orientation_choice': 'portrait', # Default for PDF
        'knowledge_base': None, # For AI Chat
        'knowledge_base_source_text': "", # To track if knowledge base needs update
        'input_source_type': 'URL', # Default input type ('URL', 'PDF', 'Text')
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# --- Streamlit UI Configuration ---
st.set_page_config(
    page_title="TI Mindmap",
    page_icon="logoTIMINDMAPGPT.png", # Make sure this path is correct
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Global Variables for API Keys (populated from sidebar) ---
GITHUB_TOKEN = st.secrets.get("api_keys", {}).get(GITHUB_TOKEN_SECRET, "")
client = None # AI client
# These will be populated in the sidebar logic
azure_api_key, azure_endpoint, deployment_name, embedding_deployment_name = "", "", "", ""
openai_api_key, mistral_api_key, mistral_model_name_input = "", "", ""


# --- Sidebar UI ---
with st.sidebar:
    st.image("logoTIMINDMAPGPT.png", width=75)
    st.markdown("Welcome to **TI MINDMAP GPT**...")
    st.markdown("Created by [Antonio Formato](https://www.linkedin.com/in/antonioformato/).")
    st.markdown("Contributor [Oleksiy Meletskiy](https://www.linkedin.com/in/alecm/).")
    st.markdown("⭐ :orange[Star on GitHub:] [![Star on GitHub](https://img.shields.io/github/stars/format81/TI-Mindmap-GPT?style=social)](https://github.com/format81/TI-Mindmap-GPT)")
    st.markdown("---")

    st.header("Visual Options")
    st.session_state.selected_theme_option = st.selectbox(
        'Select MindMap Theme:',
        ['Default', 'Neutral', 'Dark', 'Forest', 'Custom'],
        index=['Default', 'Neutral', 'Dark', 'Forest', 'Custom'].index(st.session_state.selected_theme_option),
        key='theme_selector_sidebar' # Changed key for uniqueness
    )
    st.session_state.selected_mindmap_option = st.selectbox(
        'Select MindMap Type:',
        ['Mermaid', 'Markmap'],
        index=['Mermaid', 'Markmap'].index(st.session_state.selected_mindmap_option),
        key='mindmap_type_selector_sidebar' # Changed key
    )

    st.header("AI & Language Setup")
    st.session_state.selected_language = st.multiselect(
        "Translate recap & mindmap to:",
        ["English", "Italian", "Spanish", "French", "Arabic"],
        default=st.session_state.selected_language,
        key='language_selector_sidebar' # Changed key
    )
    
    current_service_selection_index = ("OpenAI", "Azure OpenAI", "MistralAI").index(st.session_state.service_selection)
    st.session_state.service_selection = st.radio(
        ":orange[**Select AI Service**]",
        ("OpenAI", "Azure OpenAI", "MistralAI"),
        index=current_service_selection_index,
        key='ai_service_selector_sidebar' # Changed key
    )
    
    # API Key Inputs based on selection
    if st.session_state.service_selection == "Azure OpenAI":
        azure_api_key = st.text_input("Azure OpenAI API key:", type="password", key="azure_key_input_sidebar")
        azure_endpoint = st.text_input("Azure OpenAI endpoint:", key="azure_endpoint_input_sidebar")
        deployment_name_input = st.text_input("Azure OpenAI deployment name (e.g., gpt-4):", key="azure_deployment_input_sidebar")
        embedding_deployment_name_input = st.text_input("Text Embedding Azure deployment name (optional):", key="azure_embedding_input_sidebar")
        deployment_name = deployment_name_input 
        embedding_deployment_name = embedding_deployment_name_input
        st.caption("Tested with gpt-4, gpt-4-32k, gpt-35-turbo.")
    elif st.session_state.service_selection == "OpenAI":
        openai_api_key = st.text_input("OpenAI API key:", type="password", key="openai_key_input_sidebar")
        deployment_name = "gpt-4-1106-preview" # Default OpenAI model
        st.caption(f"Using OpenAI model: {deployment_name}")
    elif st.session_state.service_selection == "MistralAI":
        mistral_api_key = st.text_input("MistralAI API key:", type="password", key="mistral_key_input_sidebar")
        mistral_model_name_input = st.text_input("MistralAI model (e.g., mistral-large-latest):", value="mistral-large-latest", key="mistral_model_name_input_sidebar")
        deployment_name = mistral_model_name_input
        st.caption(f"Using MistralAI model: {deployment_name if deployment_name else 'Not specified'}")

    st.markdown("---")
    st.header("About")
    st.markdown("This project is a proof of concept... AI-generated content may be incorrect.")
    st.markdown("Feedback: [Email](mailto:antonio.formato@gmail.com) or [GitHub Issues](https://github.com/format81/TI-Mindmap-GPT/issues).")
    st.markdown("---")
    st.header("Usage Example")
    st.markdown("Select input source, provide content, and click 'Analyze'. Good TI starting points: [Microsoft TI](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/), [Cisco Talos](https://blog.talosintelligence.com/), etc.")


# --- Initialize AI Client ---
if st.session_state.service_selection == "OpenAI" and openai_api_key:
    try:
        client = OpenAI(api_key=openai_api_key)
    except Exception as e:
        st.sidebar.error(f"OpenAI Client Error: {e}")
        client = None
elif st.session_state.service_selection == "Azure OpenAI":
    if azure_api_key and azure_endpoint and deployment_name:
        try:
            client = AzureOpenAI(
                api_key=azure_api_key,
                azure_endpoint=azure_endpoint,
                api_version="2023-05-15" # Use a relevant API version
            )
        except Exception as e:
            st.sidebar.error(f"Azure Client Error: {e}")
            client = None
elif st.session_state.service_selection == "MistralAI":
    if mistral_api_key and deployment_name:
        try:
            client = MistralClient(api_key=mistral_api_key)
        except Exception as e:
            st.sidebar.error(f"MistralAI Client Error: {e}")
            client = None

# --- Main UI ---
def toggle_tabs_visibility():
    st.session_state.show_tabs = True

st.title("TI Mindmap")

# --- Input Source Selection ---
input_source_type_key = "input_source_selector_main" # Define a unique key
if input_source_type_key not in st.session_state: # Initialize if not present
    st.session_state[input_source_type_key] = st.session_state.input_source_type

input_source_type_selection = st.radio(
    "Select Input Source:",
    options=["URL", "PDF Upload", "Text Input"],
    index=["URL", "PDF Upload", "Text Input"].index(st.session_state[input_source_type_key]),
    key=input_source_type_key, # Use the defined key
    horizontal=True
)
st.session_state.input_source_type = input_source_type_selection # Persist selection

source_text_content = "" 
source_identifier = ""   
trigger_analysis = False 

if st.session_state.input_source_type == "URL":
    with st.form("form_scrape_url_main", clear_on_submit=False):
        url_input_val = st.session_state.get('url_input_widget_main_val', '')
        url_input = st.text_input(
            "Enter URL to analyze:",
            placeholder="Paste any Threat Intelligence URL here",
            key="url_input_widget_main",
            value=url_input_val
        )
        st.session_state.url_input_widget_main_val = url_input # Persist input field
        scrape_button = st.form_submit_button(":mag_right: :orange[**Analyze URL**]")
        st.caption("*Clicking 'Analyze' clears previous session data and starts a new working session.*")
        if scrape_button:
            if not url_input:
                st.warning("Please enter a URL to scrape.")
            else:
                source_identifier = url_input
                with st.spinner(f"Scraping text from {url_input}..."):
                    scraped_data = scrape_text(url_input)
                    if "Failed to scrape" in scraped_data or "Could not extract main content" in scraped_data or not scraped_data.strip():
                        st.error(f"Could not retrieve content from the URL: {scraped_data}")
                        source_text_content = ""
                    else:
                        source_text_content = scraped_data
                        st.success(f"Successfully scraped content from {url_input}.")
                        trigger_analysis = True

elif st.session_state.input_source_type == "PDF Upload":
    with st.form("form_upload_pdf_main", clear_on_submit=False):
        uploaded_pdf_file = st.file_uploader(
            "Upload Threat Report PDF",
            type="pdf",
            key="pdf_uploader_widget_main"
        )
        analyze_pdf_button = st.form_submit_button(":page_facing_up: :orange[**Analyze PDF**]")
        st.caption("*Clicking 'Analyze' clears previous session data and starts a new working session.*")
        if analyze_pdf_button:
            if not uploaded_pdf_file:
                st.warning("Please upload a PDF file.")
            else:
                source_identifier = f"PDF: {uploaded_pdf_file.name}"
                with st.spinner(f"Extracting text from {uploaded_pdf_file.name}..."):
                    pdf_bytes = uploaded_pdf_file.getvalue()
                    extracted_data, error_msg = extract_text_from_pdf(pdf_bytes)
                    if error_msg:
                        st.error(error_msg)
                        source_text_content = ""
                    else:
                        source_text_content = extracted_data
                        st.success(f"Successfully extracted text from {uploaded_pdf_file.name}.")
                        with st.expander("Preview Extracted PDF Text (first 2000 characters)", expanded=False):
                            st.text((source_text_content[:2000] + "...") if len(source_text_content) > 2000 else source_text_content)
                        trigger_analysis = True

elif st.session_state.input_source_type == "Text Input":
    with st.form("form_paste_text_main", clear_on_submit=False):
        pasted_text_val = st.session_state.get('text_area_widget_main_val', '')
        pasted_text_input = st.text_area(
            "Paste Threat Intelligence Text Here:",
            height=300,
            key="text_area_widget_main",
            placeholder="Paste the full text of the threat report here...",
            value=pasted_text_val
        )
        st.session_state.text_area_widget_main_val = pasted_text_input # Persist input
        analyze_text_button = st.form_submit_button(":clipboard: :orange[**Analyze Text**]")
        st.caption("*Clicking 'Analyze' clears previous session data and starts a new working session.*")
        if analyze_text_button:
            if not pasted_text_input.strip():
                st.warning("Please paste some text to analyze.")
            else:
                source_identifier = "Pasted Text Input"
                source_text_content = pasted_text_input
                st.success("Text input received and ready for analysis.")
                trigger_analysis = True

# --- Central Analysis Trigger ---
if trigger_analysis and source_text_content:
    if not client:
        st.error("AI Service not configured or client initialization failed. Please enter API key and details in the sidebar.")
    else:
        st.session_state['full_original_text'] = source_text_content
        st.session_state['url4'] = source_identifier

        MAX_TEXT_LENGTH_FOR_AI = 250000 
        if len(source_text_content) > MAX_TEXT_LENGTH_FOR_AI:
            st.warning(
                f"The input text is very long ({len(source_text_content):,} characters). "
                f"To manage processing demands, the analysis will be performed on the first {MAX_TEXT_LENGTH_FOR_AI:,} characters. "
                "The full original content is available in the 'Original Input Content' tab."
            )
            st.session_state['text'] = source_text_content[:MAX_TEXT_LENGTH_FOR_AI]
        else:
            st.session_state['text'] = source_text_content
        
        toggle_tabs_visibility()
        keys_to_reset = ['summary', 'summary_tweet', 'mindmap_code', 'tweet_mindmap_code',
                         'ttptable', 'attackpath', 'iocs_df', '5whats', 'stix_sdo', 'stix_sco',
                         'stix_sro', 'stix_bundle', 'mermaid_timeline',
                         'mitre_layer_json_str', 'mitre_navigator_raw_url', 'chat_history',
                         'knowledge_base', 'knowledge_base_source_text']
        for key in keys_to_reset:
            if key == 'iocs_df':
                st.session_state[key] = pd.DataFrame()
            elif key == 'chat_history':
                st.session_state[key] = []
            elif key == 'knowledge_base':
                st.session_state[key] = None
            else:
                st.session_state[key] = ""
        
        st.success(f"Content from '{source_identifier}' is ready. Proceed to generate reports in the 'Main Report Generation' tab.")
        st.rerun()

elif trigger_analysis and not source_text_content:
    st.error("Failed to get content from the source. Please try again or use a different source.")
    st.session_state.show_tabs = False

# --- Tabs Display ---
if st.session_state.show_tabs:
    tab_titles = ["🗃️ **Main Report Generation**", "💬 **AI Chat**", "📄 **PDF Report**", 
                  "🖼️ **Screenshot**", "🛡️ **STIX 2.1 (beta)**", "📝 **Original Input Content**"] # Renamed last tab
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_titles)

    # --- TAB 1: Main Report Generation ---
    with tab1:
        st.header("Generate Cyber Therat Intelligence Components")
        if not st.session_state.get('text', "").strip():
            st.info("Please provide content using an input source and click 'Analyze' on the main page.")
        else:
            with st.form("form_generate_reports_tab1"):
                st.markdown("Select components to generate based on the processed text:")
                cols_checkbox = st.columns(2)
                with cols_checkbox[0]:
                    cb_summary = st.checkbox("🗺️ Summary & MindMap", value=True, key="cb_sum_val_tab1")
                    cb_tweet = st.checkbox("📺 Tweet MindMap", value=False, key="cb_tweet_val_tab1")
                    cb_ioc = st.checkbox("🧐 Extract IOCs", value=True, key="cb_ioc_val_tab1")
                    cb_5whats = st.checkbox("❓ Threat Scope (5 Whats)", value=True, key="cb_5w_val_tab1")
                with cols_checkbox[1]:
                    cb_ttps = st.checkbox("📊 TTPs Overview Table", value=True, key="cb_ttps_table_val_tab1")
                    cb_ttps_by_time = st.checkbox("🕰️ TTPs by Execution Time", value=True, key="cb_ttps_time_val_tab1")
                    cb_ttps_timeline = st.checkbox("📈 TTPs Graphic Timeline", value=True, key="cb_ttps_graph_val_tab1")
                    cb_navigator = st.checkbox("🗺️ MITRE Navigator Layer", value=True, key="cb_nav_val_tab1")
                
                submit_button_tab1_generate = st.form_submit_button(":gear: :orange[**Generate Selected Components**]")

            if submit_button_tab1_generate and client:
                text_content = st.session_state.get('text', "") # Use processed text
                selected_lang = st.session_state.selected_language
                service_sel = st.session_state.service_selection
                # global `deployment_name` is used by AI functions
                
                with st.spinner("Checking content relevance..."):
                    relevance_check = ai_check_content_relevance(text_content, client, service_sel, deployment_name)
                
                if "not related to cybersecurity" in relevance_check.lower() and "not cti" in relevance_check.lower():
                    st.warning(f"Content might not be related to cybersecurity. AI classified it as: {relevance_check}")
                else:
                    st.success(f"Content appears relevant: {relevance_check}")
                    mindmap_prompt_prefix = f"Generate a {st.session_state.selected_mindmap_option} MindMap only using the text below:\n"
                    input_text_for_mindmap = mindmap_prompt_prefix + text_content

                    if cb_summary:
                        with st.spinner("Generating Summary & Main MindMap..."):
                            st.session_state.summary = ai_summarise(text_content, client, service_sel, selected_lang, deployment_name)
                            if st.session_state.selected_mindmap_option == "Mermaid":
                                mm_code = ai_run_models(input_text_for_mindmap, client, selected_lang, service_sel, deployment_name)
                                st.session_state.mindmap_code = add_mermaid_theme(mm_code, st.session_state.selected_theme_option)
                            else: 
                                st.session_state.mindmap_code = ai_run_models_markmap(input_text_for_mindmap, client, selected_lang, service_sel, deployment_name)
                    
                    if cb_tweet:
                        with st.spinner("Generating Tweet & Tweet MindMap..."):
                            st.session_state.summary_tweet = ai_summarise_tweet(text_content, client, service_sel, selected_lang, deployment_name)
                            tweet_mm_code = ai_run_models_tweet(input_text_for_mindmap, client, selected_lang, service_sel, deployment_name) 
                            st.session_state.tweet_mindmap_code = add_mermaid_theme(tweet_mm_code, st.session_state.selected_theme_option)

                    if cb_ioc:
                        with st.spinner("Extracting IOCs..."):
                            st.session_state.iocs_df = ai_extract_iocs(text_content, client, service_sel, deployment_name)
                    
                    if cb_ttps:
                        with st.spinner("Extracting TTPs Overview Table..."):
                            st.session_state.ttptable = ai_ttp(text_content, client, service_sel, deployment_name)
                    
                    if cb_ttps_by_time:
                        with st.spinner("Ordering TTPs by Execution Time..."):
                            current_ttps_table = st.session_state.get('ttptable', "") 
                            st.session_state.attackpath = ai_ttp_list(text_content, current_ttps_table, client, service_sel, deployment_name)
                    
                    if cb_ttps_timeline:
                        with st.spinner("Generating TTPs Graphic Timeline..."):
                            st.session_state.mermaid_timeline = ai_ttp_graph_timeline(text_content, client, service_sel, deployment_name)
                    
                    if cb_5whats:
                        with st.spinner("Generating 5 Whats Report..."):
                            st.session_state['5whats'] = ti_5whats.ai_fivewhats(text_content, client, service_sel, deployment_name)

                    if cb_navigator:
                        with st.spinner("Generating MITRE Navigator Layer..."):
                            current_ttps_table_for_nav = st.session_state.get('ttptable', "")
                            mitre_json_str = ti_navigator.attack_layer(text_content, current_ttps_table_for_nav, client, service_sel, deployment_name)
                            st.session_state.mitre_layer_json_str = mitre_json_str
                            if mitre_json_str and GITHUB_TOKEN: 
                                try:
                                    mitre_json_dict = json.loads(mitre_json_str)
                                    raw_url_nav = upload_to_github(mitre_json_dict, "mitre-navigator")
                                    st.session_state.mitre_navigator_raw_url = raw_url_nav
                                except json.JSONDecodeError:
                                    st.error("Generated MITRE layer is not valid JSON. Cannot upload.")
                st.success("Selected components generated!")
            
            st.markdown("---")
            st.subheader("Generated Report Components:")
            # Display full original text if it was a URL source (markdown formatted)
            if st.session_state.get('input_source_type') == 'URL' and st.session_state.get('full_original_text'):
                with st.expander("Full Scraped Article (Markdown)", expanded=False):
                    st.markdown(st.session_state.full_original_text) # Show full original scraped text
            
            if st.session_state.get('summary'):
                st.markdown("### 🗺️ AI-Generated Summary")
                st.markdown(st.session_state.summary)
            
            if st.session_state.get('mindmap_code'):
                st.markdown(f"### 🧠 {st.session_state.selected_mindmap_option} MindMap Visualization")
                if st.session_state.selected_mindmap_option == "Mermaid":
                    st_html(mermaid_chart_png(st.session_state.mindmap_code), width=1500, height=1500, scrolling=True)
                    st.link_button("Open Main MindMap in Mermaid.live", genPakoLink(st.session_state.mindmap_code))
                else: 
                    markmap(st.session_state.mindmap_code, height=700)
                with st.expander(f"View {st.session_state.selected_mindmap_option} Code"):
                    st.code(st.session_state.mindmap_code, language='mermaid' if st.session_state.selected_mindmap_option == "Mermaid" else 'markdown')
            
            if st.session_state.get('summary_tweet'):
                st.markdown("### 📺 Suggested Tweet")
                tweet_text_area_val = st.session_state.get('summary_tweet', '') # Ensure it has a default
                tweet_text_area = st.text_area("Edit Tweet:", value=tweet_text_area_val, height=100, key="tweet_edit_area_tab1")
                if st.session_state.get('tweet_mindmap_code'):
                    st.markdown("##### Tweet MindMap Visual:")
                    st_html(mermaid_chart_png(st.session_state.tweet_mindmap_code), width=700, height=700, scrolling=True)
                    with st.expander("View Tweet MindMap Code"):
                        st.code(st.session_state.tweet_mindmap_code, language='mermaid')
                
                # Use st.session_state.url4 which now holds the source identifier
                source_link_for_tweet = ""
                if st.session_state.get('input_source_type') == 'URL' and st.session_state.get('url4','').startswith('http'):
                    source_link_for_tweet = st.session_state.get('url4', '')
                
                tweet_url_param = urllib.parse.quote(tweet_text_area + ' ' + source_link_for_tweet)
                st.link_button("Post on X (formerly Twitter)", f"https://twitter.com/intent/tweet?text={tweet_url_param}")

            iocs_display_df = st.session_state.get('iocs_df')
            if iocs_display_df is not None: # Check for None explicitly
                st.markdown("### 🧐 Extracted Indicators of Compromise (IOCs)")
                if isinstance(iocs_display_df, pd.DataFrame) and not iocs_display_df.empty:
                    st.dataframe(iocs_display_df)
                elif isinstance(iocs_display_df, str) and iocs_display_df.strip(): # If it's a string message
                    st.info(iocs_display_df)
                else: # Handles empty DataFrame or empty string
                    st.info("No IOCs were extracted or found.")
            
            if st.session_state.get('ttptable'):
                st.markdown("### 📊 TTPs Overview Table")
                st.markdown(st.session_state.ttptable) 
            
            if st.session_state.get('attackpath'):
                st.markdown("### 🕰️ TTPs Ordered by Execution Time")
                st.markdown(st.session_state.attackpath)
            
            if st.session_state.get('mermaid_timeline'):
                st.markdown("### 📈 TTPs Graphic Timeline")
                st_html(mermaid_timeline_graph(st.session_state.mermaid_timeline), width=1500, height=600, scrolling=True)
                st.link_button("Open TTP Timeline in Mermaid.live", genPakoLink(st.session_state.mermaid_timeline))
                with st.expander("View TTP Timeline Mermaid Code"):
                    st.code(st.session_state.mermaid_timeline, language='mermaid')
            
            if st.session_state.get('5whats'):
                st.markdown("### ❓ Threat Scope Report (5 Whats)")
                st.markdown(st.session_state['5whats'])
            
            if st.session_state.get('mitre_layer_json_str'):
                st.markdown("### 🗺️ MITRE ATT&CK® Navigator Layer")
                try:
                    # Validate if it's JSON before displaying with st.json
                    json.loads(st.session_state.mitre_layer_json_str)
                    st.json(st.session_state.mitre_layer_json_str)
                except json.JSONDecodeError:
                    st.error("MITRE Layer data is not valid JSON. Raw data:")
                    st.text(st.session_state.mitre_layer_json_str)

                if st.session_state.get('mitre_navigator_raw_url'):
                    navigator_iframe_url = f"https://mitre-attack.github.io/attack-navigator/#layerURL={st.session_state.mitre_navigator_raw_url}"
                    st_html(f'<iframe src="{navigator_iframe_url}" width="100%" height="800px" style="border:none;"></iframe>', height=820)
                else:
                    st.warning("MITRE layer generated but could not be uploaded for live view (GitHub token might be missing/invalid).")

    # --- TAB 2: AI Chat ---
    with tab2:
        st.header("💬 AI Chat with Processed Data")
        # Use st.session_state.text (potentially truncated) for knowledge base
        chat_text_source = st.session_state.get('text', "")
        if not chat_text_source.strip():
            st.info("Please provide content and analyze it from the main page first.")
        elif not client:
            st.warning("AI Service not configured. Cannot start chat.")
        else:
            if st.session_state.get('knowledge_base') is None or \
               st.session_state.get('knowledge_base_source_text') != chat_text_source:
                with st.spinner("Processing text for chat knowledge base..."):
                    current_embedding_deployment = embedding_deployment_name if st.session_state.service_selection == "Azure OpenAI" else None
                    st.session_state.knowledge_base = ai_process_text(
                        chat_text_source, 
                        st.session_state.service_selection, 
                        azure_api_key if st.session_state.service_selection == "Azure OpenAI" else None,
                        azure_endpoint if st.session_state.service_selection == "Azure OpenAI" else None,
                        current_embedding_deployment,
                        openai_api_key if st.session_state.service_selection == "OpenAI" else None,
                        mistral_api_key if st.session_state.service_selection == "MistralAI" else None
                    )
                    st.session_state.knowledge_base_source_text = chat_text_source
            
            for message in st.session_state.chat_history:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])
            
            prompt = st.chat_input("Ask something about the processed content...", key=f"chat_input_tab2_{st.session_state.input_key}")
            if prompt:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.spinner("AI is thinking..."):
                    ai_response = ai_get_response(
                        st.session_state.get('knowledge_base'), 
                        prompt, 
                        st.session_state.service_selection,
                        azure_api_key if st.session_state.service_selection == "Azure OpenAI" else None,
                        azure_endpoint if st.session_state.service_selection == "Azure OpenAI" else None,
                        deployment_name, # Global deployment name
                        openai_api_key if st.session_state.service_selection == "OpenAI" else None,
                        mistral_api_key if st.session_state.service_selection == "MistralAI" else None
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                with st.chat_message("assistant"):
                    st.markdown(ai_response)

    # --- TAB 3: PDF Report ---
    with tab3:
        st.header("📄 Generate PDF Report")
        if not st.session_state.get('text', "").strip(): # Check if any analysis has been done
            st.info("Please provide content, analyze it, and generate components in the 'Main Report Generation' tab first.")
        else:
            with st.form("form_pdf_generation_tab3"):
                current_pdf_orientation_index = ["portrait", "landscape"].index(st.session_state.pdf_orientation_choice)
                st.session_state.pdf_orientation_choice = st.selectbox(
                    "PDF Orientation:", options=["portrait", "landscape"],
                    index=current_pdf_orientation_index,
                    key='pdf_orientation_selector_tab3'
                )
                st.caption("The PDF will include all components generated in the 'Main Report Generation' tab.")
                submit_button_pdf = st.form_submit_button(label="📥 :orange[**Generate & Download PDF**]")

            if submit_button_pdf:
                if not client: 
                    st.error("AI Service client not initialized. Cannot ensure all data is available for PDF.")
                else:
                    pdf_data_args = {
                        "url": st.session_state.get('url4', "N/A"), # url4 is the source identifier
                        "summary_content": st.session_state.get('summary', ""),
                        "mindmap_mermaid_code": st.session_state.get('mindmap_code', "") if st.session_state.selected_mindmap_option == "Mermaid" else "",
                        # Add Markmap data to PDF if selected and if ti_pdf supports it
                        # "mindmap_markmap_code": st.session_state.get('mindmap_code', "") if st.session_state.selected_mindmap_option == "Markmap" else "",
                        "iocs_data": st.session_state.get('iocs_df', pd.DataFrame()), 
                        "ttps_overview_data": st.session_state.get('ttptable', ""),
                        "attack_path_data": st.session_state.get('attackpath', ""),
                        "mermaid_timeline_code": st.session_state.get('mermaid_timeline', ""),
                        "five_whats_data": st.session_state.get('5whats', ""),
                        "orientation": st.session_state.pdf_orientation_choice
                    }
                    has_reportable_content = any([
                        pdf_data_args["summary_content"].strip(),
                        pdf_data_args["mindmap_mermaid_code"].strip(),
                        # pdf_data_args["mindmap_markmap_code"].strip(), # if you add markmap to PDF
                        isinstance(pdf_data_args["iocs_data"], pd.DataFrame) and not pdf_data_args["iocs_data"].empty or bool(pdf_data_args["iocs_data"]),
                        pdf_data_args["ttps_overview_data"].strip(),
                        pdf_data_args["attack_path_data"].strip(),
                        pdf_data_args["mermaid_timeline_code"].strip(),
                        pdf_data_args["five_whats_data"].strip()
                    ])
                    if not has_reportable_content:
                        st.warning("No significant content generated in 'Main Report Generation' tab to include in the PDF.")
                    else:
                        with st.spinner("Generating PDF report... This may take a moment."):
                            pdf_bytes = ti_pdf.create_pdf_bytes(**pdf_data_args) # Ensure ti_pdf can handle these args
                        if pdf_bytes:
                            current_time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            pdf_file_name = f"TI_Mindmap_Report_{current_time_str}.pdf"
                            st.download_button(
                                label="✅ Download PDF Report", data=pdf_bytes,
                                file_name=pdf_file_name, mime='application/pdf'
                            )
                            st.success("PDF report generated!")
                        else:
                            st.error("Failed to generate PDF report. Check application logs or ensure `ti_pdf` module is correctly configured.")
    
    # --- TAB 4: Screenshot ---
    with tab4:
        st.header("🖼️ Website Screenshot")
        is_url_input_type = st.session_state.get('input_source_type') == "URL"
        current_source_id = st.session_state.get('url4', "") # url4 holds the source identifier

        if not is_url_input_type or not current_source_id.startswith(('http://', 'https://')):
            st.info("Screenshot functionality is only available when a URL is analyzed.")
        else:
            # current_source_id is the URL to screenshot
            api_key_thumb = st.secrets.get("api_keys", {}).get("thumbnail")
            if not api_key_thumb:
                st.warning("Thumbnail API key not configured in secrets. Cannot fetch screenshot.")
            else:
                with st.spinner(f"Fetching screenshot of {current_source_id}..."):
                    try:
                        # Ensure the URL is properly encoded for the API call
                        encoded_url = urllib.parse.quote(current_source_id, safe='/:')
                        screenshot_api_url = f"https://api.thumbnail.ws/api/{api_key_thumb}/thumbnail/get?url={encoded_url}&width=1280&delay=2000"
                        screenshot_resp = requests.get(screenshot_api_url, timeout=30)
                        screenshot_resp.raise_for_status()
                        st.image(screenshot_resp.content, caption=f"Screenshot of {current_source_id}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to get screenshot: {e}")
                    except Exception as e: # Catch any other unexpected errors
                        st.error(f"An unexpected error occurred while fetching screenshot: {e}")

    # --- TAB 5: STIX 2.1 ---
    with tab5:
        st.header("🛡️ STIX 2.1 Threat Report Generator (Beta)")
        stix_text_source = st.session_state.get('text', "") # Use processed text
        if not stix_text_source.strip():
            st.info("Please provide content and analyze it from the main page first. STIX generation requires processed text.")
        elif not client:
            st.warning("AI Service not configured. Cannot generate STIX objects.")
        else:
            with st.form("form_stix_generation_tab5"):
                st.checkbox("Generate STIX 2.1 Bundle (SDOs, SCOs, SROs)", value=True, key="cb_stix_bundle_val_tab5", disabled=True) 
                submit_button_stix = st.form_submit_button(":orange[**Generate STIX Bundle**]")
            
            if submit_button_stix:
                service_sel_stix = st.session_state.service_selection
                # Global `deployment_name` is used by ti_stix functions
                
                with st.spinner("Generating STIX Domain Objects (SDOs)..."):
                    stix_sdo_json_str = ti_stix.sdo_stix(stix_text_source, client, service_sel_stix, deployment_name)
                    try:
                        stix_sdo_list = json.loads(stix_sdo_json_str)
                        stix_sdo_list = ti_stix.add_uuid_to_ids(stix_sdo_list) 
                        st.session_state.stix_sdo = json.dumps(stix_sdo_list, indent=4)
                    except Exception as e:
                        st.error(f"Error processing SDOs: {e}. Raw SDO JSON: {stix_sdo_json_str}")
                        st.session_state.stix_sdo = stix_sdo_json_str # Store raw on error
                if st.session_state.get('stix_sdo'):
                    with st.expander("View Generated SDOs (JSON)"): st.json(st.session_state.stix_sdo)

                with st.spinner("Generating STIX Cyber-observable Objects (SCOs)..."):
                    stix_sco_json_str = ti_stix.sco_stix(stix_text_source, client, service_sel_stix, deployment_name)
                    try:
                        stix_sco_list = json.loads(stix_sco_json_str)
                        stix_sco_list = ti_stix.add_uuid_to_ids(stix_sco_list)
                        st.session_state.stix_sco = json.dumps(stix_sco_list, indent=4)
                    except Exception as e:
                        st.error(f"Error processing SCOs: {e}. Raw SCO JSON: {stix_sco_json_str}")
                        st.session_state.stix_sco = stix_sco_json_str
                if st.session_state.get('stix_sco'):
                    with st.expander("View Generated SCOs (JSON)"): st.json(st.session_state.stix_sco)
                
                if st.session_state.get('stix_sdo') and st.session_state.get('stix_sco'):
                    with st.spinner("Generating STIX Relationship Objects (SROs)..."):
                        stix_sro_json_str = ti_stix.sro_stix(stix_text_source, st.session_state.stix_sdo, st.session_state.stix_sco, client, service_sel_stix, deployment_name)
                        try:
                            stix_sro_list = json.loads(stix_sro_json_str)
                            stix_sro_list = ti_stix.add_uuid_to_ids(stix_sro_list)
                            st.session_state.stix_sro = json.dumps(stix_sro_list, indent=4)
                        except Exception as e:
                            st.error(f"Error processing SROs: {e}. Raw SRO JSON: {stix_sro_json_str}")
                            st.session_state.stix_sro = stix_sro_json_str 
                    if st.session_state.get('stix_sro'):
                        with st.expander("View Generated SROs (JSON)"): st.json(st.session_state.stix_sro)

                    with st.spinner("Creating STIX Bundle..."):
                        try:
                            # Ensure inputs to remove_brackets are valid JSON strings before parsing
                            sdo_obj_list = []
                            if st.session_state.stix_sdo and isinstance(st.session_state.stix_sdo, str):
                                sdo_obj_list = json.loads(ti_stix.remove_brackets(st.session_state.stix_sdo))
                            
                            sco_obj_list = []
                            if st.session_state.stix_sco and isinstance(st.session_state.stix_sco, str):
                                sco_obj_list = json.loads(ti_stix.remove_brackets(st.session_state.stix_sco))

                            sro_obj_list = []
                            if st.session_state.stix_sro and isinstance(st.session_state.stix_sro, str):
                                sro_obj_list = json.loads(ti_stix.remove_brackets(st.session_state.stix_sro))
                                
                            stix_bundle_str = ti_stix.create_stix_bundle(sdo_obj_list, sco_obj_list, sro_obj_list)
                            st.session_state.stix_bundle = stix_bundle_str
                        except Exception as e:
                            st.error(f"Error creating STIX bundle: {e}")
                            st.session_state.stix_bundle = "" 

                if st.session_state.get('stix_bundle'):
                    st.markdown("### STIX 2.1 Bundle")
                    with st.expander("View Full STIX Bundle (JSON)"):
                        st.json(st.session_state.stix_bundle)
                    if GITHUB_TOKEN:
                        with st.spinner("Uploading STIX Bundle to GitHub for visualization..."):
                            try:
                                stix_bundle_dict = json.loads(st.session_state.stix_bundle)
                                raw_url_stix = upload_to_github(stix_bundle_dict, "stix-bundles")
                                if raw_url_stix:
                                    stix_viz_url = f"https://oasis-open.github.io/cti-stix-visualization/?url={raw_url_stix}"
                                    st.markdown("#### STIX Visualizer")
                                    st_html(f'<iframe src="{stix_viz_url}" width="100%" height="1000px" style="border:none;"></iframe>', height=1020)
                            except Exception as e:
                                st.error(f"Could not upload/visualize STIX bundle: {e}")
                    else:
                        st.warning("GitHub token not configured. Cannot upload STIX bundle for live visualization.")

    # --- TAB 6: Original Input Content ---
    with tab6:
        st.header("📝 Original Input Content")
        original_content = st.session_state.get('full_original_text', "")
        source_name = st.session_state.get('url4', "the selected source") # url4 holds the identifier

        if original_content.strip():
            st.markdown(f"Below is the full original content from **{source_name}**.")
            
            if len(original_content) > len(st.session_state.get('text', '')):
                st.caption(":information_source: _Note: For AI processing, a truncated version of this content may have been used due to length._")

            # If original was from URL, it's already markdown. Otherwise, it's raw text.
            if st.session_state.get('input_source_type') == 'URL':
                st.markdown("_(Scraped content below is in Markdown format)_")
                st.text_area("Content (Markdown)", value=original_content, height=600, key="markdown_display_area_tab6")
            else:
                st.text_area("Content (Raw Text)", value=original_content, height=600, key="raw_text_display_area_tab6")
            
            current_time_str_txt = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_source_name_part = "".join(c if c.isalnum() else "_" for c in source_name.split(':')[-1].strip()[:30])
            text_file_name = f"TI_Mindmap_Original_Content_{safe_source_name_part}_{current_time_str_txt}.txt"
            
            try:
                st.download_button(
                    label="📥 Download Original Content",
                    data=original_content.encode('utf-8', errors='replace'),
                    file_name=text_file_name,
                    mime="text/plain"
                )
            except Exception as e:
                st.error(f"Error preparing download for original content: {e}")
        else:
            st.info("No content processed yet. Please use one of the input methods on the main page.")

else: 
    st.info("👋 Welcome to TI Mindmap! Select an input source above and click 'Analyze' to begin.")