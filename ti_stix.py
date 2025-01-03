import uuid
import json
from stix2 import parse, exceptions, Bundle
from langsmith import traceable
from datetime import datetime
from github import Github
import streamlit as st
from uuid import uuid4

# Model configuration
OPENAI_MODEL = "gpt-4o-2024-08-06"
# GitHub credentials
GITHUB_TOKEN = st.secrets["api_keys"]["github_accesstoken"]
REPO_NAME = "format81/ti-mindmap-storage"

# Add UUIDs to 'id' fields in STIX objects, ensuring each object has a unique identifier.
def add_uuid_to_ids(stix_data):
    """
    Add UUIDs to 'id' fields in STIX objects.
    """
    for item in stix_data:
        if 'id' in item:
            object_type = item['type']
            item['id'] = f"{object_type}--{uuid.uuid4()}"
    return stix_data

#Validate a list of STIX objects against the STIX 2.1 standard, identifying any invalid objects.
def validate_stix_objects(stix_objects):
    """
    Validate STIX objects against the STIX 2.1 standard.
    """
    all_valid = True
    invalid_objects = []
    for obj in stix_objects:
        try:
            # Parse the object to validate against the STIX 2.1 standard
            stix_obj = parse(json.dumps(obj), allow_custom=True)
            print(f"Validation passed for object ID: {obj.get('id')}")
        except exceptions.STIXError as se:
            print(f"STIX parsing error for object ID {obj.get('id')}: {se}")
            invalid_objects.append(obj)
            all_valid = False
        except json.JSONDecodeError as je:
            print(f"JSON parsing error: {je}")
            invalid_objects.append(obj)
            all_valid = False
    return all_valid, invalid_objects

#STIX Domain Objects prompt
system_prompt_sdo = (
    "You are tasked with creating STIX 2.1 Domain Objects (SDOs) from the provided threat intelligence text."
    "Possible SDOs include: Attack Pattern, Campaign, Course of Action, Identity, Indicator, Intrusion Set, Malware, Observed Data, Report, Threat Actor, Tool, Vulnerability, Infrastructure, Relationship, Sighting, Note, Opinion, Grouping, Incident, Location, Malware Analysis."
    "Create relevant SDOs in JSON format, strictly adhering to the STIX 2.1 specification."
    "Ensure the output is a valid JSON array ([...]) containing only SDOs identified with high confidence."
    "The is_family field indicates whether the malware is a family (if true) or an instance (if false). The values true or false are always enclosed in quotes."
    "For id property write just SDO_type-- following this example: \"id\": \"malware--\""
    "Timestamp must be in ISO 8601 format."
    "Don't use created_by_ref and source_ref"
    "The labels property in malware is used to categorize or tag the malware object with descriptive terms (e.g., \"trojan\", \"backdoor\", \"ransomware\"), Must contain at least one string."
    "threat-actor labels property should be an array of strings representing categories or descriptive terms for the threat actor."
    "Return only the JSON array, without any additional text, commentary, or code block delimiters (e.g., json)."
)


# Generate STIX SDOs
@traceable
def sdo_stix(input_text, client, ai_service_provider, deployment_name=None):
    """
    Generate STIX SDOs from input text using the AI model.
    """
    user_prompt_stix = f"Text: {input_text}"
    if not input_text or not client or not ai_service_provider:
        return "Invalid input parameters."
    
    try:
        if ai_service_provider == "OpenAI" or ai_service_provider == "Azure OpenAI":
            # Determine the model based on the service provider
            model = OPENAI_MODEL if ai_service_provider == "OpenAI" else deployment_name
        
            # Make the API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt_sdo},
                    {"role": "user", "content": user_prompt_stix}
                ],
            )
        
            return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"

