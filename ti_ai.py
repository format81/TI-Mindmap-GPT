import streamlit as st
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.callbacks import get_openai_callback
from langchain_community.vectorstores import FAISS
#from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, OpenAI as langchainOAI, OpenAIEmbeddings
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings, OpenAIEmbeddings, ChatOpenAI as langchainChatOpenAI
from langchain_mistralai.chat_models import ChatMistralAI as langchainMistralChat # Renamed for clarity
from langchain_mistralai import MistralAIEmbeddings
import pandas as pd
from mistralai.models.chat_completion import ChatMessage # For direct Mistral client
import hashlib
import os

# --- Constants ---
OPENAI_DEFAULT_MODEL = "gpt-4o-2024-08-06" # Using the newer model
MISTRAL_DEFAULT_CHAT_MODEL = "mistral-large-latest" # Default for direct Mistral chat
MISTRAL_DEFAULT_EMBED_MODEL = "mistral-embed" # Default for Mistral embeddings

# --- Langsmith Configuration ---
# Accessing the secrets from the [default] section (ensure these are in st.secrets)
langchain_tracing_v2 = st.secrets.get("api_keys", {}).get("LANGCHAIN_TRACING_V2", "false") # Default to false if not set
langchain_endpoint = st.secrets.get("api_keys", {}).get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
langchain_api_key = st.secrets.get("api_keys", {}).get("LANGCHAIN_API_KEY", "")
langchain_project = st.secrets.get("api_keys", {}).get("LANGCHAIN_PROJECT", "Default TI Mindmap")

# Setting the environment variables
os.environ["LANGCHAIN_TRACING_V2"] = langchain_tracing_v2
if langchain_endpoint: os.environ["LANGCHAIN_ENDPOINT"] = langchain_endpoint
if langchain_api_key: os.environ["LANGCHAIN_API_KEY"] = langchain_api_key
if langchain_project: os.environ["LANGCHAIN_PROJECT"] = langchain_project

from langsmith import traceable # Import after setting env vars

# --- Helper Functions ---

def get_model_name(ai_service_provider, deployment_name=None, default_openai_model=OPENAI_DEFAULT_MODEL, default_mistral_model=MISTRAL_DEFAULT_CHAT_MODEL):
    """Determines the appropriate model name based on the AI service provider."""
    if ai_service_provider == "OpenAI":
        return default_openai_model
    elif ai_service_provider == "Azure OpenAI":
        if not deployment_name:
            raise ValueError("Deployment name is required for Azure OpenAI.")
        return deployment_name
    elif ai_service_provider == "MistralAI":
        # If deployment_name is provided (from timindmapgpt.py, where it's set to the Mistral model name), use it.
        # Otherwise, fall back to a default Mistral model.
        return deployment_name if deployment_name else default_mistral_model
    else:
        raise ValueError(f"Unsupported AI service provider: {ai_service_provider}")

# --- AI Function Definitions ---

@traceable
def ai_summarise_tweet(input_text, client, ai_service_provider, selected_language, deployment_name=None):
    """Summarizes text for a short tweet."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for tweet summary."
    
    language = ", ".join(selected_language) if selected_language else "English"
    system_message = (
        f"You are creating a concise tweet in {language} for a Threat Analyst. "
        f"Summarize the main topic and key findings relevant to a threat analyst in 250 characters or less. "
        f"Include a relevant emoji and the hashtag #TIMindmapGPT."
    )
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_text},
                ],
                max_tokens=70 # Max tokens for a short tweet
            )
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            chat_response = client.chat(
                model=model_to_use, # Use the determined model
                messages=[
                    ChatMessage(role="system", content=system_message),
                    ChatMessage(role="user", content=input_text),
                ],
                max_tokens=70
            )
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error generating tweet summary: {e}"

@traceable
def ai_summarise(input_text, client, ai_service_provider, selected_language, deployment_name=None):
    """Summarizes a long text for a Threat Analyst."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for summary."
        
    language = ", ".join(selected_language) if selected_language else "English"
    system_message = (
        f"You are summarizing a threat report in {language} for a Threat Analyst. "
        "Create a detailed summary covering the main topic, key findings, IOCs, and TTPs. "
        "Use paragraphs, include a title, and add a relevant emoji. Avoid bullet points."
    )
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)

        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_text},
                ],
            )
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            chat_response = client.chat(
                model=model_to_use,
                messages=[
                    ChatMessage(role="system", content=system_message),
                    ChatMessage(role="user", content=input_text),
                ],
            )
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error generating summary: {e}"

