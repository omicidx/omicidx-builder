#!/bin/bash
export NCBI_MIRROR_DIR=$MIRROR_DIR
omicidx_builder sra download $NCBI_MIRROR_DIR
cd $NCBI_MIRROR_DIR
omicidx_builder sra parse-entity -e study
omicidx_builder sra parse-entity -e sample
omicidx_builder sra parse-entity -e experiment
omicidx_builder sra parse-entity -e run
cd ..
omicidx_builder sra upload $NCBI_MIRROR_DIR
omicidx_builder sra load-sra-data-to-bigquery
omicidx_builder sra sra-to-bigquery
omicidx_builder sra sra-bigquery-for-elasticsearch
omicidx_builder sra gcs-dump
omicidx_builder sra gcs-to-elasticsearch