@traceable
def correct_invalid_stix(input_text, invalid_objects, original_stix):
    """
    Ask the LLM to correct invalid STIX output based on the original text and invalid objects.
    """
    try:
        if ai_service_provider == "OpenAI" or ai_service_provider == "Azure OpenAI":
            # Determine the model based on the service provider
            model = OPENAI_MODEL if ai_service_provider == "OpenAI" else deployment_name
        
            # Make the API call
            invalid_output = json.dumps(invalid_objects, indent=4)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt_sdo},
                    {
                "role": "user",
                "content": f"""
Correct the following invalid STIX objects based on the original text and ensure consistency with the overall STIX data:

Input text:
{input_text}

Invalid STIX objects:
{invalid_output}

Existing valid STIX data:
{original_stix}
"""
            }
                ],
            )
        
            return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"

# Generate STIX data and ensure valid output
is_valid = False
stix_sdo = ""

#STIX Cyber-observable Object prompt
system_prompt_sco = (
    "You are tasked with creating STIX 2.1 Cyber-observable Objects (SCOs) based on the provided threat intelligence write-up."
    "SCOs include: Artifact, Autonomous System, Directory, Domain Name, Email Address, Email Message, File, IPv4 Address, IPv6 Address, MAC Address, Mutex, Network Traffic, Process, Software, URL, User Account, Windows Registry Key, X.509 Certificate, HTTP Request, ICMP, Socket Ext, TCP Ext, Archive Ext, Raster Image Ext, NTFS Ext, PDF Ext, UNIX Account Ext, Windows PE Binary Ext, Windows Process Ext, Windows Service Ext, Windows Registry Ext, JPEG File Ext, Email MIME Component, Email MIME Multipart Type, Email MIME Message Type, Email MIME Text Type."
    "Create relevant STIX 2.1 SCOs in JSON format based on the information provided in the text."
    "Strictly follow the STIX 2.1 specification, ensuring no properties are used that are not defined in the specification"
    "Ensure the JSON output is valid, starting with [ and closing with ]."
    "STIX SCO objects require at least type, id and value properties"
    "Only provide output if one or more SCOs can be identified with reasonable certainty from the text."
    "Ensure the structure and format are fully compliant with STIX 2.1."
    "id STIX identifier must match <object-type>--<UUID>"
    "Return only the JSON array, without any additional text, commentary, or code block delimiters (e.g., json)."
  )

@traceable
def sco_stix(input_text, client, ai_service_provider, deployment_name=None):
    """
    Generate STIX SCOs from input text using the AI model.
    """
    user_prompt_stix = f"Text: {input_text}"
    if not input_text or not client or not ai_service_provider:
        return "Invalid input parameters."
    
    try:
        if ai_service_provider == "OpenAI" or ai_service_provider == "Azure OpenAI":
            # Determine the model based on the service provider
            model = OPENAI_MODEL if ai_service_provider == "OpenAI" else deployment_name
        
            # Make the API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt_sco},
                    {"role": "user", "content": user_prompt_stix}
                ],
            )
        
            return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"
    
#STIX Relationship Object prompt
system_prompt_sro = (
    "You are tasked with creating a STIX 2.1 Relationship Object (SRO) based on the provided writeup about threat intelligence text SDOs and SCOs"
    "Remember a relationship is a link between STIX Domain Objects (SDOs), STIX Cyber-observable Objects (SCOs), or between an SDO and a SCO that describes the way in which the objects are related. Relationships can be represented using an external STIX Relationship Object (SRO) or, in some cases, through certain properties which store an identifier reference that comprises an embedded relationship, (for example the created_by_ref property)."
    "Create STIX Objects, in json format."
    "Identify Relationships: For each entity (like intrusion-set, malware, infrastructure, domain-name, file, directory), identify how they relate to each other. For example, malware might use infrastructure for command and control, or an intrusion set might leverage certain domains"
    "Use relationship Objects: Use relationship objects to connect entities. This object will specify the source and target entities and define the nature of the relationship (e.g., \"uses\", \"communicates with\")"
    "Ensure Consistent Referencing: Make sure that every object you want to relate is referenced correctly using their id in the relationship objects."
    "Pay attention to properties, don't use properties not defined in STIX 2.1 specification"
    "Start with [ and close with ] , no other content before [ and after ]"
    "If you cannot identify a specific SCO from the provided text, simply do not do anything."
    "Provide output only if you can identify one or more SCOs with reasonable certainty."
    "Pay attention to provide valid json."
    "Pay attention to provide valid STIX 2.1 structure."
    "Return only the JSON array, without any additional text, commentary, or code block delimiters (e.g., json)."
  )

