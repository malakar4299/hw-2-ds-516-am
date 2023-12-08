from flask import Flask, Response, abort, request
from google.cloud import storage
from google.cloud import logging as gcloud_logging
from flask_cors import cross_origin
from google.cloud import pubsub_v1
import json
import datetime

import sqlalchemy

from google.cloud.sql.connector import Connector, IPTypes
import pymysql

import sqlalchemy

# Import the Secret Manager client library.
from google.cloud import secretmanager

app = Flask(__name__)

# Initialize an anonymous client
storage_client = storage.Client.create_anonymous_client()

bucket = storage_client.bucket('ds-561-gcs-bucket-am')

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('gcs-file-requests')

BANNED_COUNTRIES = ['North Korea', 'Iran', 'Cuba', 'Myanmar', 'Iraq', 'Libya', 'Sudan', 'Zimbabwe', 'Syria']
SECOND_APP_URL = "http://localhost:5001/alert"
HTTP_METHODS = ['GET','POST','PUT', 'DELETE', 'HEAD', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

# GCP project in which to store secrets in Secret Manager.
project_id = "ds-561-am"

# ID of the secret to create.
secret_ids = ["db_user","db_pass","db_name","sql_INSTANCE_CONNECTION_NAME","pub_ip"]

creds = {}

def access_secret_version(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(name=name)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

for secret_id in secret_ids:
    # Access the secret version.
    
    creds[secret_id] = access_secret_version(secret_id=secret_id)

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.

    Uses the Cloud SQL Python Connector package.
    """

    global creds

    instance_connection_name = creds["sql_INSTANCE_CONNECTION_NAME"]  # e.g. 'project:region:instance'
    db_user = creds["db_user"]  # e.g. 'my-db-user'
    db_pass = creds["db_pass"]  # e.g. 'my-db-password'
    db_name = creds["db_name"]  # e.g. 'my-database'

    ip_type = IPTypes.PUBLIC

    connector = Connector(ip_type)

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )

        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800, 
    )
    return pool




def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    return connect_with_connector()


# create 'votes' table in database if it does not already exist
def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    """Creates the `users`, `requests`, `failed-requests` tables if it doesn't exist."""
    with db.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                    "CREATE TABLE IF NOT EXISTS Users (user_id INT AUTO_INCREMENT PRIMARY KEY, client_ip VARCHAR(15), gender VARCHAR(10), age INT, income FLOAT, is_banned BOOLEAN);"
            )
        )

        conn.execute(
            sqlalchemy.text(
                    "CREATE TABLE IF NOT EXISTS Requests (request_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, country VARCHAR(50), time_of_day TIME, requested_file VARCHAR(255),FOREIGN KEY(user_id) REFERENCES Users(user_id));"
            )
        )

        conn.execute(
            sqlalchemy.text(
                     "CREATE TABLE IF NOT EXISTS FailedRequests (request_id INT AUTO_INCREMENT PRIMARY KEY, time_of_request TIMESTAMP, requested_file VARCHAR(255), error_code INT);"
            )
        )

        
        conn.commit()


db = None


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
    client_ip = request.headers.get('X-client-IP')
    gender = request.headers.get('X-gender')
    age = request.headers.get('X-age')
    income = request.headers.get('X-income')
    is_banned = country in BANNED_COUNTRIES

    global db

    request_id = 0

    db = init_connection_pool()

    stmt_user = sqlalchemy.text(
        "INSERT INTO Users (client_ip, gender, age, income, is_banned) VALUES (:client_ip, :gender, :age, :income, :is_banned)"
    )

    stmt_request = sqlalchemy.text(
        "INSERT INTO Requests (user_id, country, time_of_day, requested_file) VALUES (:user_id, :country, :time, :requested_file)"
   )

    time_cast = datetime.datetime.now(tz=datetime.timezone.utc)
    try:
        with db.connect() as conn:
            res = conn.execute(stmt_user, parameters={"client_ip": client_ip, "gender": gender, "age":age, "income": income, "is_banned":is_banned})
            res_req = conn.execute(stmt_request, parameters={"user_id": res.lastrowid, "country":country, "time": time_cast, "requested_file":filename})
            request_id = res_req.lastrowid

            conn.commit()
    except Exception as e:
        print(e)
        return Response(
            status=500,
            response="Unable to successfully cast vote! Please check the "
            "application logs for more details.",
        )

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
        push_failed(db, request_id, time_cast, filename, 400)
        return "Permission Denied", 400


    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        push_failed(db, request_id, time_cast, filename, 501)
        return "Not Implemented", 501

    blob = bucket.blob('files/' + filename)
    if not blob.exists():
        logger.log_text(f"File not found, this is being logged from the code: {filename}")
        push_failed(db, request_id, time_cast, filename, 404)
        abort(404)

    content = blob.download_as_text()
    return Response(content, mimetype='text/html'), 200  # Adjust the mimetype based on your file types


def push_failed(db, request_id, time, requested_file, error_code):
    db = init_connection_pool()

    stmt_failed = sqlalchemy.text(
        "INSERT INTO FailedRequests (request_id, time_of_request, requested_file, error_code) VALUES (:request_id, :time_of_request, :requested_file, :error_code)"
    )

    try:
        with db.connect() as conn:
            res = conn.execute(stmt_failed, parameters={"request_id": request_id, "time_of_request": time, "requested_file":requested_file, "error_code": error_code})
            conn.commit()
    except Exception as e:
        print(e)
        return Response(
            status=500,
            response="Unable to successfully cast vote! Please check the "
            "application logs for more details.",
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
