import click
import pubmed_parser as pp
import httpx
import io
import orjson
from .click_root import cli
import gzip
import datetime

def fix_mesh(mesh_str: str) -> list[dict[str, str]]:
    meshes = mesh_str.split(';')
    ret = []
    for mesh in meshes:
        split_mesh = mesh.strip().split(":")
        if len(split_mesh)<2:
            return []
        ret.append({
            # include curie
            'curie': "mesh:" + split_mesh[0],
            'term': split_mesh[1]
        })
    return ret

@cli.group("pubmed")
def pubmed():
    pass

@pubmed.command()
@click.argument('basefile')
def process(basefile: str):
    BASE_URL = "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/"
    fname = basefile + ".xml.gz"
    url = BASE_URL+fname
    response = httpx.get(url, follow_redirects=True)
    response.raise_for_status()
    xml_string = gzip.decompress(response.content)
    data = pp.parse_medline_grant_id(xml_string)
    data2 = pp.parse_medline_xml(xml_string, year_info_only=False,nlm_category =True,author_list=True,reference_list=True)
    with gzip.open(basefile + "-grants.ndjson.gz", "wb") as f:
        for d in data:
            f.write(orjson.dumps(d) + b"\n")
    with gzip.open(basefile + "-metadata.ndjson.gz", "wb") as f:
        for d in data2:
            d['basefile'] = basefile
            d['processed_at'] = datetime.datetime.now()
            d['mesh_terms']= fix_mesh(d['mesh_terms'])
            d['publication_types'] = fix_mesh(d['publication_types'])
            d['chemical_list'] = fix_mesh(d['chemical_list'])
            f.write(orjson.dumps(d) + b"\n")