@traceable
def ai_check_content_relevance(input_text, client, ai_service_provider, deployment_name=None):
    """Determines if input text is related to cybersecurity."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for relevance check."
        
    # Improved prompt for clearer yes/no and reason
    system_message = (
        "Analyze the following text. Is it primarily related to cybersecurity, cyber threats, "
        "threat intelligence, or information security? Respond with 'Yes' or 'No'. "
        "If 'No', briefly state the main topic."
    )
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)

        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_text}
                ],
                max_tokens=50 # Enough for Yes/No and brief reason
            )
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            chat_response = client.chat(
                model=model_to_use,
                messages=[
                    ChatMessage(role="system", content=system_message),
                    ChatMessage(role="user", content=input_text)
                ],
                max_tokens=50
            )
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error checking content relevance: {e}"

# Common system prompt for Mermaid mindmaps (main and tweet)
MERMAID_MINDMAP_SYSTEM_PROMPT_TEMPLATE = (
    "You are creating a Mermaid.js mindmap in {language} for a Threat Analyst. "
    "Visually organize key findings from the text. Guidelines:\n"
    "1. No hyphens or nested parentheses in node text (use dashes or rephrase).\n"
    "2. Limit main node branches to {max_primary_nodes}. These are top themes. Add detailed sub-nodes.\n"
    "3. Use single parentheses `()` for rounded node shapes.\n"
    "4. No icons or emojis.\n"
    "5. No trailing spaces on lines. No parentheses/special chars in chart field names.\n"
    "6. Start with `mindmap` on its own line. No ``` at start/end.\n"
    "7. No `style root` lines. No comments like `#`. Second line must be `root(...)`.\n"
    "8. Escape/avoid special chars in text, e.g., `mail.kz` not `mail[.]kz`.\n"
    "9. Enclose text with dashes if needed, not extra parentheses.\n"
    "10. Example: `(Indicators of compromise - IOC - provided)` not `(Indicators of compromise (IOC) provided)`.\n"
    "11. Report domains like `weinsteinfrog.com`, IPs like `123.234.12.89` (no brackets).\n"
    "12. Do not end lines with `.` before the closing `)`."
)

# Few-shot example for Mermaid mindmaps
MERMAID_MINDMAP_USER_EXAMPLE = (
    "Title: Threat Report Summary: Kazakhstan-associated YoroTrooper disguises origin of attacks as Azerbaijan\n\n"
    "Threat actors known as YoroTrooper, presumably originating from Kazakhstan, have been conducting cyber espionage activities, "
    "largely focusing on Commonwealth of Independent States (CIS) countries..." # Shortened for brevity
)
MERMAID_MINDMAP_ASSISTANT_EXAMPLE = (
    "mindmap\nroot(YoroTrooper Threat Analysis)\n  (Origin and Target)\n    (Likely originates from Kazakhstan)\n    (Mainly targets CIS countries)\n"
    "    (Attempts to make attacks appear from Azerbaijan)\n  (TTPs)\n    (Uses VPN exit points in Azerbaijan)\n"
    "    (Spear phishing via credential-harvesting sites)\n  (Language Proficiency)\n    (Fluency in Kazakh and Russian)\n"
    "  (Malware Use)\n    (Evolved from commodity malware to custom-built malware)"
)

@traceable
def ai_run_models(input_text, client, selected_language, ai_service_provider, deployment_name=None):
    """Generates a detailed Mermaid.js mindmap."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for detailed mindmap."

    language = ", ".join(selected_language) if selected_language else "English"
    system_prompt = MERMAID_MINDMAP_SYSTEM_PROMPT_TEMPLATE.format(language=language, max_primary_nodes="four")
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": MERMAID_MINDMAP_USER_EXAMPLE},
            {"role": "assistant", "content": MERMAID_MINDMAP_ASSISTANT_EXAMPLE},
            {"role": "user", "content": input_text}, # Actual user input for generation
        ]

        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(model=model_to_use, messages=messages)
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            mistral_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
            chat_response = client.chat(model=model_to_use, messages=mistral_messages)
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error generating detailed mindmap: {e}"

