import requests
from bs4 import BeautifulSoup
import openai
from openai import OpenAI
from openai import AzureOpenAI
import streamlit as st
from streamlit.components.v1 import html
import pandas as pd
import urllib.parse
import os
from uuid import uuid4
import base64

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


# Function to summarize the blog, it work for both OpenAI and Azure OpenAI
def summarise(input_text, client, service_selection, selected_language):
    # Combine the selected languages into a string, or default to "English" if none selected
    language = ", ".join(selected_language) if selected_language else "English"
    if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"You are responsible for summarizing in {language} a threat report for a Threat Analyst. Write a paragraph that will summarize the main topic, the key findings, and all the detailed information relevant for a threat analyst such as detection opportunity iocs and TTPs. Use the title and add an emoji. Do not generate a bullet points list but rather multiple paragraphs."
                },
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"You are responsible for summarizing in {language} a threat report for a Threat Analyst. Write a paragraph that will summarize the main topic, the key findings, and all the detailed information relevant for a threat analyst such as detection opportunity iocs and TTPs. Use the title and add an emoji. Do not generate a bullet points list but rather multiple paragraphs."
                },
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content 

# Function to summarize the blog to create a short tweet, it work for both OpenAI and Azure OpenAI
def summarise_tweet(input_text, client, service_selection, selected_language):
   # Combine the selected languages into a string, or default to "English" if none selected
    language = ", ".join(selected_language) if selected_language else "English"
    if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"You are responsible for creating a short tweet in {language} for a Threat Analyst. Write a tweet summary that contains maximum 250 symbols and will summarize the main topic and the key findings relevant for a threat analyst. you can add an emoji. add tag #timindmap"
                },
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"You are responsible for creating a short tweet in {language} for a Threat Analyst. Write a tweet summary that contains maximum 250 symbols and will summarize the main topic and the key findings relevant for a threat analyst. you can add an emoji. add tag #timindmap"
                },
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content  



# Function to check if content is related to cybersecurity
def check_content_relevance(input_text, client, service_selection):
    prompt = "Determine if the following text is related to cybersecurity: \n" + input_text
    if service_selection == "OpenAI":
         # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
        model = deployment_name,
        messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content

