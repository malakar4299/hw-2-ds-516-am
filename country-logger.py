from flask import Flask, request
from google.cloud import logging as gcloud_logging

from google.cloud import pubsub_v1
import json
import time

from google.cloud.pubsub_v1.types import PullRequest


app = Flask(__name__)

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('forbidden-requests')

# Initialize subscriber client
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path('ds-561-am', 'banned-message-subs')

def continuously_pull_and_log():
    """Continuously pull messages and log them."""
    while True:
        print("checking messages")
        pull_and_log_banned_requests()
        time.sleep(5)  # Sleep for 5 seconds before pulling again

def pull_and_log_banned_requests():
    """Pull messages from Pub/Sub and log them."""

    # Construct the request object
    pull_request = PullRequest(subscription=subscription_path, max_messages=10)

    # Pull messages using the request object
    response = subscriber.pull(request=pull_request)
    
    # Iterate over each received message
    ack_ids = []
    for msg in response.received_messages:
        
        # Decode the message data from bytes to string, then load as JSON
        message_data = json.loads(msg.message.data.decode('utf-8'))
        
        # Log the message details (you can format this however you prefer)
        print("Received forbidden request details:")
        print(f"Country: {message_data.get('country')}")
        print(f"IP Address: {message_data.get('ip')}")
        print(f"Requested File: {message_data.get('requested_file')}")
        print("-" * 50)

        log_message = f"FORBIDDEN REQUEST! Country: {message_data.get('country')}, IP: {message_data.get('ip')}, Requested File: {message_data.get('requested_file')}"
        logger.log_text(log_message)
        
        # Acknowledge receipt of the message
        ack_ids.append(msg.ack_id)

    # Acknowledge all received messages at once
    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})

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
    continuously_pull_and_log()
    app.run(port=5001, debug=True)  # Running on a different port from the first app.
