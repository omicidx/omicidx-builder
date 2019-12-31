"""Create a basic Click instance. GEO, SRA, and Biosample 
groups then import `cli` from here to add groups"""
import click

@click.group(help="""Command-line interface for omicidx processing
""")
def cli():
    pass
