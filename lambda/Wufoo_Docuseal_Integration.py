import os, requests, sys, json, shutil
from subprocess import PIPE, run
from urllib.parse import parse_qs
from dotenv import load_dotenv

load_dotenv()

def get_wufoo_json(entry_id):
    subdomain = os.environ.get('WUFOO_SUBDOMAIN') 
    api_key = os.environ['WUFOO_API_KEY']
    form_id = os.environ.get('WUFOO_FORM_ID')  
    url = f"https://{subdomain}.wufoo.com/api/v3/forms/{form_id}/entries.json"
    params = {'Filter1': f'EntryId Is_equal_to {entry_id}'}
    response = requests.get(url, params=params, auth=(api_key, 'footastic'))
    response.raise_for_status()
    data = response.json()
    entries = data.get('Entries', [])
    if not entries:
        raise ValueError(f"No entry found for EntryId: {entry_id}")
    return entries[0]

def prepare_docuseal_data(wufoo_json):
    try:
        template_id = os.environ.get['DOCUSEAL_TEMPLATE_ID']
        
        field_mappings = {
            'Field6': 'First Name', 
            'Field7': 'Last Name', 
            'Field9': 'Email',  
        }
        
        f_name = wufoo_json.get('Field6', '') 
        l_name = wufoo_json.get('Field7', '') 
        email = wufoo_json.get('Field9', '') 
        
        if not email:
            raise ValueError("Missing required email from Wufoo data")
        
        values = {}
        for wufoo_id, docuseal_name in field_mappings.items():
            if wufoo_id in wufoo_json:
                values[docuseal_name] = wufoo_json[wufoo_id]
        
        data = {
            "template_id": int(template_id),
            "send_email": True,
            "submitters": [
                {
                    "first_name": f_name,
                    "last_name": l_name,
                    "email": email,
                    "role": "First Party",  
                    "values": values  
                }
            ]
        }
        return data
    except ValueError as ve:
        print(f"Validation Error: {str(ve)}")
        raise 
    except KeyError as ke:
        print(f"Missing key in wufoo_json: {str(ke)}")
        raise
    except Exception as e:
        print(f"Unexpected error in prepare_docuseal_data: {str(e)}")
        raise


def send_to_docuseal(docuseal_data):
    url = "https://api.docuseal.com/submissions"
    api_key = os.environ.get('')
    headers = {
        "X-Auth-Token": api_key,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=docuseal_data, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_submission_link(response):
    try:
        print("Response received in extract_submission_link:", json.dumps(response, indent=2)) 

        first_entry = response[0]  
        
        embed_src = first_entry['embed_src'] 
        
        return embed_src
        
    except IndexError:
        raise ValueError("Expected response to be a non-empty list")

    except KeyError:
        raise ValueError("No 'embed_src' in the first entry")
        
    except Exception as e:
        print(f"Unexpected error in extract_submission_link: {str(e)}")
        raise

 