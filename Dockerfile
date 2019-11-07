FROM python:3.7
LABEL maintainer="seandavi@gmail.com"
LABEL project="omicidx-builder"
LABEL description="usage: docker run seandavi/omicidx-builder ..."

RUN apt-get update && apt-get install libpq-dev gcc

COPY . omicidx_builder/

RUN cd omicidx_builder && pip install .


CMD ["/usr/local/bin/omicidx_builder"]
