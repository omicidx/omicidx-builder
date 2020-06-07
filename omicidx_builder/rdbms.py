import databases
import asyncio
import sqlalchemy
from sqlalchemy.dialects.postgresql.json import JSONB

metadata = sqlalchemy.MetaData()

geo_jsonb = sqlalchemy.Table(
    "geo_jsonb",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("accession", sqlalchemy.String(length=100)),
    sqlalchemy.Column("doc", JSONB),
)

database = databases.Database(
    'postgresql://postgres:this2222@localhost:5432/omicidx',
    min_size=5,
    max_size=20)


async def main():

    await database.connect()
    stmt = geo_jsonb.select()
    res = await database.fetch_all(stmt)
    for r in res:
        print(r['accession'])
    await insert_record('abc', {'abc': 123})


async def get_saved_gses():
    async with databases.Database(
            'postgresql://postgres:this2222@localhost:5432/omicidx') as db:
        stmt = geo_jsonb.select(geo_jsonb.c.accession)
        res = [r.get(0) for r in await db.fetch_all(stmt)]
        return res


async def insert_records(vals):
    async with databases.Database(
            'postgresql://postgres:this2222@localhost:5432/omicidx') as db:
        stmt = 'insert into geo_jsonb (accession, doc) values (:accession, :doc)'

        stmt = geo_jsonb.insert()
        res = await db.execute_many(stmt, vals)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
