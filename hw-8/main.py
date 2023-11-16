from flask import Flask, Response, abort, request, make_response
from google.cloud import storage
from google.cloud import logging as gcloud_logging
from flask_cors import cross_origin
from google.cloud import pubsub_v1
import json

from google.cloud.sql.connector import Connector, IPTypes

import requests

app = Flask(__name__)

# Initialize an anonymous client
storage_client = storage.Client.create_anonymous_client()

bucket = storage_client.bucket('hw-2-files-bucket')

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('gcs-file-requests')

BANNED_COUNTRIES = ['North Korea', 'Iran', 'Cuba', 'Myanmar', 'Iraq', 'Libya', 'Sudan', 'Zimbabwe', 'Syria']
SECOND_APP_URL = "http://localhost:5001/alert"
HTTP_METHODS = ['GET','POST','PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

# GCP project in which to store secrets in Secret Manager.
project_id = "ds-561-am"

def get_instance_zone():
    """
    Fetches the zone information of the current GCP instance.
    """
    metadata_server = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
    metadata_flavor = {"Metadata-Flavor": "Google"}
    try:
        response = requests.get(metadata_server, headers=metadata_flavor)
        if response.status_code == 200:
            # The response includes the full zone path, so we split to get the last part
            return response.text.split('/')[-1]
    except requests.exceptions.RequestException:
        return "Unknown"


@cross_origin()
@app.route('/<path:filename>', methods=HTTP_METHODS)
def serve_file(filename):
    # Check HTTP method
    country = request.headers.get('X-country')
    client_ip = request.headers.get('X-client-IP')
    gender = request.headers.get('X-gender')
    age = request.headers.get('X-age')
    income = request.headers.get('X-income')
    is_banned = country in BANNED_COUNTRIES

    zone = get_instance_zone()  # Fetch the zone information

    if country in BANNED_COUNTRIES:
        # Initialize publisher client
        logger.log_text(f"APP 1 logging: banned country : {country} for file: {filename}")
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path('ds-561-am', 'banned-message-handler')

        data = {
            'country': country,
            'ip': request.headers.get('X-client-IP'),
            'filename': filename
        }

        """Publish details of a request from a banned country to Pub/Sub."""
        publisher.publish(topic_path, data=json.dumps(data).encode("utf-8"))
        # requests.post(SECOND_APP_URL, json=data)
        response = make_response("Permission Denied", 400)
        response.headers['X-Server-Zone'] = zone
        return response


    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        response = make_response("Not Implemented", 501)
        response.headers['X-Server-Zone'] = zone
        return response


    blob = bucket.blob('files/' + filename)
    if not blob.exists():
        logger.log_text(f"File not found, this is being logged from the code: {filename}")
        response = make_response("File not found", 404)
        response.headers['X-Server-Zone'] = zone
        return response

    content = blob.download_as_text()
    
    response = make_response(content, mimetype='text/html')  # Adjust the mimetype based on your file types
    response.headers['X-Server-Zone'] = zone
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
