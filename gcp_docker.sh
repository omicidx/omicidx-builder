#!/bin/bash

# Run this locally to start two
# docker jobs running on GCP instances.
# Images are preemptible, so check to see that things
# worked.

#ES_HOST=""
#GCS_STAGING_URL=""
#GCS_EXPORT_URL=""

YMD=$1 # should look like 20200401
MIRROR_DIR=NCBI_SRA_Mirroring_${1}_Full
gcloud compute instances create-with-container ob-sra \
       --machine-type n1-standard-2 \
       --container-restart-policy='never' \
       --container-env MIRROR_DIR=$MIRROR_DIR \
       --container-env ES_HOST=$ES_HOST \
       --container-env GCS_STAGING_URL=$GCS_STAGING_URL \
       --container-env GCS_EXPORT_URL=$GCS_EXPORT_URL \
       --container-image seandavi/omicidx-builder \
       --boot-disk-size 100G \
       --container-command '/bin/bash' \
       --container-arg='./sra_pipeline.sh' \
       --scopes=cloud-platform
gcloud compute instances create-with-container ob-biosample \
       --machine-type n1-standard-2 \
       --container-restart-policy='never' \
       --container-env MIRROR_DIR=$MIRROR_DIR \
       --container-env ES_HOST=$ES_HOST \
       --container-env GCS_STAGING_URL=$GCS_STAGING_URL \
       --container-env GCS_EXPORT_URL=$GCS_EXPORT_URL \
       --container-image seandavi/omicidx-builder \
       --boot-disk-size 100G \
       --container-command '/bin/bash' \
       --container-arg='./biosample_pipeline.sh' \
       --scopes=cloud-platform
