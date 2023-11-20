MY_INSTANCE_NAME="hw-8-app-1-b"
ZONE=us-central1-a

gcloud compute instances create $MY_INSTANCE_NAME \
    --image-family=debian-10 \
    --image-project=debian-cloud \
    --machine-type=e2-micro \
    --scopes userinfo-email,cloud-platform \
    --metadata-from-file startup-script=startup-script.sh \
    --zone $ZONE \
    --tags http-server,https-server
