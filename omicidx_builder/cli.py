#!/usr/bin/env python
import click
import subprocess
import logging
import os
import omicidx
from .bigquery_utils import *
import omicidx.sra.parser
from .click_root import cli
from .geo_cli import geo
import argparse
import json
import logging
import collections
from xml.etree import ElementTree as et
from .utils import dateconverter


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger(__name__)


@cli.group(help="Use these commands to process SRA metadata")
def sra():
    pass


@sra.command("download",
             help="""Downloads the files necessary to build
             the SRA json conversions of the XML files.

             Files will be placed in the <mirrordir> directory. Mirrordirs
             have the format `NCBI_SRA_Mirroring_20190801_Full`.
             """)
@click.argument('mirrordir')
def download_mirror_files(mirrordir):
    logger.info('getting xml files')
    subprocess.run("wget -nH -np --cut-dirs=3 -r -e robots=off {}/{}/".format(
        "http://ftp.ncbi.nlm.nih.gov/sra/reports/Mirroring", mirrordir),
                   shell=True)

    logger.info('getting SRA Accessions file')
    subprocess.run(
        "wget ftp://ftp.ncbi.nlm.nih.gov/sra/reports/Metadata/SRA_Accessions.tab -P {}"
        .format(mirrordir),
        shell=True)



@sra.command("parse-entity",
             help="""SRA XML to JSON

             Transforms an SRA XML mirroring metadata file into
             corresponding JSON format files. JSON is line-delimited
             JSON (not an array).""")
@click.option('--entity', '-e', help="entity to process")
def process_xml_entity(entity):

    fname = "meta_{}_set.xml.gz".format(entity)

    entity = entity

    parsers = {
        'study': omicidx.sra.parser.SRAStudyRecord,
        'sample': omicidx.sra.parser.SRASampleRecord,
        'run': omicidx.sra.parser.SRARunRecord,
        'experiment': omicidx.sra.parser.SRAExperimentRecord
    }
    sra_parser = parsers[entity]

    import omicidx.sra.pydantic_models as p
    parsers = {
        'study': p.SraStudy,
        'sample': p.SraSample,
        'run': p.SraRun,
        'experiment': p.SraExperiment
    }
    pydantic_model = parsers[entity]

    logger.info('using {} entity type'.format(entity))
    logger.info('parsing {} records'.format(entity))
    n = 0
    outfname = "{}.json".format(entity)
    ENTITY = entity.upper()
    with open(outfname, 'w') as outfile:
        with omicidx.sra.parser.open_file(fname) as f:
            for event, element in et.iterparse(f):
                if (event == 'end' and element.tag == ENTITY):
                    rec = sra_parser(element).data
                    n += 1
                    if ((n % 100000) == 0):
                        logger.info('parsed {} {} entries'.format(entity, n))
                    outfile.write(
                        json.dumps(pydantic_model(**rec).dict(),
                                   default=dateconverter) + "\n")
                    element.clear()
            logger.info('parsed {} entity entries'.format(n))


@sra.command('upload', help="""Upload SRA json to GCS""")
@click.argument('mirrordir')
def upload_processed_sra_data(mirrordir):
    from .gcs_utils import upload_blob_to_gcs, parse_gcs_url

    for entity in 'study sample experiment run'.split():
        fname = entity + '.json'
        loc_fname = os.path.join(mirrordir, fname)
        upload_blob_to_gcs('temp-testing', loc_fname, 'abc/' + fname)

    fname = 'SRA_Accessions.tab'
    loc_fname = os.path.join(mirrordir, fname)
    (bucket, path) = parse_gcs_url(config.GCS_STAGING_URL)
    upload_blob_to_gcs(bucket, loc_fname, os.path.join(path,fname))


@sra.command(help="""Load gcs files to Bigquery""")
def load_sra_data_to_bigquery():
    from importlib import resources

    for i in 'study sample experiment run'.split():
        with resources.path('omicidx_builder.data.bigquery_schemas',
                            f"{i}.schema.json") as schemafile:
            load_json_to_bigquery('omicidx_etl',
                                  f'sra_{i}',
                                  f'gs://temp-testing/abc/{i}.json',
                                  schema=parse_bq_json_schema(schemafile))

    load_csv_to_bigquery('omicidx_etl',
                         'sra_accessions',
                         'gs://temp-testing/abc/SRA_Accessions.tab',
                         field_delimiter='\t',
                         null_marker='-',
                         quote_character="")


