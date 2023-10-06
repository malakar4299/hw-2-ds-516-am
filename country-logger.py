from flask import Flask, request
from google.cloud import logging as gcloud_logging

app = Flask(__name__)

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('forbidden-requests')

@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    country = data.get('country')
    ip = data.get('ip')
    filename = data.get('filename')
    
    log_message = f"FORBIDDEN REQUEST! Country: {country}, IP: {ip}, Requested File: {filename}"
    logger.log_text(log_message)
    return "Alert Received", 200

if __name__ == '__main__':
    app.run(port=5001, debug=True)  # Running on a different port from the first app.
