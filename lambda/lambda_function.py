import json, requests, logging
from Wufoo_Docuseal_Integration import get_wufoo_json, prepare_docuseal_data, send_to_docuseal, extract_submission_link

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {}) or {}
    
    entry_id = query_params.get('entry') 
    
    if not entry_id:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/plain'},
            'body': 'Error: No entry_id provided in query parameter (?entry=EntryId)'
        }

    try:
        wufoo_json = get_wufoo_json(entry_id)
        docuseal_data = prepare_docuseal_data(wufoo_json)
        docuseal_response = send_to_docuseal(docuseal_data)
        logger.info("Docuseal Response: " + json.dumps(docuseal_response, indent=2))
        
        submission_link = extract_submission_link(docuseal_response)
        
        return {
            'statusCode': 301,
            'headers': {
                'Location': submission_link
            },
            'body': ''  # Body can be empty for redirects
        }
        
    except Exception as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Error: {str(e)}'
        }