@traceable
def sro_stix(input_text, stix_sdo, stix_sco,client, ai_service_provider, deployment_name=None):
    """
    """
    user_stix_sdo_sco_text = f"Text of writeup: {input_text},  {stix_sdo} , {stix_sco}"
    if not input_text or not client or not ai_service_provider:
        return "Invalid input parameters."
    
    try:
        if ai_service_provider == "OpenAI" or ai_service_provider == "Azure OpenAI":
            # Determine the model based on the service provider
            model = OPENAI_MODEL if ai_service_provider == "OpenAI" else deployment_name
        
            # Make the API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt_sro},
                    {"role": "user",
                "content": f"""
Generate STIX 2.1 relationship objects (SROs) based on the following:

Input text:
{input_text}

SDO:
{stix_sdo}

SCO:
{stix_sco}
"""
            }
        ],
    )
        
            return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"
    
def remove_brackets(text):
    """
    Remove leading '[' and trailing ']' and format inner objects into a valid JSON array.
    """
    if not text.startswith('[') or not text.endswith(']'):
        raise ValueError("Input text does not start with '[' or end with ']'")

    # Remove brackets and split into individual JSON objects
    objects_str = text[1:-1].strip()  # Remove brackets and leading/trailing whitespace
    objects_list = objects_str.split('}{')

    # Add back the missing curly braces and format into a valid JSON array
    formatted_objects = "[" + ", ".join(["{" + obj + "}" if not obj.startswith("{") and not obj.endswith("}") else obj for obj in objects_list]) + "]"

    return formatted_objects

def create_stix_bundle(sdo_data, sco_data, sro_data):
    """
    Create a STIX 2.1 bundle from input SDO, SCO, and SRO data.

    Args:
        sdo_data (list): List of valid SDO objects.
        sco_data (list): List of valid SCO objects.
        sro_data (list): List of valid SRO objects.

    Returns:
        str: A STIX 2.1 bundle in JSON format.
    """
    # Combine SDO, SCO, and SRO data
    all_objects = sdo_data + sco_data + sro_data
    #print("all_objects:", all_objects)

    bundle = {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "objects": all_objects
    }

    # Return the serialized bundle
    return json.dumps(bundle, indent=4)

def upload_to_github_stix(stix_bundle):
    """
    Uploads JSON content to a specified GitHub repository.

    Parameters:
    stix_bundle (dict): The JSON content to be uploaded to GitHub.

    Returns:
    str: The raw URL of the uploaded JSON file.
    """
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    commit_message = "Updated via Streamlit app"

    # Generate a unique file name with the current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    unique_id = str(uuid4())
    file_path_stix = f"stix2.1-bundles/{current_date}_{unique_id}.json"

    # Convert JSON to string
    json_str = json.dumps(stix_bundle, indent=4)

    try:
        # Get the file contents from GitHub
        contents = repo.get_contents(file_path_stix)
        sha = contents.sha
        # Update the file
        repo.update_file(contents.path, commit_message, json_str, sha)
        st.success("File updated successfully.")
    except:
        # If file does not exist, create it
        repo.create_file(file_path_stix, commit_message, json_str)
        st.success("File created successfully.")

    # Return the raw URL of the uploaded JSON file
    raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path_stix}"
    st.write("URL to STIX 2.1 bundle json file:")
    st.write(raw_url)
    return raw_url