@traceable
def ai_run_models_markmap(input_text, client, selected_language, ai_service_provider, deployment_name=None):
    """Generates a Markmap.js mindmap."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for Markmap."
        
    language = ", ".join(selected_language) if selected_language else "English"
    system_prompt = (
        f"You are creating an in-depth MarkMap mindmap in {language}.\n"
        "Organize key Threat Intelligence points. Guidelines (apply to {language}):\n"
        "1. Max 4 primary nodes (top themes).\n"
        "2. Max 4 secondary nodes per primary (context titles).\n"
        "3. Sub-nodes: concise, relevant for threat analysts.\n"
        "4. No icons/emojis. No trailing spaces. No parentheses/special chars in field names.\n"
        "5. Escape/avoid special chars, e.g., `mail.kz` not `mail[.]kz`.\n"
        "6. Enclose text with dashes if needed, not extra parentheses.\n"
        "7. Ensure full MarkMap syntax compliance. No spaces between lines. No ``` at start/end."
    )
    # Simplified few-shot example for Markmap
    markmap_user_example = "Title: UNC2970 Backdoor Deployment\n\nTargets US critical infrastructure..."
    markmap_assistant_example = (
        "# Threat Intelligence\n- UNC2970 Backdoor Deployment\n  - Targets\n    - Victims in US critical infrastructure\n"
        "  - Phishing Tactic\n    - Email and WhatsApp used\n  - Trojanized PDF reader\n    - SumatraPDF"
    )
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markmap_user_example},
            {"role": "assistant", "content": markmap_assistant_example},
            {"role": "user", "content": input_text},
        ]
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(model=model_to_use, messages=messages)
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            mistral_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
            chat_response = client.chat(model=model_to_use, messages=mistral_messages)
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error generating Markmap: {e}"

@traceable
def ai_run_models_tweet(input_text, client, selected_language, ai_service_provider, deployment_name=None):
    """Generates a concise Mermaid.js mindmap for a tweet."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for tweet mindmap."

    language = ", ".join(selected_language) if selected_language else "English"
    system_prompt = MERMAID_MINDMAP_SYSTEM_PROMPT_TEMPLATE.format(language=language, max_primary_nodes="3 or 4") + \
                    "\n13. Keep branches to max 2 sub-branches for conciseness." # Add tweet specific constraint

    # More concise assistant example for tweet mindmap
    tweet_mindmap_assistant_example = (
        "mindmap\nroot(YoroTrooper Analysis)\n  (Origin & Disguise)\n    (Kazakhstan -> Azerbaijan)\n"
        "  (TTPs)\n    (VPNs, Spear Phishing)\n  (Malware)\n    (Custom: Py, PS, Go, Rust)"
    )

    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": MERMAID_MINDMAP_USER_EXAMPLE}, # Can reuse the general user example
            {"role": "assistant", "content": tweet_mindmap_assistant_example},
            {"role": "user", "content": input_text},
        ]
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(model=model_to_use, messages=messages)
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            mistral_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
            chat_response = client.chat(model=model_to_use, messages=mistral_messages)
            return chat_response.choices[0].message.content
    except Exception as e:
        return f"Error generating tweet mindmap: {e}"

@traceable
def create_dataframe_from_response(response_content_str):
    """Creates a pandas DataFrame from a CSV-like string response."""
    if not response_content_str or not response_content_str.strip():
        # st.warning("AI response for IOCs is empty.")
        return pd.DataFrame() # Return empty DataFrame

    try:
        # Split lines and then split by comma, handling potential quotes
        lines = response_content_str.strip().split("\n")
        if not lines:
            return pd.DataFrame()

        header = [h.strip().replace('"', '') for h in lines[0].split(",")]
        
        data_rows = []
        for line in lines[1:]:
            if not line.strip(): continue
            # Simple split by comma, assumes commas in descriptions are handled by LLM or not present
            # A more robust CSV parser might be needed if LLM output is complex
            row_values = [val.strip().replace('"', '') for val in line.split(",")]
            data_rows.append(row_values)

        # Ensure all rows have the same number of columns as the header
        # Pad with empty strings if necessary
        standardized_data = []
        for row in data_rows:
            if len(row) < len(header):
                standardized_data.append(row + [''] * (len(header) - len(row)))
            elif len(row) > len(header):
                 standardized_data.append(row[:len(header)]) # Truncate
            else:
                standardized_data.append(row)
        
        if not standardized_data and not header: # No data at all
             return pd.DataFrame()
        if not standardized_data and header: # Only header, no data
            return pd.DataFrame(columns=header)


        df = pd.DataFrame(standardized_data, columns=header)
        return df
    except Exception as e:
        st.error(f"Error parsing IOCs into DataFrame: {e}. Raw response: '{response_content_str[:200]}...'")
        return pd.DataFrame() # Return empty DataFrame on error