# Function to generate a mindmap
def run_models(input_text, client, selected_language):
    # Combine the selected languages into a string, or default to "English" if none selected
    language = ", ".join(selected_language) if selected_language else "English"
    # Define the SYSTEM prompt with guidelines for creating the mindmap
    system_prompt = (
        f"You are tasked with creating an in-depth mindmap in {language} language designed specifically for a threat analyst. "
        "This mindmap aims to visually organize key findings and crucial highlights from the text. Please adhere to the following guidelines in English but apply the approach to {language}: \n"
        "1. Avoid using hyphens in the text, as they cause errors in the Mermaid.js code. \n"
        "2. Limit the number of primary nodes branching from the main node to four. These primary nodes should encapsulate the top four main themes. Add detailed sub-nodes to elaborate on these themes. \n"
        "3. Incorporate icons where suitable to enhance readability and comprehension. \n"
        "4. You MUST use single parentheses around each node to give them a rounded shape. \n"
        "5. Avoid using icons and emojis. \n "
        "6. Do not insert spaces after the text of each line and do not use parentheses or special characters for the names of the chart fields. \n "
        "7. Start mermaid code with word mindmap, don't use anythong else in first line. \n "
        "8. Don't write ``` as the first and last line. \n"
        "9. Avoid using a line with style root. \n"
        "10. Avoid closing with any comment starting with #. \n"
        "11. Do not use theme as the second line; the second line must start with root syntax. \n"
        "12. Special characters need to be escaped or avoided, like brackets in domain. Example: not use mail[.]kz but use mail.kz. \n"
        "13. When encapsulating text within a line, avoid using additional parentheses as they can introduce ambiguity in Mermaid syntax. Instead, use dashes to enclose your text. \n"
        "14. Instead of using the following approach (Indicators of compromise (IOC) provided), use this: (Indicators of compromise - IOC - provided). \n"
    )
    # Define the USER prompt
    user_prompt = (
        "Title:  Threat Report Summary: Kazakhstan-associated YoroTrooper disguises origin of attacks as Azerbaijan\n\nThreat actors known as YoroTrooper, presumably originating from Kazakhstan, have been conducting cyber espionage activities, largely focusing on Commonwealth of Independent States (CIS) countries. These actors mask their origins, making their attacks appear to come from Azerbaijan. Several tactics, techniques, and procedures (TTPs) were used, including using VPN exit points in Azerbaijan and spear phishing via credential-harvesting sites. They have infiltrated websites and accounts of several government officials between May and August 2023.\n\nThe information supporting that YoroTrooper is likely based in Kazakhstan includes the use of Kazakh currency, fluency in Kazakh and Russian, and the limited targeting of Kazakh entities. Interestingly, YoroTrooper has shown a defensive interest in the website of the Kazakhstani state-owned email service (mail[.]kz), taking precautions to ensure it is not exposed to potential security vulnerabilities. The only Kazakh institution targeted was the government’s Anti-Corruption Agency.\n\nYoroTrooper subtly alters its actions to blur its origin, using various tactics to point to Azerbaijan. In addition to routinely rerouting its operations via Azerbaijan, the threat actors frequently translate Azerbaijani to Russian and draft lures in Russian before converting them to Azerbaijani for their phishing attacks. The addition of Uzbek language in their payloads since June 2023 poses another layer of obfuscation, but is likely a demonstration of the actors' multilingual abilities rather than an attempt to mask as an Uzbek adversary.\n\nIn terms of malware use, YoroTrooper has evolved from relying heavily on commodity malware to also using custom-built malware across platforms such as Python, PowerShell, GoLang, and Rust. There is evidence that this threat actor continues to learn and adapt. There has been successful intrusion into several CIS government entities, indicating possible state-backing or state interests serving as motivation.\n\nInvestigations into YoroTrooper are ongoing to determine the extent of potential state sponsorship and additionally whether there is another motivator or objective, such as financial gain through the sale of state-held information. Protective countermeasures have been highlighted. Various IOCs are listed on GitHub for public access."
    )
    # Define the ASSISTANT prompt
    assistant_prompt = (
        "mindmap\nroot(YoroTrooper Threat Analysis)\n    (Origin and Target)\n      ::icon(fa fa-crosshairs)\n      (Likely originates from Kazakhstan)\n      (Mainly targets CIS countries)\n      (Attempts to make attacks appear from Azerbaijan)\n    (TTPs)\n      ::icon(fa fa-tactics)\n      (Uses VPN exit points in Azerbaijan)\n      (Spear phishing via credential-harvesting sites)\n      (Infiltrates websites and accounts of government officials)\n      (Subtly alters actions to blur origin)\n    (Language Proficiency)\n      ::icon(fa fa-language)\n      (Fluency in Kazakh and Russian)\n      (Translates Azerbaijani to Russian for phishing attacks)\n      (Uses Uzbek language in payloads)\n    (Malware Use)\n      ::icon(fa fa-bug)\n      (Evolved from commodity malware to custom-built malware)\n      (Uses Python, PowerShell, GoLang, and Rust platforms)\n    (Investigations and Countermeasures)\n      ::icon(fa fa-search)\n      (Ongoing investigations into potential state sponsorship)\n      (Protective countermeasures highlighted)\n      (IOCs listed on GitHub for public access)"
    )
    if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_prompt},
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_prompt},
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content