@sra.command(help="""ETL query to public schema for all SRA entities""")
def sra_to_bigquery():
    sql = """CREATE OR REPLACE TABLE `isb-cgc-01-0006.omicidx.sra_run` AS
SELECT 
  run.* EXCEPT (published, lastupdate, received, total_spots, total_bases, avg_length, run_date),
  CAST(acc.Updated as DATETIME) as lastupdate,
  CAST(acc.Published as DATETIME) as published,
  CAST(acc.Received as DATETIME) as received,
  CAST(run_date as DATETIME) as run_date,
  CAST(acc.Spots as INT64) as total_spots,
  CAST(acc.Bases as INT64) as total_bases,
  CAST(acc.Bases AS NUMERIC)/CAST(acc.Spots AS NUMERIC) as avg_length,
  acc.Sample as sample_accession,
  acc.Study as study_accession
FROM 
    `isb-cgc-01-0006.omicidx_etl.sra_run` run
  JOIN 
    `isb-cgc-01-0006.omicidx_etl.sra_accessions` acc
  ON acc.Accession = run.accession;
"""
    query(sql)

    sql = """CREATE OR REPLACE TABLE `isb-cgc-01-0006.omicidx.sra_experiment` AS
SELECT 
  expt.* EXCEPT (published, lastupdate, received),
  CAST(acc.Updated as DATETIME) as lastupdate,
  CAST(acc.Published as DATETIME) as published,
  CAST(acc.Received as DATETIME) as received
FROM 
    `isb-cgc-01-0006.omicidx_etl.sra_experiment` expt
  JOIN 
    `isb-cgc-01-0006.omicidx_etl.sra_accessions` acc
  ON acc.Accession = expt.accession;
    """
    query(sql)

    sql = """CREATE OR REPLACE TABLE `isb-cgc-01-0006.omicidx.sra_sample` AS
SELECT 
  sample.* EXCEPT (published, lastupdate, received),
  CAST(acc.Updated as DATETIME) as lastupdate,
  CAST(acc.Published as DATETIME) as published,
  CAST(acc.Received as DATETIME) as received,
  acc.Study as study_accession
FROM 
    `isb-cgc-01-0006.omicidx_etl.sra_sample` sample
  JOIN 
    `isb-cgc-01-0006.omicidx_etl.sra_accessions` acc
  ON acc.Accession = sample.accession;
    """
    query(sql)

    sql = """CREATE OR REPLACE TABLE `isb-cgc-01-0006.omicidx.sra_study` AS
WITH stat_agg AS (
SELECT
  COUNT(a.Accession) as sample_count,
  a.Study as study_accession
FROM 
  `isb-cgc-01-0006.omicidx_etl.sra_accessions` a
WHERE
  a.Type='SAMPLE'
GROUP BY 
  study_accession)
SELECT 
  study.* EXCEPT (published, lastupdate, received),
  CAST(acc.Updated as DATETIME) as lastupdate,
  CAST(acc.Published as DATETIME) as published,
  CAST(acc.Received as DATETIME) as received
FROM 
    `isb-cgc-01-0006.omicidx_etl.sra_study` study
  JOIN 
    `isb-cgc-01-0006.omicidx_etl.sra_accessions` acc
  ON acc.Accession = study.accession
  LEFT OUTER JOIN
    stat_agg on stat_agg.study_accession=study.accession;
    """
    query(sql)


