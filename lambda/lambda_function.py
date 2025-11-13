import json, requests, logging, os, sys
from urllib.parse import parse_qs

logger = logging.getLogger()
logger.setLevel(logging.INFO)

first_name_field = os.environ['FIRST_NAME_FIELD']
last_name_field = os.environ['LAST_NAME_FIELD']
email_field = os.environ['EMAIL_FIELD']
identification_type_field = os.environ['IDENTIFICATION_TYPE_FIELD']
identification_number_field = os.environ['IDENTIFICATION_NUMBER_FIELD']

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
        template_id = os.environ['DOCUSEAL_TEMPLATE_ID']
        field_mappings = {
            first_name_field: 'First Name', 
            last_name_field: 'Last Name', 
            email_field: 'Email', 
            identification_type_field: 'ID Type', 
            identification_number_field: 'ID Number', 
        }
        
        first_name = wufoo_json.get(first_name_field) 
        last_name = wufoo_json.get(last_name_field) 
        email = wufoo_json.get(email_field) 
        id_type = wufoo_json.get(identification_type_field) 
        id_number = wufoo_json.get(identification_number_field) 
        
        values = {}
        for wufoo_id, docuseal_name in field_mappings.items():
            if wufoo_id in wufoo_json:
                values[docuseal_name] = wufoo_json[wufoo_id]
        
        data = {
            "template_id": int(template_id),
            "send_email": False,
            "submitters": [
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "id_type": id_type,
                    "id_number": id_number,
                    "role": "Signer",
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
    api_key = os.environ.get('DOCUSEAL_API_KEY')
    if not api_key:
        raise ValueError("Missing or empty DOCUSEAL_API_KEY environment variable")
    headers = {
        "X-Auth-Token": api_key,
        "Content-Type": "application/json"
    }
    logger.info(f"Sending to DocuSeal with headers: {headers}")
    response = requests.post(url, json=docuseal_data, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_submission_link(response):
    try:
        print("Response received in extract_submission_link:", json.dumps(response, indent=2)) 

        if isinstance(response, list):
            submitters = response
        else:
            submitters = response.get('submitters', [])
        
        if not submitters:
            raise ValueError("No submitters in response")
        
        first_submitter = submitters[0]
        if not isinstance(first_submitter, dict):
            raise ValueError("First submitter is not a dictionary")
        
        embed_src = first_submitter['embed_src']  
        
        return embed_src
    
    except IndexError:
        raise ValueError("Expected response to be a non-empty list")
    
    except KeyError:
        raise ValueError("No 'embed_src' in the first entry")
        
    except Exception as e:
        print(f"Unexpected error in extract_submission_link: {str(e)}")
        raise

def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {}) or {}
    
    entry_id = query_params.get('entryId') 
    
    if not entry_id:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/plain'},
            'body': 'Error: No entry_id provided in query parameter (?entry=EntryId)'
        }

    try:
        wufoo_json = get_wufoo_json(entry_id)
        logger.info("Wufoo JSON: " + json.dumps(wufoo_json, indent=2))
        print("Fetch Data Successful")
        
        docuseal_data = prepare_docuseal_data(wufoo_json)
        print("Success Preparing Json")
        
        docuseal_response = send_to_docuseal(docuseal_data)
        logger.info("Docuseal Response: " + json.dumps(docuseal_response, indent=2))
        
        submission_link = extract_submission_link(docuseal_response)
        print("Submission link Created")

        return {
            'statusCode': 302,
            'headers': {'Location': submission_link},
            'body': ''
        }
        
    except Exception as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Error: {str(e)}'
        }