# Function to generate a mindmap
def run_models_tweet(input_text, client, selected_language):
    # Combine the selected languages into a string, or default to "English" if none selected
    language = ", ".join(selected_language) if selected_language else "English"
    if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"You are tasked with creating an mindmap in {language} language designed specifically for a threat analyst. This mindmap aims to visually organize 3 or 4 brances or key findings and crucial highlights from the text, considering each branch cannot have more than 2 subbranches. Please adhere to the following guidelines in english but apply approach to {language}: \n1. Avoid using hyphens in the text, as they cause errors in the Mermaid.js code 2. Limit the number of primary nodes branching from the main node to four. These primary nodes should encapsulate the top four main themes. Add detailed sub-nodes to elaborate on these themes \n3. Incorporate icons where suitable to enhance readability and comprehension\n4. Use single parentheses around each node to give them a rounded shape.\n5. avoid using icons and emoji\n6. Do not insert spaces after the text of each line and do not use parentheses or special characters for the names of the chart fields.\n7 Start mermaid code with 'mindmap', not use as first line \n8 Don't write ``` as last line. \n9 Avoid use line with style root. \n10 Avoid close with any comment starting with # . \n11 not use theme as second line, second line must start with root syntax. \n12 special characters need to be escaped or avoided, like brackets in domain. Example: not use mail[.]kz but use mail.kz \n13 When encapsulating text within a line, avoid using additional parentheses as they can introduce ambiguity in Mermaid syntax. Instead, use dashes to enclose your text \n14 Instead of using following approach (Indicators of compromise (IOC) provided) use this: (Indicators of compromise - IOC - provided)."
                },
                {
                    "role":"user",
                    "content":"Title:  Threat Report Summary: Kazakhstan-associated YoroTrooper disguises origin of attacks as Azerbaijan\n\nThreat actors known as YoroTrooper, presumably originating from Kazakhstan, have been conducting cyber espionage activities, largely focusing on Commonwealth of Independent States (CIS) countries. These actors mask their origins, making their attacks appear to come from Azerbaijan. Several tactics, techniques, and procedures (TTPs) were used, including using VPN exit points in Azerbaijan and spear phishing via credential-harvesting sites. They have infiltrated websites and accounts of several government officials between May and August 2023.\n\nThe information supporting that YoroTrooper is likely based in Kazakhstan includes the use of Kazakh currency, fluency in Kazakh and Russian, and the limited targeting of Kazakh entities. Interestingly, YoroTrooper has shown a defensive interest in the website of the Kazakhstani state-owned email service (mail[.]kz), taking precautions to ensure it is not exposed to potential security vulnerabilities. The only Kazakh institution targeted was the government’s Anti-Corruption Agency.\n\nYoroTrooper subtly alters its actions to blur its origin, using various tactics to point to Azerbaijan. In addition to routinely rerouting its operations via Azerbaijan, the threat actors frequently translate Azerbaijani to Russian and draft lures in Russian before converting them to Azerbaijani for their phishing attacks. The addition of Uzbek language in their payloads since June 2023 poses another layer of obfuscation, but is likely a demonstration of the actors' multilingual abilities rather than an attempt to mask as an Uzbek adversary.\n\nIn terms of malware use, YoroTrooper has evolved from relying heavily on commodity malware to also using custom-built malware across platforms such as Python, PowerShell, GoLang, and Rust. There is evidence that this threat actor continues to learn and adapt. There has been successful intrusion into several CIS government entities, indicating possible state-backing or state interests serving as motivation.\n\nInvestigations into YoroTrooper are ongoing to determine the extent of potential state sponsorship and additionally whether there is another motivator or objective, such as financial gain through the sale of state-held information. Protective countermeasures have been highlighted. Various IOCs are listed on GitHub for public access."
                },
                {
                    "role":"assistant",
                    "content":"mindmap\nroot(YoroTrooper Threat Analysis)\n    (Origin and Disguise)\n       ::icon(fa fa-crosshairs)\n      (Presumed origin: Kazakhstan)\n      (Disguises attacks as from Azerbaijan)\n    (TTPs and Language Use)\n      ::icon(fa fa-tactics)\n      (Uses VPNs and spear phishing)\n      (Languages: Kazakh, Russian, Azerbaijani, Uzbek)\n    (Malware Evolution)\n      ::icon(fa fa-bug)\n      (From commodity to custom malware)\n      (Platforms: Python, PowerShell, GoLang, Rust)\n"
                },
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"You are tasked with creating an in-depth mindmap {language} language designed specifically for a threat analyst. This mindmap aims to visually organize 3 or 4 brances or key findings and crucial highlights from the text, considering each branch cannot have more than 2 subbranches. Please adhere to the following guidelines in english but apply approach to {language}: \n1. Avoid using hyphens in the text, as they cause errors in the Mermaid.js code 2. Limit the number of primary nodes branching from the main node to four. These primary nodes should encapsulate the top four main themes. Add detailed sub-nodes to elaborate on these themes \n3. Incorporate icons where suitable to enhance readability and comprehension\n4. Use single parentheses around each node to give them a rounded shape.\n5. avoid using icons and emoji\n6. Do not insert spaces after the text of each line and do not use parentheses or special characters for the names of the chart fields.\n7 Start mermaid code with 'mindmap', not use as first line \n8 Don't write ``` as last line. \n9 Avoid use line with style root. \n10 Avoid close with any comment starting with # . \n11 not use theme as second line, second line must start with root syntax. \n12 special characters need to be escaped or avoided, like brackets in domain. Example: not use mail[.]kz but use mail.kz \n13 When encapsulating text within a line, avoid using additional parentheses as they can introduce ambiguity in Mermaid syntax. Instead, use dashes to enclose your text \n14 Instead of using following approach (Indicators of compromise (IOC) provided) use this: (Indicators of compromise - IOC - provided)."
                },
                {
                    "role":"user",
                    "content":"Title:  Threat Report Summary: Kazakhstan-associated YoroTrooper disguises origin of attacks as Azerbaijan\n\nThreat actors known as YoroTrooper, presumably originating from Kazakhstan, have been conducting cyber espionage activities, largely focusing on Commonwealth of Independent States (CIS) countries. These actors mask their origins, making their attacks appear to come from Azerbaijan. Several tactics, techniques, and procedures (TTPs) were used, including using VPN exit points in Azerbaijan and spear phishing via credential-harvesting sites. They have infiltrated websites and accounts of several government officials between May and August 2023.\n\nThe information supporting that YoroTrooper is likely based in Kazakhstan includes the use of Kazakh currency, fluency in Kazakh and Russian, and the limited targeting of Kazakh entities. Interestingly, YoroTrooper has shown a defensive interest in the website of the Kazakhstani state-owned email service (mail[.]kz), taking precautions to ensure it is not exposed to potential security vulnerabilities. The only Kazakh institution targeted was the government’s Anti-Corruption Agency.\n\nYoroTrooper subtly alters its actions to blur its origin, using various tactics to point to Azerbaijan. In addition to routinely rerouting its operations via Azerbaijan, the threat actors frequently translate Azerbaijani to Russian and draft lures in Russian before converting them to Azerbaijani for their phishing attacks. The addition of Uzbek language in their payloads since June 2023 poses another layer of obfuscation, but is likely a demonstration of the actors' multilingual abilities rather than an attempt to mask as an Uzbek adversary.\n\nIn terms of malware use, YoroTrooper has evolved from relying heavily on commodity malware to also using custom-built malware across platforms such as Python, PowerShell, GoLang, and Rust. There is evidence that this threat actor continues to learn and adapt. There has been successful intrusion into several CIS government entities, indicating possible state-backing or state interests serving as motivation.\n\nInvestigations into YoroTrooper are ongoing to determine the extent of potential state sponsorship and additionally whether there is another motivator or objective, such as financial gain through the sale of state-held information. Protective countermeasures have been highlighted. Various IOCs are listed on GitHub for public access."
                },
                {
                    "role":"assistant",
                    "content":"mindmap\nroot(YoroTrooper Threat Analysis)\n    (Origin and Disguise)\n       ::icon(fa fa-crosshairs)\n      (Presumed origin: Kazakhstan)\n      (Disguises attacks as from Azerbaijan)\n    (TTPs and Language Use)\n      ::icon(fa fa-tactics)\n      (Uses VPNs and spear phishing)\n      (Languages: Kazakh, Russian, Azerbaijani, Uzbek)\n    (Malware Evolution)\n      ::icon(fa fa-bug)\n      (From commodity to custom malware)\n      (Platforms: Python, PowerShell, GoLang, Rust)\n"
                },
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content

