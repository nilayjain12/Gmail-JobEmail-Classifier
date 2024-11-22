import json
from flask import request

def handle_webhook():
    data = request.get_json()
    if data:
        email_data = json.loads(data['message']['data'])
        print("New email received:", email_data)
    return '', 200