def calculate_sha256(url_string):
    """Calculates SHA256 hash of a URL string."""
    return hashlib.sha256(url_string.encode()).hexdigest()

def update_virus_total_urls(ioc_dataframe):
    """Updates VirusTotal URLs for URL type indicators in the DataFrame."""
    if "Type" not in ioc_dataframe.columns or "Indicator" not in ioc_dataframe.columns:
        # st.warning("IOC DataFrame missing 'Type' or 'Indicator' column for VirusTotal URL update.")
        return ioc_dataframe
    if "Virus Total URL" not in ioc_dataframe.columns:
        ioc_dataframe["Virus Total URL"] = "" # Ensure column exists

    for index, row in ioc_dataframe.iterrows():
        try:
            if row["Type"] == "URL" and pd.notna(row["Indicator"]):
                sha256 = calculate_sha256(str(row["Indicator"]))
                ioc_dataframe.at[index, "Virus Total URL"] = f"https://www.virustotal.com/gui/url/{sha256}"
            # Other types are assumed to be handled by the LLM prompt correctly
        except Exception as e:
            # st.warning(f"Could not update VirusTotal URL for row {index}: {e}")
            pass # Continue processing other rows
    return ioc_dataframe

@traceable
def ai_extract_iocs(input_text, client, ai_service_provider, deployment_name=None):
    """Extracts IOCs from text and returns a pandas DataFrame."""
    if not all([input_text, client, ai_service_provider]):
        return "Error: Invalid input parameters for IOC extraction."

    # Simplified prompt: Python will now construct the SHA256 URL for "URL" types.
    # LLM should focus on extracting Type, Indicator, Description, and basic VT URLs for non-URL types.
    prompt = (
        "Extract IOCs from the provided text for a threat analyst. "
        "Format as CSV: Indicator,Type,Description,Virus Total URL.\n"
        "Types can be: IPv4, Domain, URL, File Hash (MD5), File Hash (SHA1), File Hash (SHA256), Email Address, CVE.\n"
        "For 'Virus Total URL' column:\n"
        "  - If Type is SHA (any kind): https://www.virustotal.com/gui/file/[Indicator]\n"
        "  - If Type is IP: https://www.virustotal.com/gui/ip-address/[Indicator]\n"
        "  - If Type is Domain: https://www.virustotal.com/gui/domain/[Indicator]\n"
        "  - For Type URL: Leave this column BLANK or put 'N/A'. It will be calculated later.\n"
        "Remove brackets from IPs, URLs, domains (e.g., 'hxxp://example[.]com' becomes 'http://example.com'). \n"
        "No extra text, return just the CSV content. No '''\n"
    )
    
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        response_content_str = ""

        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "system", "content": prompt},
                          {"role": "user", "content": input_text}]
            )
            response_content_str = response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            chat_response = client.chat(
                model=model_to_use,
                messages=[
                    ChatMessage(role="system", content=prompt),
                    ChatMessage(role="user", content=input_text)
                ]
            )
            response_content_str = chat_response.choices[0].message.content
        
        if not response_content_str or "no iocs found" in response_content_str.lower() or "no indicators found" in response_content_str.lower() :
            return pd.DataFrame(columns=["Indicator", "Type", "Description", "Virus Total URL"]) # Return empty DF with headers

        ioc_dataframe = create_dataframe_from_response(response_content_str)
        
        if not ioc_dataframe.empty:
            ioc_dataframe = update_virus_total_urls(ioc_dataframe) # Call the helper function
        return ioc_dataframe
    except Exception as e:
        return f"Error extracting IOCs: {e}"