# Function to extract IOCs   
def extract_iocs(input_text, client, service_selection):
    prompt = "You are tasked with extracting IOCs from the following blog post for a threat analyst. Provide a structured, table-like format, with rows separated by newlines and columns by commas with the following rows: Indicator, Type, Description. Extract indicators just if you are able to find them in the blog post provided. With reference to IP addresses, URLs, and domains, remove square brackets. Examples: tech[.]micrsofts[.]com will be tech.micrsofts.com and 27.102.113.93\n\n" + input_text
    if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": prompt}
            ],
        )
    elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": prompt}
            ],
        )
    else:
        return "Service selection is invalid."

    # Extract and return the response content
    try:
        response_content = response.choices[0].message.content
        # Parse the response content into a DataFrame
        data = [line.split(",") for line in response_content.strip().split("\n")]
        #df = pd.DataFrame(data[1:], columns=data[0])
        #return df
        max_columns = max(len(row) for row in data)
        standardized_data = [row + [''] * (max_columns - len(row)) for row in data]

        df = pd.DataFrame(standardized_data[1:], columns=standardized_data[0])
        return df
    except Exception as e:
        return f"Failed to extract and parse IOCs: {e}"


#Function to provide TTPs (tactics and techniques) table from the scraped text
def ttp(text, client):
  # Define the SYSTEM prompt with guidelines for creating the mindmap
  system_prompt_ttp = (
        "You are an AI assistant expert in cybersecurity, threat intelligence, and Mitre attack, assisting Infosec professionals in understanding cyber attacks."
  )
    # Define the USER prompt
  user_prompt_ttp = (
        f"With reference to ATT&CK Matrix for Enterprise extract TTPs (tactics and techniques) from text at the end of following prompt. \n" 
        "For each techniques try to provide techniqueID, tactic, comment if you can get relevant content from text, producing a table with following columns: technique, technique ID, tactic, comment. \n" 
        "Text to work with: {text}"
    )
  if service_selection == "OpenAI":
      # OpenAI API call
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": system_prompt_ttp},
            {"role": "user", "content": user_prompt_ttp},
            {"role": "user", "content": input_text},
            ],
        )
    return response.choices[0].message.content
  elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {"role": "system", "content": system_prompt_ttp},
                {"role": "user", "content": user_prompt_ttp},
                {"role": "user", "content": input_text},
                ],
            )   
        return response.choices[0].message.content

