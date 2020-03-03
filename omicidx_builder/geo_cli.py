from .click_root import cli
import click
import omicidx.geo.parser as gm
import logging
logger = logging.getLogger()
from .rdbms import insert_records, get_saved_gses
import asyncio

@cli.group('geo')
def geo():
    pass

@geo.command('get-series', help='print out series accessions between specified dates')
@click.option('--from_date', '-f', default='2005-01-01', help='format as 2005-01-01')
@click.option('--to_date', '-t', default='2030-01-01', help='format as 2030-01-01')
def get_series(from_date, to_date):
    n = 0
    from_date = from_date.replace('-','/')
    to_date = to_date.replace('-','/')
    
    for g in gm.get_geo_accessions(add_term=f"{from_date}:{to_date}[PDAT]", etyp="GSE"):
        n+=1
        print(g)
        if(n % 1000 == 0):
            logger.info('sent {} records'.format(n))


async def _insert_gse_to_db(gse):
    vals = []
    avail_gses = get_saved_gses()
    if(gse in avail_gses):
        return True
    for z in gm.geo_soft_entity_iterator(gm.get_geo_accession_soft(gse)):
        vals.append({'accession':z.accession, 'doc': z.json()})
    await insert_records(vals)

@geo.command('gse-to-json')
@click.argument('gse')
def gse_to_json(gse):
    asyncio.run(_insert_gse_to_db(gse))