@traceable
def ai_ttp(text, client, ai_service_provider, deployment_name=None):
    """Extracts TTPs and formats them as a Markdown table string."""
    if not all([text, client, ai_service_provider]):
        return "Error: Invalid input parameters for TTP extraction."

    user_prompt_ttp = (
        "Using the ATT&CK Matrix for Enterprise, extract Tactics, Techniques, and Procedures (TTPs) "
        "from the provided text. For each identified technique, include its ID, tactic, and relevant "
        "comments/context derived from the text. Focus on the most important TTPs.\n"
        "Format the output as a Markdown table with columns: Technique, Technique ID, Tactic, Comment.\n"
        f"The text to analyze is: {text}"
    )
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": user_prompt_ttp}],
            )
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            response = client.chat(
                model=model_to_use,
                messages=[ChatMessage(role="user", content=user_prompt_ttp)],
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"Error extracting TTPs table: {e}"

@traceable
def ai_ttp_list(text, ttptable_str, client, ai_service_provider, deployment_name=None):
    """Generates a list of TTPs ordered by perceived execution time."""
    if not all([text, client, ai_service_provider]): # ttptable_str can be empty
        return "Error: Invalid input parameters for TTP list."

    system_prompt_ttp_list = (
        "You are an AI expert in cybersecurity, threat intelligence, and MITRE ATT&CK. "
        "Your task is to list TTPs ordered by their perceived execution time based on the provided text and TTP table."
    )
    user_prompt_ttp_list = (
        f"Based on the following text: '{text}' \n\nAnd this TTP information (if available): '{ttptable_str}'\n\n"
        "Provide a list of TTPs ordered by their likely execution time. "
        "Each line should include only the Tactic and Technique name, with the Technique ID in brackets. "
        "Use MITRE ATT&CK Enterprise tactics: Reconnaissance, Resource Development, Initial Access, Execution, "
        "Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, "
        "Collection, Command and Control, Exfiltration, Impact."
    )
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        messages = [
            {"role": "system", "content": system_prompt_ttp_list},
            {"role": "user", "content": user_prompt_ttp_list},
        ]
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(model=model_to_use, messages=messages)
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            mistral_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
            response = client.chat(model=model_to_use, messages=mistral_messages)
            return response.choices[0].message.content
    except Exception as e:
        return f"Error generating TTP execution list: {e}"

# Example TTP timeline and Mermaid code for few-shot prompting (can be moved to a config or constants file)
EXAMPLE_TTPS_TIMELINE_TEXT = """
1. Initial Access: Exploitation of Remote Services [T1210]
2. Execution: Command and Scripting Interpreter: PowerShell [T1059.001]
3. Persistence: External Remote Services [T1133]
... (shortened for brevity)
16. Impact: Data Encrypted for Impact [T1486]
"""
EXAMPLE_MERMAID_TIMELINE_CODE = """
timeline
    title Lazarus Group Operation Blacksmith
    Initial Access
    : Exploitation of Remote Services - [T1210]
    Execution
    : Command and Scripting Interpreter - PowerShell - [T1059.001]
    Persistence
    : External Remote Services - [T1133]
    Impact: Data Encrypted for Impact - [T1486]
"""

@traceable
def ai_ttp_graph_timeline(text_content, client, ai_service_provider, deployment_name=None):
    """Generates a Mermaid.js timeline graph for TTPs."""
    if not all([text_content, client, ai_service_provider]):
        return "Error: Invalid input parameters for TTP timeline graph."

    user_prompt_ttp_graph_timeline = (
        f"Generate a Mermaid.js timeline graph illustrating a cyber attack's stages based on TTPs in the following text: '{text_content}'.\n"
        f"Example TTPs: '{EXAMPLE_TTPS_TIMELINE_TEXT}'\nExample Mermaid Output: '{EXAMPLE_MERMAID_TIMELINE_CODE}'\n"
        "Guidelines:\n"
        "1. Start with `timeline`. Title with `title: Your Title`.\n"
        "2. Each step on a new line: `Description : Detail - [Optional Tactic ID]`.\n"
        "3. Use MITRE ATT&CK Enterprise tactics.\n"
        "4. Output only Mermaid.js code. No ```."
    )
    try:
        model_to_use = get_model_name(ai_service_provider, deployment_name)
        messages = [{"role": "user", "content": user_prompt_ttp_graph_timeline}]
        if ai_service_provider in ["OpenAI", "Azure OpenAI"]:
            response = client.chat.completions.create(model=model_to_use, messages=messages)
            return response.choices[0].message.content
        elif ai_service_provider == "MistralAI":
            mistral_messages = [ChatMessage(role="user", content=user_prompt_ttp_graph_timeline)]
            response = client.chat(model=model_to_use, messages=mistral_messages)
            return response.choices[0].message.content
    except Exception as e:
        return f"Error generating TTP timeline graph: {e}"


# --- Langchain QA Functions ---
@traceable
def ai_process_text(text, service_selection, azure_api_key, azure_endpoint, azure_embedding_deployment, openai_api_key, mistral_api_key):
    """Processes text and creates a FAISS knowledge base for Langchain QA."""
    if not text or not text.strip():
        st.warning("Input text for AI processing is empty.")
        return None
    
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len)
    chunks = text_splitter.split_text(text)
    if not chunks:
        st.warning("Text splitting resulted in no chunks.")
        return None

    embeddings_object = None
    try:
        if service_selection == "OpenAI":
            if not openai_api_key: raise ValueError("OpenAI API key not provided.")
            embeddings_object = OpenAIEmbeddings(openai_api_key=openai_api_key)
        elif service_selection == "Azure OpenAI":
            if not all([azure_api_key, azure_endpoint, azure_embedding_deployment]): 
                raise ValueError("Azure API key, endpoint, or embedding deployment name not provided.")
            embeddings_object = AzureOpenAIEmbeddings(
                deployment=azure_embedding_deployment,
                model="text-embedding-ada-002", # Often a default, confirm this is your deployed embedding model name
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                chunk_size=1, # Recommended for AzureOpenAIEmbeddings
                api_version="2024-02-15-preview" # Or your preferred API version
            )
        elif service_selection == "MistralAI":
            if not mistral_api_key: raise ValueError("MistralAI API key not provided.")
            embeddings_object = MistralAIEmbeddings(mistral_api_key=mistral_api_key, model=MISTRAL_DEFAULT_EMBED_MODEL)
        else:
            raise ValueError(f"Invalid AI service selection for embeddings: {service_selection}")

        if embeddings_object:
            knowledge_base = FAISS.from_texts(chunks, embeddings_object)
            return knowledge_base
        else:
            st.error("Failed to initialize embeddings object.")
            return None
    except Exception as e:
        st.error(f"Error processing text for AI Chat: {e}")
        return None

