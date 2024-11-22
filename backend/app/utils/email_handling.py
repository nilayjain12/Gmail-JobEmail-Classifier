import base64
from flask import session
import pickle
from googleapiclient.discovery import build

def get_latest_emails():
    if 'credentials' not in session:
        return []

    credentials = pickle.loads(session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)

    results = service.users().messages().list(userId='me', maxResults=1).execute()
    messages = results.get('messages', [])

    email_data = []
    if messages:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']

            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
            from_email = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")

            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body'].get('data', ' ')
                        break
                    elif part['mimeType'] == 'text/html':
                        body = part['body'].get('data', ' ')
                        break
            else:
                body = payload.get('body', {}).get('data', '')

            if body:
                body = base64.urlsafe_b64decode(body).decode('utf-8')

            email_data.append({
                'subject': subject,
                'from': from_email,
                'body': body.strip()
            })

    return email_data
