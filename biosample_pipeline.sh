#/bin/bash
omicidx_builder biosample download
omicidx_builder biosample parse biosample_set.xml.gz biosample.json
omicidx_builder biosample upload
omicidx_builder biosample load
omicidx_builder biosample etl-to-public
omicidx_builder biosample gcs-dump
omicidx_builder biosample gcs-to-elasticsearch