# ------------------ prompt variables ----------------------------#
prompt_table = """
| Technique                                | Technique ID | Tactic           | Comment                                                                                                      |
|------------------------------------------|--------------|------------------|--------------------------------------------------------------------------------------------------------------|
| Used CVE-2021-44228 for initial access.   | T1190        | Initial Access   | Used CVE-2021-44228 to exploit publicly exposed servers for initial access.                                  |
| Used commands and scripts for execution.  | T1059        | Execution        | Used commands and scripts (like PowerShell and BAT) to execute different operations.                         |
| Used NineRAT for persistence.             | T1543        | Persistence      | Used NineRAT to set up persistence by creating services using BAT scripts.                                     |
| NineRAT dropper deletes itself for defense evasion. | T1140 | Defense Evasion  | NineRAT has a dropper binary containing two other components, written to disk, and the dropper deletes itself to avoid detection. |
| Used Telegram for command and control.   | T1102        | Command and Control | Used Telegram bots and channels for C2 communications.                                                       |
| Used commands for system information discovery. | T1082 | Discovery        | Used commands like "whoami," "ver," "getmac" for system information discovery.                                |
| Used NineRAT for data collection.         | T1005        | Collection       | NineRAT is used to collect data from the local system.                                                        |
"""

prompt_response = """
{
  "name": "Lazarus Group TTPs",
  "versions": {
    "attack": "14",
    "navigator": "4.9.1",
    "layer": "4.5"
  },
  "domain": "enterprise-attack",
  "description": "TTPs identified in Lazarus Group's Operation Blacksmith",
  "filters": {
    "platforms": ["windows"]
  },
  "sorting": 0,
  "layout": {
    "layout": "side",
    "aggregateFunction": "average",
    "showID": false,
    "showName": true,
    "showAggregateScores": false,
    "countUnscored": false,
    "expandedSubtechniques": "none"
  },
  "hideDisabled": false,
  "techniques": [
    {
      "techniqueID": "T1190",
      "tactic": "initial-access",
      "color": "",
      "comment": "Used CVE-2021-44228 to exploit publicly exposed servers for initial access.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1059",
      "tactic": "execution",
      "color": "",
      "comment": "Used commands and scripts (like PowerShell and BAT) to execute different operations",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1543",
      "tactic": "persistence",
      "color": "",
      "comment": "Used NineRAT to set up persistence by creating services using BAT scripts.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1140",
      "tactic": "defense-evasion",
      "color": "",
      "comment": "NineRAT has a dropper binary containing two other components, which are written to disk and the dropper deletes itself to avoid detection.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1102",
      "tactic": "command-and-control",
      "color": "",
      "comment": "Used Telegram bots and channels for C2 communications.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1082",
      "tactic": "discovery",
      "color": "",
      "comment": "Used commands like \"whoami\", \"ver\", \"getmac\" for system information discovery.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    },
    {
      "techniqueID": "T1005",
      "tactic": "collection",
      "color": "",
      "comment": "NineRAT is used to collect data from the local system.",
      "enabled": true,
      "metadata": [],
      "links": [],
      "showSubtechniques": false
    }
  ],
  "gradient": {
    "colors": ["#ff6666", "#ffe766", "#8ec843"],
    "minValue": 0,
    "maxValue": 100
  },
  "legendItems": [],
  "metadata": [],
  "links": [],
  "showTacticRowBackground": false,
  "tacticRowBackground": "#dddddd"
}
"""

