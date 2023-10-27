from flask import Flask, Response, abort, request
from google.cloud import storage
from google.cloud import logging as gcloud_logging
import requests
import functions_framework
from flask_cors import cross_origin
from google.cloud import pubsub_v1
import json
import datetime

import sqlalchemy

from connect_connector import connect_with_connector
from connect_connector_auto_iam_authn import connect_with_connector_auto_iam_authn
from connect_tcp import connect_tcp_socket
from connect_unix import connect_unix_socket

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


def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    # use a TCP socket when INSTANCE_HOST (e.g. 127.0.0.1) is defined
    if os.environ.get("INSTANCE_HOST"):
        return connect_tcp_socket()

    # use a Unix socket when INSTANCE_UNIX_SOCKET (e.g. /cloudsql/project:region:instance) is defined
    if os.environ.get("INSTANCE_UNIX_SOCKET"):
        return connect_unix_socket()

    # use the connector when INSTANCE_CONNECTION_NAME (e.g. project:region:instance) is defined
    if os.environ.get("INSTANCE_CONNECTION_NAME"):
        # Either a DB_USER or a DB_IAM_USER should be defined. If both are
        # defined, DB_IAM_USER takes precedence.
        return (
            connect_with_connector_auto_iam_authn()
            if os.environ.get("DB_IAM_USER")
            else connect_with_connector()
        )

    raise ValueError(
        "Missing database connection type. Please define one of INSTANCE_HOST, INSTANCE_UNIX_SOCKET, or INSTANCE_CONNECTION_NAME"
    )


# create 'votes' table in database if it does not already exist
def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    """Creates the `votes` table if it doesn't exist."""
    with db.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                "CREATE TABLE IF NOT EXISTS votes "
                "( vote_id SERIAL NOT NULL, time_cast timestamp NOT NULL, "
                "candidate VARCHAR(6) NOT NULL, PRIMARY KEY (vote_id) );"
            )
        )
        conn.commit()


# This global variable is declared with a value of `None`, instead of calling
# `init_db()` immediately, to simplify testing. In general, it
# is safe to initialize your database connection pool when your script starts
# -- there is no need to wait for the first request.
db = None


# init_db lazily instantiates a database connection pool. Users of Cloud Run or
# App Engine may wish to skip this lazy instantiation and connect as soon
# as the function is loaded. This is primarily to help testing.
@app.before_first_request
def init_db() -> sqlalchemy.engine.base.Engine:
    """Initiates connection to database and its' structure."""
    global db
    db = init_connection_pool()
    migrate_db(db)


@cross_origin()
@app.route('/<path:filename>', methods=HTTP_METHODS)
def serve_file(filename):
    # Check HTTP method
    country = request.headers.get('X-country')
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
        return "Permission Denied", 400


    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        return "Not Implemented", 501

    blob = bucket.blob('files/' + filename)
    if not blob.exists():
        logger.log_text(f"File not found, this is being logged from the code: {filename}")
        abort(404)

    content = blob.download_as_text()
    return Response(content, mimetype='text/html'), 200  # Adjust the mimetype based on your file types


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
