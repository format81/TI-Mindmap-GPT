import os
import json
from uuid import uuid4
from mistralai.models.chat_completion import ChatMessage

OPENAI_MODEL = "gpt-4-1106-preview"

prompt_table2 = """
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

prompt_response2 = """
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

#Function to provide ATT&CK Matrix for Enterprise layer json file
def attack_layer(input_text, ttptable, client, service_selection, deployment_name=None):
  """
Creates an ATT&CK Matrix for Enterprise layer in JSON format based on the provided input text and TTP table.

Args:  
    input_text (str): The input text to be used for creating the ATT&CK Matrix.  
    ttptable (str): The TTP table that will be used as input for creating the ATT&CK Matrix.  
    client (object): An instance of the client to be used for making the API calls. Can be either an OpenAI client, Azure OpenAI client, or MistralAI client.  
    service_selection (str): The AI service to be used for processing the text. Can be either "OpenAI", "Azure OpenAI", or "MistralAI".  
    deployment_name (str, optional): The name of the Azure Machine Learning deployment that contains the text embedding model. Required if using "Azure OpenAI".  

Returns:  
    str: The JSON content of the ATT&CK Matrix for Enterprise layer. Returns an error message if the processing fails.  

Raises:  
    Exception: If there is an error in the API call or in the creation of the ATT&CK Matrix.
    """
  # Define the SYSTEM prompt
  system_prompt_attack_layer = (
      "You are tasked with creating an ATT&CK Matrix for Enterprise layer json file with attack version 14, navigator 4.9.1, layer version 4.5 to load a layer in MITRE ATT&CK Navigator. \n" 
      f"Use {ttptable} as input. Print just json content, avoiding including any additional text in the response. In domain field use enterprise-attack."
  )
  # Define the USER prompt
  user_prompt_attack_layer = (
      f"Title:  Enterprise techniques used by 2015 Ukraine Electric Power Attack, ATT&CK campaign C0028 (v1.0): Table: {prompt_table2}"   
  )
  # Define the ASSISTANT prompt
  assistant_prompt_attack_layer = (
      f"{prompt_response2}"   
  )
  try:
      if service_selection == "OpenAI" or service_selection == "Azure OpenAI":
          # Determine the model based on the service provider
          model = OPENAI_MODEL if service_selection == "OpenAI" else deployment_name

          # Prepare the messages for the API call
          messages=[
              {"role": "system", "content": system_prompt_attack_layer},
              {"role": "user", "content": user_prompt_attack_layer},
              {"role": "assistant", "content": assistant_prompt_attack_layer},
		          {"role": "user", "content": input_text},
              ]
          # Make the API call
          response = client.chat.completions.create(
              model=model,
              messages=messages,
              )

          # Return the response content
          return response.choices[0].message.content
      elif service_selection == "MistralAI":
            # Make the API call
            response = client.chat(
                model="mistral-large-latest",
                messages=[
                    ChatMessage(role="system", content=system_prompt_attack_layer),
                    ChatMessage(role="user", content=user_prompt_attack_layer),
                    ChatMessage(role="assistant", content=assistant_prompt_attack_layer),
                    ChatMessage(role="user", content=input_text),
                ],
            )
            # Return the response content
            return response.choices[0].message.content
  except Exception as e:
      return f"Failed to extract TTPs: {e}"