ttps_timeline = """
1. Initial Access: Exploitation of Remote Services [T1210]
2. Execution: Command and Scripting Interpreter: PowerShell [T1059.001]  
3. Persistence: External Remote Services [T1133]
4. Persistence: Server Software Component: Web Shell [T1505.003]
5. Persistence: Account Creation [T1136]
6. Defense Evasion: Use Alternate Authentication Material [T1550]
7. Defense Evasion: Modify Registry [T1112]
8. Defense Evasion: Indicator Removal on Host: File Deletion [T1070.004]
9. Credential Access: OS Credential Dumping [T1003]
10. Discovery: System Information Discovery [T1082]
11. Collection: Data Staged: Local Data Staging [T1074.001]
12. Command and Control: Remote Access Tools [-]
13. Command and Control: Proxy: Multi-hop Proxy [T1090.003]
14. Command and Control: Application Layer Protocol: Web Protocols [T1071.001]
15. Command and Control: Ingress Tool Transfer [T1105]
16. Impact: Data Encrypted for Impact [T1486]
"""

mermaid_timeline = """
timeline
title Lazarus Group Operation Blacksmith
    Initial Access
    : Exploitation of Remote Services - [T1210]
	Execution
    : Command and Scripting Interpreter - PowerShell - [T1059.001]  
    Persistence
    : External Remote Services - [T1133]
	: Server Software Component - Web Shell - [T1505.003]
	: Account Creation - [T1136]
	Defense Evasion
	: Use Alternate Authentication Material - [T1550]
	: Modify Registry - [T1112]
	: Indicator Removal on Host - File Deletion - [T1070.004]
	Credential Access
    : OS Credential Dumping - [T1003]
    Discovery
    : System Information Discovery - [T1082]
    Collection: Data Staged - Local Data Staging - [T1074.001]
	Command and Control
    : Remote Access Tools - [-]
    : Proxy Multi-hop Proxy - [T1090.003]
    : Application Layer Protocol Web Protocols - [T1071.001]
	: Ingress Tool Transfer - [T1105]
    Impact: Data Encrypted for Impact - [T1486]
"""

#Function to provide ATT&CK Matrix for Enterprise layer json file
def attack_layer(text, client):
  # Define the SYSTEM prompt
  system_prompt_attack_layer = (
      f"You are tasked with creating an ATT&CK Matrix for Enterprise layer json file with attack version 14, navigator 4.9.1, layer version 4.5 to load a layer in MITRE ATT&CK Navigator. \n" 
      "Use {ttptable} as input. Print just json content, avoiding including any additional text in the response. In domain field use enterprise-attack."
  )
  # Define the USER prompt
  user_prompt_attack_layer = (
      f"Title:  Enterprise techniques used by 2015 Ukraine Electric Power Attack, ATT&CK campaign C0028 (v1.0): Table: {prompt_table}"   
  )
  # Define the ASSISTANT prompt
  assistant_prompt_attack_layer = (
      f"{prompt_response}"   
  )
  if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt_attack_layer},
                {"role": "user", "content": user_prompt_attack_layer},
                {"role": "assistant", "content": assistant_prompt_attack_layer},
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
  elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {"role": "system", "content": system_prompt_attack_layer},
                {"role": "user", "content": user_prompt_attack_layer},
                {"role": "assistant", "content": assistant_prompt_attack_layer},
		        {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content

#Function to provide a list of TTPs order by execution time
def ttp_list(text, ttptable, client):
  # Define the SYSTEM prompt
  system_prompt_ttp_list = (
      "You are an AI assistant expert in cybersecurity, threat intelligence, and Mitre attack, assisting Infosec professionals in understanding cyber attacks."
  )
  # Define the USER prompt
  user_prompt_ttp_list = (
      f"Based on {text} and {ttptable} provide a list of TTPs order by execution time, Each line must include only Tactic and Subtactic, IDs between brackets after subtactic. \n" 
      "The Enterprise tactics names as defined by the MITRE ATT&CK framework are: Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, Impact" 
  )
  if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt_ttp_list},
                {"role": "user", "content": user_prompt_ttp_list},
            ],
        )
        return response.choices[0].message.content
  elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {"role": "system", "content": system_prompt_ttp_list},
                {"role": "user", "content": user_prompt_ttp_list},
            ],
        )
        return response.choices[0].message.content

