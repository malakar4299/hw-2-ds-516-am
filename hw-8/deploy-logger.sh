MY_INSTANCE_NAME="hw-4-app-2"
ZONE=us-central1-a

gcloud compute instances create $MY_INSTANCE_NAME \
    --image-family=debian-10 \
    --image-project=debian-cloud \
    --machine-type=e2-micro \
    --scopes userinfo-email,cloud-platform \
    --metadata-from-file startup-script=startup-script-logger.sh \
    --zone $ZONE \
    --tags http-server,https-server
