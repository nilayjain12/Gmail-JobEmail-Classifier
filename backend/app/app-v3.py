from flask import Flask, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv
import os
import logging
import config
from utils.authenticate import authorize_user, handle_oauth2callback, register_push_notification
from utils.email_handling import get_latest_emails
from utils.pubsub_service import handle_webhook

# Load environment variables
load_dotenv(os.path.join(config.BASEDIR, '.env'))

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'gmail-authenticate'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route("/", methods=["GET"])
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    email_data = get_latest_emails()
    return render_template("index.html", emails=email_data)

@app.route('/authorize')
def authorize():
    return redirect(authorize_user())

@app.route('/oauth2callback')
def oauth2callback():
    credentials = handle_oauth2callback()
    register_push_notification(credentials)
    return redirect(url_for('index'))

@app.route('/webhook', methods=['POST'])
def webhook():
    return handle_webhook()

@app.route('/get_emails', methods=['GET'])
def get_emails():
    email_data = get_latest_emails()
    return jsonify(email_data)

@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('authorize'))

if __name__ == "__main__":
    logger.info("Starting Flask app.")
    app.run(debug=True)