#Function to generate attack timeline Mermaid.js code 
def ttp_graph_timeline(text, client):
  # Define the USER prompt
  user_prompt_ttp_graph_timeline = (
          f"Write a Mermaid.js timeline graph that illustrates the stages of a cyber attack whose TTPs timeline is as follows: {text} .\n" 
          "As an example condider the Lazarus Group's operation named Operation Blacksmith, whose Tactics, Techniques, and Procedures (TTPs) timeline is as follows: {ttps_timeline}, and related meirmad.js code is: {mermaid_timeline}. \n"
          "Use the Enterprise tactics names as defined by the MITRE ATT&CK framework are: Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, Impact"
          "Use the following guidalines to generate code: \n"
          "1. Use keyword timeline to start the graph definition, timeline must be first word in the output, don't use anything else. \n"
          "2. title: This keyword is followed by the title of the timeline graph \n" 
          "3. Each timeline step is defined on a separate line and starts with a description of the step. The description should be concise and informative, summarizing the key actions or events of the step. \n"
          "4 The description is followed by a colon (:) and then the step details \n"
          "5. The step details can include any additional information about the step, such as the specific tools or techniques used. \n"
          "6. Optionally, the step details can include a reference to a malleable threat technique ID using square brackets. \n"
          "7. Avoid provide days after TTP ID. \n"
          "8. Provide just mermaid.js code without any other text. \n"
          "9. Start code with timeline- \n"
          "10. Don't use any bracket at the benning and the end of your output. \n"  
          "11. When encapsulating text within a line, avoid using additional parentheses as they can introduce ambiguity in Mermaid syntax. Instead, use dashes to enclose your text. \n"
          "12. Don't write ``` as the first and last line." 
    )
  if service_selection == "OpenAI":
        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "user", "content": user_prompt_ttp_graph_timeline},
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content
  elif service_selection == "Azure OpenAI":
        # Azure OpenAI API call
        response = client.chat.completions.create(
            model = deployment_name,
            messages=[
                {"role": "user", "content": user_prompt_ttp_graph_timeline},
                {"role": "user", "content": input_text},
            ],
        )
        return response.choices[0].message.content

#Mermaid Timeline
def mermaid_timeline_graph(mindmap_code_timeline):
    html_code = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div class="mermaid">{mindmap_code_timeline}</div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    return html_code

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
        "Welcome to TI MINDMAP, an AI-powered tool designed to help producing Threat Intelligence summaries, Mindmap and IOCs extraction and more."
    )
    st.markdown("Created by [Antonio Formato](https://www.linkedin.com/in/antonioformato/).")
    st.markdown("Contributor [Oleksiy Meletskiy](https://www.linkedin.com/in/alecm/).")
    # Add "Star on GitHub"
    st.sidebar.markdown(
        "⭐ Star on GitHub: [![Star on GitHub](https://img.shields.io/github/stars/format81/TI-Mindmap-GPT?style=social)](https://github.com/format81/TI-Mindmap-GPT)"
    )
    st.markdown("""---""")
st.sidebar.header("Setup")
with st.sidebar: 
    # List of options for the language dropdown menu
    options = ["English", "Italian", "Spanish", "French", "Arabic"]
    # Create a multi-select dropdown menu
    selected_language = st.multiselect("Select the language into which you want to translate the recap and mindmap of your input:", options, default=["English"])

    service_selection = st.sidebar.radio(
        "Select AI Service",
        ("OpenAI", "Azure OpenAI")
    )
    if service_selection == "Azure OpenAI":
        azure_api_key = st.sidebar.text_input(
            "Enter your Azure OpenAI API key:", 
            type="password",
            help="You can find your Azure OpenAI API key on the [Azure portal](https://portal.azure.com/).",
            )
        azure_endpoint = st.sidebar.text_input(
            "Enter your Azure OpenAI endpoint:",
            help="Example: https://YOUR_RESOURCE_NAME.openai.azure.com/",
            )
        deployment_name = st.sidebar.text_input(
            "Enter your Azure OpenAI deployment name:",
            help="The deployment name you chose when you deployed the model.",
            )
        st.markdown(
            "Data stays active solely for the duration of the user's session and is erased when the page is refreshed."
        )
        st.markdown(
            "Tested with Azure OpenAI model: gpt-4-32k, but it should work also with gpt-35-turbo"
        )

    if service_selection == "OpenAI":
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