#@traceable
def ai_get_response(knowledge_base, query, service_selection, azure_api_key, azure_endpoint, deployment_name, openai_api_key, mistral_api_key):
    """Gets a response from the Langchain QA chain."""
    if not knowledge_base:
        return "Knowledge base not initialized. Please process text first."
    if not query or not query.strip():
        return "Please enter a query."

    docs = knowledge_base.similarity_search(query, k=3) # Get top 3 relevant docs
    if not docs:
        return "Could not find relevant information in the document for your query."

    llm = None
    try:
        #if service_selection == "OpenAI":
        #    if not openai_api_key: raise ValueError("OpenAI API key not provided.")
        #    llm = langchainOAI(openai_api_key=openai_api_key, model_name=OPENAI_DEFAULT_MODEL, temperature=0.7)
        if service_selection == "OpenAI":
            if not openai_api_key: raise ValueError("OpenAI API key not provided.")
            llm = langchainChatOpenAI(openai_api_key=openai_api_key, model_name=OPENAI_DEFAULT_MODEL, temperature=0.7)
        elif service_selection == "Azure OpenAI":
            if not all([azure_api_key, azure_endpoint, deployment_name]):
                raise ValueError("Azure API key, endpoint, or deployment name not provided.")
            llm = AzureChatOpenAI(
                # model parameter for AzureChatOpenAI is often the deployment name itself, or a specific model if your endpoint supports it.
                # Using deployment_name here as it refers to the chat model deployment.
                model=deployment_name, 
                deployment_name=deployment_name,
                api_key=azure_api_key,
                api_version="2023-07-01-preview", # Or your preferred API version
                azure_endpoint=azure_endpoint,
                temperature=0.7
            )
        elif service_selection == "MistralAI":
            if not mistral_api_key: raise ValueError("MistralAI API key not provided.")
            # `deployment_name` from timindmapgpt.py for MistralAI is the model name
            llm = langchainMistralChat(api_key=mistral_api_key, model=deployment_name if deployment_name else MISTRAL_DEFAULT_CHAT_MODEL, temperature=0.7)
        else:
            raise ValueError(f"Invalid AI service selection for LLM: {service_selection}")

        if llm:
            chain = load_qa_chain(llm, chain_type="stuff") # "stuff" is good for smaller contexts
            with get_openai_callback() as cb: # This callback might primarily track OpenAI/Azure costs
                response = chain.invoke(input={"question": query, "input_documents": docs})
                # st.info(f"QA Chain Cost: {cb}") # Optional: display cost if needed
            return response.get("output_text", "No answer found.")
        else:
            return "LLM not initialized."
    except Exception as e:
        return f"Error getting AI response: {e}"