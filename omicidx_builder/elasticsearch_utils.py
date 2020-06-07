import elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import connections
from omicidx_builder.config import config
import json
import logging
import gzip
logging.basicConfig(level=logging.INFO, format=logging.BASIC_FORMAT)
import os


def init_connection_object():
    connections.create_connection(alias='default',
                                  hosts=config.ES_HOST,
                                  retry_on_timeout=True,
                                  max_retries=3,
                                  timeout=30)


init_connection_object()


def get_client() -> elasticsearch.client:
    return connections.get_connection()


client = get_client()


def prep_data(fname, index, id_field):
    with gzip.open(fname) as f:
        for line in f:
            d = json.loads(line)
            d['_index'] = index
            if (id_field is not None):
                if (id_field in d):
                    d['_id'] = d[id_field]
                else:
                    continue
            yield (d)


def bulk_index(fname, index, id_field=None, **kwargs):
    bulk(get_client(), prep_data(fname, index, id_field), **kwargs)


def put_template(template_name: str, template_body: dict):
    client.indices.put_template(template_name, template_body)


def bulk_index_from_gcs(bucket, prefix, index, id_field=None, **kwargs):
    """Perform bulk indexing from a set of gcs blobs

    Parameters
    ----------
    bucket: str
        GCS bucket name
    prefix: str
        The prefix string (without wildcard) to get the right blobs
    index: str
        The elasticsearch index name
    id_field: str
        The id field name (default None) that will be used as the
        `_id` field in elasticsearch
    """
    from tempfile import NamedTemporaryFile
    from .gcs_utils import list_blobs
    logging.info(f'{bucket}/{prefix}')
    flist = list(list_blobs(bucket, prefix))
    logging.info(f'Found {len(flist)} files for indexing')
    for i in flist:
        tmpfile = NamedTemporaryFile()
        if (i.name.endswith('.gz')):
            tmpfile = NamedTemporaryFile(suffix='.gz')
        logging.info('Downloading ' + i.name)
        i.download_to_filename(tmpfile.name)
        logging.info('Indexing ' + i.name)
        bulk_index(tmpfile.name, index, id_field=id_field, **kwargs)
        tmpfile.close()


def delete_index(index):
    """Delete the named index"""
    if client.indices.exists(index):
        client.indices.delete(index)
    else:
        logging.warn(f"index {index} does not exist, so not deleted!")


def create_alias(alias: str, index: str):
    """Create an alias for an index

    Parameters
    ----------
    alias: str
        the alias name
    index: str
        the index name
    """
    if client.indices.exists(index):
        client.indices.put_alias(index, alias)
        logging.info(f"alias {alias} for index {index} created")
    else:
        logging.warn(
            f"index {index} does not exist, so alias {alias} not created")


def delete_alias(alias: str, index: str = None):
    """Create an alias for an index

    Parameters
    ----------
    alias: str
        the alias name
    index: str
        the index name
    """
    if client.indices.exists_alias(index, alias):
        client.indices.delete_alias(index, alias)
        logging.info(f"alias {alias} for index {index} deleted")
    else:
        logging.warn(f"alias {alias} does not exist")


def swap_indices_behind_alias(alias: str, old_index: str, new_index: str):
    """Swap the alias for old_index to point to new_index

    This just swaps the alias, nothing more. If the new index
    does not exist, this function is a no-op.

    Parameters
    ----------
    alias: str
        The alias to re-assign

    old_index: str
        The name of the old index. This index remains intact; only 
        the alias changes.
    
    new_index: str
        The name of the new index to which to assign the alias.
    """
    if client.indices.exists(index=new_index):
        for index in index_for_alias(alias).keys():
            delete_index(index)
        client.indices.put_alias(index=new_index, name=alias)
        logging.info(f"alias {alias} for index {new_index} created")
    else:
        logging.warn(
            f"new index {new_index} does not exist, so alias {alias} remains unchanged"
        )


def index_for_alias(alias: str):
    """get the name of the index for a given alias

    Parameters
    ----------
    alias: str
       The name of the alias

    Returns
    -------
    str: the name of the matching index (or None)
    """
    res = None
    try:
        res = client.indices.get_alias(name=alias)
    except:
        return None
    return res