# "About" section to the sidebar
st.sidebar.header("About")
with st.sidebar:
    st.markdown(
        "This project should be considered a proof of concept. You are welcome to contribute or give me feedback. Always keep in mind that AI-generated content may be incorrect."
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
        "7) [Splunk Securiy Blog](https://www.splunk.com/en_us/blog/security.html)"
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

# Main UI
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.title("TI MINDMAP")
with col2:
    st.image("logoTIMINDMAPGPT.png", width=150)

#Insert containers separated into tabs.
tab1, tab2, tab3, tab4 = st.tabs(["🗃 Main", "💾 AI Chat with your data (future release🚧)", "🗃️ Conf file (future release🚧)", "📈 Pdf Report (future release🚧)"])

# Form for URL input
with tab1:
    form = st.form("Form to run", clear_on_submit=True)
    default_url = ""
    url = form.text_input("Enter your URL below:", default_url, placeholder="Paste any URL of your choice")

# Create columns for buttons and checkboxes
cols = form.columns(2)

with cols[0]:
    submit_button = form.form_submit_button("Generate")
    
with cols[1]:
    submit_cb_summary = form.checkbox("🗺️Summary and MindMap",value=True)
    submit_cb_tweet = form.checkbox("📺I want to tweet MindMap",value=True)
    submit_cb_ioc = form.checkbox("🧐I want to extract IOCs (if present)",value=True)
    submit_cb_ttps = form.checkbox("📊Extract adversary tactics, techniques, and procedures (TTPs)",value=True)
    submit_cb_ttps_by_time = form.checkbox("🕰️TTPs ordered by execution time",value=True)
    submit_cb_ttps_timeline = form.checkbox("📈TTPs (Tactics, Techniques, and Procedures) graphic timeline",value=True)

user_input=""

if submit_button and client:
    text = scrape_text(url)
    # Check if the content is related to cybersecurity
    relevance_check = check_content_relevance(text, client, service_selection)
    if "not related to cybersecurity" in relevance_check:
        st.write(f"**Content not related to cybersecurity**, It's about {relevance_check}")
    else:
        # If related, proceed with summary and mindmap generation
        input_text = "Generate a Mermaid.js MindMap only using the text below:\n" + text
        with st.expander("See full article"):
            st.write(text)

        # Generate Summary and Mindmap
        if submit_cb_summary:
            with st.spinner("Generating Summary "):
                summary = summarise(text, client, service_selection, selected_language)
                st.write("### OpenAI Generated Summary")
                st.write(summary) 

                with st.spinner("Generating Mermaid Code"):
                    mindmap_code = run_models(input_text, client, selected_language)
                    html(mermaid_chart_png(mindmap_code), width=1500, height=1500)
                with st.expander("See OpenAI Generated Mermaid Code"):
                    st.code(mindmap_code)

        #Generate tweet
        if submit_cb_tweet:
            with st.spinner("Generating Tweet"):    
                summary_tweet = summarise_tweet(text, client, service_selection, selected_language)
                st.write("### OpenAI Generated Tweet")
                user_input = st.text_area("Edit your tweet:", summary_tweet, height=100)
                #num_symbols = len(user_input)
                #st.write(summary_tweet)  

                if submit_cb_summary == False:
                    with st.spinner("Generating Mermaid Tweet Code"):
                        mindmap_code = run_models_tweet(input_text, client, selected_language)
                        html(mermaid_chart_png(mindmap_code), width=600, height=600)
                    with st.expander("See OpenAI Generated Mermaid Code - sorter version"):
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
        
        # Extracting IOCs and displaying them as a table
        if submit_cb_ioc:
            with st.spinner("Extracting IOCs"):
                iocs_df = extract_iocs(text, client, service_selection)
                if isinstance(iocs_df, pd.DataFrame):
                    st.write("### Extracted IOCs")
                    st.dataframe(iocs_df)
                else:
                    st.error(iocs_df)

        # Extracting IOCs and displaying them as a table
        if submit_cb_ttps:
           with st.spinner("Extracting TTPs (tactics, techniques, and procedures) table from the scraped text."):
               ttptable = ttp(text, client)  # Assign the output of ttp to ttptable
               st.write("### TTPs table")
               st.write(ttptable)
        
        # Extracting IOCs and displaying them as a table
        if submit_cb_ttps_by_time:
            with st.spinner("TTPs ordered by execution time"):
                attackpath = ttp_list(text, ttptable, client)
                st.write("### TTPs ordered by execution time")
                st.write(attackpath)

        # Mermaid TTPs timeline
        if submit_cb_ttps_timeline:
            #with st.spinner("Mermaid TTPs Timeline"):
            mermaid_timeline = ttp_graph_timeline(text, client)
            with st.expander("See OpenAI Generated Mermaid TTPs Timeline"):
                st.code(mermaid_timeline)
            html(mermaid_timeline_graph(mermaid_timeline), width=1500, height=1500)

elif submit_button and not client:
    st.error("Please enter a valid OpenAI API key to generate the mindmap.")

#TAB2
with tab2:
    st.write("💾 AI Chat with your data - future release🚧")
    st.write("Work in progress")

#TAB3
with tab3:
    st.write("🗃️ Conf file - future release🚧")
    st.write("Work in progress")

#TAB3
with tab4:
    st.write("📈 Pdf Report - future release🚧")
    st.write("Work in progress")