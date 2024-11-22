from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import base64
import json
import logging
import config
import pickle

# Allow insecure transport for testing purposes
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Flask app setup
app = Flask(__name__)
app.secret_key = "your_secret_key"

# OAuth and API setup
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/pubsub"]
CLIENT_SECRETS_FILE = os.path.join(config.BASEDIR, 'config', 'credentials.json')  # Replace with your credentials file
REDIRECT_URI = "http://localhost:5000/oauth2callback"
WEBHOOK_URL = "https://mpa9adbc7ad7f1a56488.free.beeceptor.com"  # Replace with your webhook URL
PUBSUB_TOPIC = "projects/job-email-classifier-442106/topics/job-email-classifier"
PROJECT_ID = "job-email-classifier-442106"
SUBSCRIPTION_NAME = "job-email-classifier-sub"

# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google OAuth flow setup
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
)

emails_received = []
# In-memory storage for credentials
user_credentials = {}

@app.route("/", methods=["GET"])
def index():
    """Render the HTML page that will display the messages."""
    # Check if the user is authorized
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    # Fetch the latest emails
    email_data = get_latest_emails()
    return render_template("index.html", emails=email_data)

@app.route('/authorize')
def authorize():
    # Initialize the OAuth 2.0 flow
    flow = Flow.from_client_secrets_file(os.path.join(config.BASEDIR, 'config', 'credentials.json'), scopes=SCOPES, redirect_uri=REDIRECT_URI)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    flow = Flow.from_client_secrets_file(os.path.join(config.BASEDIR, 'config', 'credentials.json'), scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI)
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
        "topicName": PUBSUB_TOPIC,  # This should match the Pub/Sub topic
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

def get_latest_emails():
    if 'credentials' not in session:
        return []

    # Load credentials from session
    credentials = pickle.loads(session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)

    # Retrieve the latest email
    results = service.users().messages().list(userId='me', maxResults=1).execute()
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

            # Extract the email body
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':  # Extract plain text only
                        body = part['body'].get('data', ' ')
                        break
                    elif part['mimeType'] == 'text/html':  # If plain text isn't available, fallback to HTML
                        body = part['body'].get('data', ' ')
                        break
            else:
                # Check if the body is directly in the payload
                body = payload.get('body', {}).get('data', '')

            # Decode the base64url encoded email body
            if body:
                body = base64.urlsafe_b64decode(body).decode('utf-8')

            # Add the email data to the list
            email_data.append({
                'subject': subject,
                'from': from_email,
                'body': body.strip()  # Strip extra whitespace from the body
            })

    return email_data

@app.route('/get_emails', methods=['GET'])
def get_emails():
    """Endpoint to fetch the latest emails as JSON."""
    email_data = get_latest_emails()  # Call the function to get the latest emails
    return jsonify(email_data)  # Return the email data as JSON

@app.route('/logout')
def logout():
    """Clear the session and redirect to the authorization page."""
    session.pop('credentials', None)  # Remove the credentials from the session
    return redirect(url_for('authorize'))  # Redirect to authorization

# callback function, listen_for_messages, and other routes remain unchanged.

if __name__ == "__main__":
    logger.info("Starting Flask app.")
    app.run(debug=True)