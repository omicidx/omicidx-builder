#!/bin/bash

# Run this locally to start two
# docker jobs running on GCP instances.
# Images are preemptible, so check to see that things
# worked.

YMD=$1 # should look like 20200401
MIRROR_DIR=NCBI_SRA_Mirroring_${1}_Full
gcloud compute instances create-with-container ob-sra \
       --preemptible \
       --machine-type n1-standard-2 \
       --container-env MIRROR_DIR=$MIRROR_DIR \
       --container-image seandavi/omicidx-builder \
       --boot-disk-size 100G \
       --container-command '/bin/bash' \
       --container-arg='./sra_pipeline.sh'
gcloud compute instances create-with-container ob \
       --preemptible \
       --machine-type n1-standard-2 \
       --container-image seandavi/omicidx-builder \
       --boot-disk-size 100G \
       --container-command '/bin/bash' \
       --container-arg='./biosample_pipeline.sh'
