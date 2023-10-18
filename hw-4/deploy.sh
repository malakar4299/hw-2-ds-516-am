MY_INSTANCE_NAME="hw-4-app-1"
ZONE=us-central1-a

gcloud compute instances create $MY_INSTANCE_NAME \
    --image-family=debian-10 \
    --image-project=debian-cloud \
    --machine-type=e2-micro \
    --scopes userinfo-email,cloud-platform \
    --metadata-from-file startup-script=startup-script.sh \
    --zone $ZONE \
    --tags http-server,https-server


gcloud compute addresses create hw-app-1-static --project=ds-561-am --network-tier=STANDARD --region=us-central1

gcloud compute instances add-access-config hw-4-app-1 --project=ds-561-am --zone=us-central1-a --address=IP_OF_THE_NEWLY_CREATED_STATIC_ADDRESS --network-tier=STANDARD