def _sra_bigquery_for_elasticsearch():
    sql = """CREATE OR REPLACE TABLE omicidx_etl.sra_experiment_for_es AS
SELECT
  expt.*,
  STRUCT(samp).samp as sample,
  STRUCT(study).study as study
FROM 
  `isb-cgc-01-0006.omicidx.sra_experiment` expt 
  LEFT OUTER JOIN 
  `isb-cgc-01-0006.omicidx.sra_sample` samp
  ON samp.accession = expt.sample_accession
  LEFT OUTER JOIN 
  `isb-cgc-01-0006.omicidx.sra_study` study
  ON study.accession = expt.study_accession
WHERE samp.accession IS NOT NULL
AND study.accession IS NOT NULL
AND expt.study_accession is NOT NULL
AND expt.sample_accession is NOT NULL
    """
    query(sql)

    sql = """CREATE OR REPLACE TABLE omicidx_etl.sra_run_for_es AS
SELECT
  run.*,
  STRUCT(expt).expt as experiment,
  STRUCT(samp).samp as sample,
  STRUCT(study).study as study
FROM 
  `isb-cgc-01-0006.omicidx.sra_run` run
  LEFT OUTER JOIN
  `isb-cgc-01-0006.omicidx.sra_experiment` expt
  ON run.experiment_accession = expt.accession
  LEFT OUTER JOIN 
  `isb-cgc-01-0006.omicidx.sra_sample` samp
  ON samp.accession = expt.sample_accession
  LEFT OUTER JOIN 
  `isb-cgc-01-0006.omicidx.sra_study` study
  ON study.accession = expt.study_accession
WHERE samp.accession IS NOT NULL
AND study.accession IS NOT NULL
AND expt.study_accession is NOT NULL
AND expt.sample_accession is NOT NULL
AND run.experiment_accession IS NOT NULL
"""
    query(sql)

    sql = """CREATE OR REPLACE TABLE omicidx_etl.sra_sample_for_es AS
with agg_counts as 
(SELECT
  sample.accession,
  COUNT(DISTINCT(expt.accession)) as experiment_count,
  COUNT(DISTINCT(run.accession)) as run_count,
  SUM(CAST(run.total_bases as INT64)) as total_bases,
  SUM(CAST(run.total_spots as INT64)) as total_spots,
  AVG(CAST(run.total_bases as INT64)) as mean_bases_per_run
from `isb-cgc-01-0006.omicidx.sra_experiment` expt
JOIN `isb-cgc-01-0006.omicidx.sra_run` run
  ON run.experiment_accession = expt.accession and run.experiment_accession is not null and expt.accession is not null
JOIN `isb-cgc-01-0006.omicidx.sra_sample` sample
  ON expt.sample_accession = sample.accession and expt.sample_accession is not null and sample.accession is not null
JOIN `isb-cgc-01-0006.omicidx.sra_study` study
  ON expt.study_accession = study.accession and expt.study_accession is not null and study.accession is not null
group by sample.accession
)
select 
  sample.*,
  STRUCT(study).study,
  agg_counts.* except(accession)
from `isb-cgc-01-0006.omicidx.sra_experiment` expt
JOIN `isb-cgc-01-0006.omicidx.sra_sample` sample
  ON expt.sample_accession = sample.accession and expt.sample_accession is not null and sample.accession is not null
JOIN `isb-cgc-01-0006.omicidx.sra_study` study
  ON expt.study_accession = study.accession and expt.study_accession is not null and study.accession is not null
join agg_counts on agg_counts.accession=sample.accession
"""
    query(sql)

    sql = """CREATE OR REPLACE TABLE omicidx_etl.sra_study_for_es AS
with agg_counts as 
(SELECT
  study.accession,
  COUNT(DISTINCT(sample.accession)) as sample_count,
  COUNT(DISTINCT(expt.accession)) as experiment_count,
  COUNT(DISTINCT(run.accession)) as run_count,
  SUM(CAST(run.total_bases as INT64)) as total_bases,
  SUM(CAST(run.total_spots as INT64)) as total_spots,
  AVG(CAST(run.total_bases as INT64)) as mean_bases_per_run
from `isb-cgc-01-0006.omicidx.sra_experiment` expt
JOIN `isb-cgc-01-0006.omicidx.sra_run` run
  ON run.experiment_accession = expt.accession and run.experiment_accession is not null and expt.accession is not null
JOIN `isb-cgc-01-0006.omicidx.sra_sample` sample
  ON expt.sample_accession = sample.accession and expt.sample_accession is not null and sample.accession is not null
JOIN `isb-cgc-01-0006.omicidx.sra_study` study
  ON expt.study_accession = study.accession and expt.study_accession is not null and study.accession is not null
group by study.accession
)
select 
  study.*,
  agg_counts.* except(accession)
from `isb-cgc-01-0006.omicidx.sra_study` study
join agg_counts on agg_counts.accession=study.accession
"""
    query(sql)


@sra.command(help="""ETL queries to create elasticsearch tables in bigquery""")
def sra_bigquery_for_elasticsearch():
    _sra_bigquery_for_elasticsearch()


def _sra_gcs_to_elasticsearch(entity):
    from omicidx_builder.elasticsearch_utils import (
        bulk_index_from_gcs,
        swap_indices_behind_alias,
        index_for_alias,
        create_alias,
        delete_index
    )                                                
    import uuid
    e = str(uuid.uuid4())

    idx_name = 'sra_' + entity + '-' + e
    logger.info(f"creating index {idx_name}")
    bulk_index_from_gcs('omicidx-cancerdatasci-org',
                        'exports/sra/json/{}-'.format(entity),
                        idx_name,
                        id_field='accession')
    old_index = index_for_alias('sra_'+entity)
    if old_index is None:
        create_alias('sra_'+entity, idx_name)
        logger.info(f'alias sra_{entity} now points to {idx_name}')
    else:
        swap_indices_behind_alias('sra_'+entity, old_index, idx_name)
        logger.info(f'alias sra_{entity} now points to {idx_name}')
        delete_index(old_index)
        logger.info(f'deleted old index {old_index}')


@sra.command('gcs-to-elasticsearch',
             help="""ETL query to public schema for all SRA entities""")
