FROM python:3.7
LABEL maintainer="seandavi@gmail.com"
LABEL project="omicidx-builder"
LABEL description="usage: docker run seandavi/omicidx-builder ..."

ENV ES_HOST=""
ENV GCS_STAGING_PATH=""
ENV GCS_EXPORT_PATH=""

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.0.0

# System deps:
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY poetry.lock pyproject.toml ./

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY . ./

RUN apt-get update && apt-get install libpq-dev gcc

RUN poetry install


CMD ["/usr/local/bin/omicidx_builder"]
