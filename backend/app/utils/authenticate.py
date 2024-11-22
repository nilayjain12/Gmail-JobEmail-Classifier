from flask import session, request, redirect, url_for
from google_auth_oauthlib.flow import Flow
import os
import config
import pickle
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(config.BASEDIR, '.env'))

# Google OAuth flow setup
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/pubsub"]
CLIENT_SECRETS_FILE = os.path.join(config.BASEDIR, 'config', 'credentials.json')
REDIRECT_URI = os.getenv('REDIRECT_URI')
PUBSUB_TOPIC = os.getenv('PUBSUB_TOPIC')

def authorize_user():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state  # Ensure this line is executed
    return authorization_url


def handle_oauth2callback():
    state = session.get('state')
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI)
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = pickle.dumps(credentials)
    return credentials

def register_push_notification(credentials):
    service = build('gmail', 'v1', credentials=credentials)
    watch_request = {
        "topicName": PUBSUB_TOPIC,
        "labelIds": ["INBOX"]
    }
    service.users().watch(userId='me', body=watch_request).execute()
