from flask import Flask, redirect, url_for, session, render_template, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import os
import config

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'admin'  # Replace with a strong secret key

# Scopes for read-only Gmail access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

@app.route('/')
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

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
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
            from_email = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")
            snippet = msg.get('snippet', '')
            email_data.append({'subject': subject, 'from': from_email, 'snippet': snippet})

    return render_template('index.html', emails=email_data)


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

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)