@click.option(
    '--entity',
    '-e',
    multiple=True,
    help="Entity (study, sample, experiment, run). Multiple values can be used"
)
def sra_gcs_to_elasticsearch(entity):
    for e in entity:
        _sra_gcs_to_elasticsearch(e)


def _sra_to_gcs_for_elasticsearch(bucket: str="omicidx-cancerdatasci-org",
                                  path: str="exports/sra/json"):
    from google.cloud import storage
    client = storage.Client()
    blobs = client.list_blobs(bucket, prefix=path+'/')
    for blob in blobs:
        logging.info(f"deleting {blob.name}")
        blob.delete()
    for entity in 'experiment study sample run'.split():
        table_to_gcs(
            'omicidx_etl', f'sra_{entity}_for_es',
            f'gs://{bucket}/{path}/{entity}-*.json.gz'
        )


@sra.command("""gcs-dump""",
             help="Write json.gz format of sra entities to gcs")
def sra_to_gcs_for_elasticsearch():
    _sra_to_gcs_for_elasticsearch()


######################
# Biosample handling #
######################


@cli.group(help="Use these commands to process biosample records.")
def biosample():
    pass


from omicidx.biosample import BioSampleParser


def biosample_to_json(biosample_file: str, output: click.File):
    n = 0
    logging.info(f'starting biosample record parsing')
    for i in BioSampleParser(biosample_file):
        n+=1
        if (i is None):
            break
        if (n % 100000 == 0):
            logging.info(f'{n} biosample records parsed')
        output.write(i.as_json() + "\n")
    logging.info(f'completing biosample record parsing')


def download_biosample():
    subprocess.run(
        "wget ftp://ftp.ncbi.nlm.nih.gov/biosample/biosample_set.xml.gz",
        shell=True)


def upload_biosample():
    from .gcs_utils import upload_blob_to_gcs

    fname = 'biosample.json'
    (bucket, path) = parse_gcs_url(config.GCS_EXPORT_URL)
    upload_blob_to_gcs(bucket, loc_fname, os.path.join(path,fname))


def load_biosample_from_gcs_to_bigquery():

    load_json_to_bigquery('omicidx_etl', 'biosample',
                          'gs://temp-testing/abc/biosample.json')


@biosample.command("""download""",
                   help="Download biosample xml file from NCBI")
def download():
    download_biosample()


@biosample.command("""upload""", help="Download biosample xml file from NCBI")
def upload():
    upload_biosample()


@biosample.command("""parse""", help="Parse xml to json, output to stdout")
@click.argument('biosample_file')
@click.argument('output', type=click.File('w'))
def to_json(biosample_file, output):
    biosample_to_json(biosample_file, output)


@biosample.command("""load""",
                   help="Load the gcs biosample.json file to bigquery")
def load_biosample_to_bigquery():
    load_biosample_from_gcs_to_bigquery()


@biosample.command("""etl-to-public""",
                   help="ETL process (copy) from etl schema to public")
def biosample_to_public():
    copy_table('omicidx_etl', 'omicidx', 'biosample', 'biosample')


@biosample.command("""gcs-dump""",
                   help="Write json.gz format of biosample to gcs")
def biosample_to_gcs():
    table_to_gcs(
        'omicidx', 'biosample',
        'gs://omicidx-cancerdatasci-org/exports/biosample/json/biosample-*.json.gz'
    )


def _biosample_gcs_to_elasticsearch():
    from omicidx_builder.elasticsearch_utils import (
        bulk_index_from_gcs,
        swap_indices_behind_alias,
        index_for_alias,
        create_alias,
        delete_index
    )                                                
    import uuid
    e = str(uuid.uuid4())

    idx_name = 'biosample-' + e
    logger.info(f"creating index {idx_name}")
    bulk_index_from_gcs('omicidx-cancerdatasci-org',
                        'exports/biosample/json/biosample-',
                        idx_name,
                        max_retries=3,
                        chunk_size=2000,
                        id_field = 'accession'
    )
    old_index = index_for_alias('biosample')
    if old_index is None:
        create_alias('biosample', idx_name)
        logger.info(f'alias biosample now points to {idx_name}')
    else:
        swap_indices_behind_alias('biosample', old_index, idx_name)
        logger.info(f'alias biosample now points to {idx_name}')
        delete_index(old_index)
        logger.info(f'deleted old index {old_index}')

    
    from omicidx_builder.elasticsearch_utils import bulk_index_from_gcs


@biosample.command("gcs-to-elasticsearch")
def biosample_gcs_to_elasticsearch():
    _biosample_gcs_to_elasticsearch()


if __name__ == '__main__':
    cli()
