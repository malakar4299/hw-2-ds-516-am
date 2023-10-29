# Import the Secret Manager client library.
from google.cloud import secretmanager

# GCP project in which to store secrets in Secret Manager.
project_id = "ds-561-am"

# ID of the secret to create.
secrets = {"db_user":"amalakar","db_pass":"h2-6-am","db_name":"hw-5","sql_INSTANCE_CONNECTION_NAME":"ds-561-am:us-central1:hw-6-db","pub_ip":"34.29.77.158"}

for secret in secrets.keys():

    # ID of the secret to create.
    # secret_id = "pub_ip"

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the parent name from the project.
    parent = f"projects/{project_id}"

    # Create the parent secret.
    secret = client.create_secret(
        request={
            "parent": parent,
            "secret_id": secret,
            "secret": {"replication": {"automatic": {}}},
        }
    )

    # Add the secret version.
    version = client.add_secret_version(
        request={"parent": secret.name, "payload": {"data":b""+ secrets[secret]}}
    )

    # Access the secret version.
    response = client.access_secret_version(request={"name": version.name})

    # Print the secret payload.
    #
    # WARNING: Do not print the secret in a production environment - this
    # snippet is showing how to access the secret material.
    payload = response.payload.data.decode("UTF-8")
    print(f"Plaintext: {payload}")