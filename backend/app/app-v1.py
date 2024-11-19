from flask import Flask, redirect, url_for, session, render_template, request, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import os
import config
import google.auth
from google.cloud import pubsub_v1
import json
import time

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'admin'  # Replace with a strong secret key

# Scopes for Gmail access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Your Google Cloud Project and Pub/Sub topic
PROJECT_ID = 'job-email-classifier-442106'
TOPIC_NAME = 'projects/job-email-classifier-442106/topics/job-email-classifier'

@app.route('/')
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    return render_template('index.html')


@app.route('/authorize')
def authorize():
    # Initialize the OAuth 2.0 flow
    flow = Flow.from_client_secrets_file(os.path.join(config.BASEDIR, 'config', 'credentials.json'), scopes=SCOPES, redirect_uri='http://127.0.0.1:5000/oauth2callback')
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(os.path.join(config.BASEDIR, 'config', 'credentials.json'), scopes=SCOPES, state=state, redirect_uri='http://127.0.0.1:5000/oauth2callback')
    flow.fetch_token(authorization_response=request.url)

    # Save credentials in the session
    credentials = flow.credentials
    session['credentials'] = pickle.dumps(credentials)

    # Register Gmail push notifications (Webhook for receiving new emails)
    register_push_notification(credentials)

    return redirect(url_for('index'))


def register_push_notification(credentials):
    # Register for push notifications with Gmail API
    service = build('gmail', 'v1', credentials=credentials)
    watch_request = {
        "topicName": f"projects/{PROJECT_ID}/topics/job-email-classifier",  # This should match the Pub/Sub topic
        "labelIds": ["INBOX"]
    }

    service.users().watch(userId='me', body=watch_request).execute()


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data:
        # Extract new email information from the Pub/Sub message
        email_data = json.loads(data['message']['data'])

        # Store or process the email data in some way (e.g., saving it in memory, database, etc.)
        # Here we're assuming the email data is added to some global variable or database
        print("New email received:", email_data)

    return '', 200


@app.route('/get_emails', methods=['GET'])
def get_emails():
    if 'credentials' not in session:
        return jsonify({"error": "Not authenticated"}), 401

    # Load credentials from session
    credentials = pickle.loads(session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)

    # Retrieve the latest email
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    email_data = []
    if messages:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']

            # Extract Subject and From fields
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
            from_email = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")

            # Extract the email body (can be plain text or HTML)
            body = ""
            for part in payload.get('parts', []):
                if part['mimeType'] == 'text/plain':
                    body = part['body']['data']
                    break
                elif part['mimeType'] == 'text/html':
                    # You can choose to use HTML body instead of plain text
                    body = part['body']['data']
                    break

            # Decode the base64url encoded email body
            if body:
                import base64
                body = base64.urlsafe_b64decode(body).decode('utf-8')

            # If the body is not found in parts, check the body of the payload itself
            if not body and 'body' in payload:
                body = payload['body'].get('data', '')
                if body:
                    body = base64.urlsafe_b64decode(body).decode('utf-8')

            # Add the email data to the list
            email_data.append({
                'subject': subject,
                'from': from_email,
                'body': body
            })

    return jsonify(email_data)


@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
