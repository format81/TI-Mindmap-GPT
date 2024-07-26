import os
import json
from uuid import uuid4
from mistralai.models.chat_completion import ChatMessage
from langsmith import traceable

OPENAI_MODEL = "gpt-4-1106-preview"

prompt_table = """
| Question    | Description
--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
|What?	      | Google has assigned a new CVE ID (CVE-2023-5129) to a libwebp security vulnerability exploited as a zero-day.
|When?	      | 2023-09-25 (2023-09-15)
|Where?	      | An official security announcement by google have been published
|Who?	        | Google, Apple, Chromium, Several Open Source Projects
|How?	        | A heap-based overflow issue has been identified in the WebP image encoding library.
|Why?	        | A few weeks ago Apple reported an vulnerability to google in one of it’s open-source libraries. Possibly after their investigation of the BLASTPASS exploit chain used to compromise iPhones previously.
|So what?	    | The WebP image encoding library is used by a lot of both open and closed applications for image processing. It’s particular common in web-browser, these mainstream browsers have been updated during the last weeks but modern applications like Teams, Slack and other Electron applications bundle vulnerable versions.
|What is next?|	1.	We need to review our asset library for vulnerable web-browsers and make sure that devices are updated accordingly. 2. Both sanctioned and unsanctioned electron application need to be tracked down and either be updated or removed. 3. A Threat Hunting package should be drafted to give direction for our cyber security partner for tracking down abnormal activities related to electron applications if possible.
|References	  | •	https://thehackernews.com/2023/09/new-libwebp-vulnerability-under-active.html •	https://blog.isosceles.com/the-webp-0day/   •	https://www.bleepingcomputer.com/news/security/google-assigns-new-maximum-rated-cve-to-libwebp-bug-exploited-in-attacks/
"""


#Function to provide ATT&CK Matrix for Enterprise layer json file
@traceable
def ai_fivewhats(input_text, client, service_selection, deployment_name=None):

    # Define the SYSTEM prompt
    system_prompt_5whats = ("You are an expert in Cyber threat analisys, common structured analisys and threat intelligence. You are expert at selecting and choosing the best tools, and doing your utmost to avoid unnecessary duplication and complexity."
                            "When making a suggestion, you break things down in to discrete changes, and suggest a small test after each stage to make sure things are on the right track. You are tasked with creating an a table with main summaries of the article with the answers on the following questions where it applicable to have an answer regarding text in article : What? (what happened), When? (when it happened), Where? (where it happened).")
    # Define the USER prompt
    system_prompt_5whats2 = f"Use {prompt_table} as an example of possible result. Print formatted table with 2 columnes Questions and Summaries. Where you can't answer for the question or you are lack of information just fill NON APPLICABLE for appropriate question "
    
    user_prompt_5whats = (
        f"Title:  Critical flaw in image library exploited in the wild (CVE-2023-4863) Table: {prompt_table}"   
    )
    # Define the ASSISTANT prompt
    assistant_prompt_5whats = (
        f"{prompt_table}"   
    )

  # Combine the selected languages into a string, or default to "English" if none selected
    if not input_text or not client or not service_selection:
        return "Invalid input parameters."
    
    try:
        if service_selection == "OpenAI" or service_selection == "Azure OpenAI":
            # Determine the model based on the service provider
            model = OPENAI_MODEL if service_selection == "OpenAI" else deployment_name
        
            # Make the API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt_5whats},
                    {"role": "user", "content": input_text},
                    {"role": "assistant", "content": system_prompt_5whats2},
                ],
            )
        
            return response.choices[0].message.content
            
        elif service_selection == "MistralAI":
            chat_response = client.chat(
            model = "mistral-large-latest",
            messages=[
                ChatMessage(role="system", content=system_prompt_5whats),
                ChatMessage(role="user", content=input_text),
                ],
            )
            return chat_response.choices[0].message.content  

    except Exception as e:
        # Return a more informative error message
        return f"An error occurred while generating the table summary: {e}"

  