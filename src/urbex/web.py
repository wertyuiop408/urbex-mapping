import urllib.parse

from db_base import session_factory
from db_tables import places, refs
from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response_containers import Template
from litestar.static_files.config import StaticFilesConfig
from litestar.template.config import TemplateConfig
from sqlalchemy import select, text

db = session_factory()

"""
http://127.0.0.1:8000/schema/redoc
http://127.0.0.1:8000/schema/elements
http://127.0.0.1:8000/schema/swagger
"""


@get("/")
async def index() -> Template:
    return Template(name="index.html")


@get("/latest")
async def latest() -> Template:
    return Template(name="latest.html")


@get("/bounds/{ne_lat: decimal}/{ne_lng: decimal}/{sw_lat: decimal}/{sw_lng: decimal}")
async def get_bounds(
    ne_lat: float, ne_lng: float, sw_lat: float, sw_lng: float
) -> list[dict[str, str | bool]]:
    mysel = (
        select(places)
        .where(places.lat < ne_lat)
        .where(places.lat > sw_lat)
        .where(places.long < ne_lng)
        .where(places.long > sw_lng)
    )

    res = db.scalars(mysel).all()
    print(len(res))

    geojson = {"type": "FeatureCollection", "features": list()}

    for row in res:
        yy = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row.long, row.lat]},
            "properties": {"name": row.name, "pid": row.row_id, "loc": ""},
        }
        geojson["features"].append(yy)
    return geojson

    """
        #tags = get_tags(x["row_id"])
   
                "loc": tags
    
    SELECT row_id, name, lat, long
        FROM places
        WHERE lat < ? and lat > ? and long < ? and long > ?
        AND (places.status NOT IN (1, 4) OR places.status IS NULL)
    [ne_lat, sw_lat, ne_lng, sw_lng])
    """


@get("/search/{query_: str}")
async def search(query_: str) -> list[dict[str, str | bool]]:
    geojson = {"type": "FeatureCollection", "features": list()}
    if len(query_) < 3:
        return geojson

    # search the virtual table for the tag, and order it by the bm25 algorithm. Then grab the related place
    stmt = text(
        """SELECT places.row_id, places.long, places.lat, places.name, tagquery.tag FROM
            (SELECT rowid, tag, bm25(tags_ft) AS bm25 FROM tags_ft WHERE tags_ft.tag MATCH :query LIMIT 10) AS tagquery
        LEFT JOIN tag_rel ON tag_rel.tag_id=tagquery.rowid
        LEFT JOIN places ON tag_rel.place_id=places.row_id
        ORDER BY tagquery.bm25"""
    )

    res = db.execute(stmt, {"query": f"{query_}*"}).all()
    print(len(res))

    for row in res:
        yy = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row[1], row[2]]},
            "properties": {"name": row[3], "pid": row[0], "loc": ""},
        }
        geojson["features"].append(yy)

    return geojson


def condition(query_, row, value) -> select:
    value = urllib.parse.unquote(value)

    if value[:2] == ">=" or value[:2] == "<=" or value[:2] == "<>":
        if value[:2] == ">=":
            query_ = query_.where(row >= value[2:])

        elif value[:2] == "<=":
            query_ = query_.where(row <= value[2:])

        elif value[:2] == "<>":
            query_ = query_.where(row != value[2:])

    elif value[0] == ">" or value[0] == "<" or value[0] == "=":
        if value[0] == ">":
            query_ = query_.where(row > value[1:])

        elif value[0] == "<":
            query_ = query_.where(row < value[1:])

        elif value[0] == "=":
            query_ = query_.where(row == value[1:])
    else:
        query_ = query_.where(row.like(f"%{value}%"))
    return query_


@get("/search2/sites")
async def search_sites(
    ID: str | None = None,
    Name: str | None = None,
    Status: str | None = None,
    foo: str | None = None,
) -> list[dict[str, str | bool]]:
    # foo isn't actually needed, but datatables needs something to query, so it's a sacrafice

    query_ = select(places)

    if ID:
        query_ = condition(query_, places.row_id, ID)

    if Name:
        query_ = condition(query_, places.name, Name)

    if Status:
        query_ = condition(query_, places.status, Status)

    query_ = query_.order_by(places.row_id.desc()).limit(200)
    # sometimes the webpage stops querying properly, never caught it before with below debug
    print(query_)
    res = db.scalars(query_).all()

    data = list()
    for row in res:
        data.append(
            {
                "id": row.row_id,
                "name": row.name,
                "loc": f"{row.lat},{row.long}",
                "status": row.status,
            }
        )

    return data


@get("/search2/refs")
async def search_refs(
    ID: str | None = None,
    URL: str | None = None,
    title: str | None = None,
    PID: str | None = None,
    Date: str | None = None,
) -> list[dict[str, str | bool]]:
    query_ = select(refs)

    if ID:
        query_ = condition(query_, refs.row_id, ID)

    if URL:
        query_ = condition(query_, refs.url, URL)

    if title:
        query_ = condition(query_, refs.title, title)

    if Date:
        query_ = condition(query_, refs.date_post, Date)

    query_ = query_.order_by(refs.row_id.desc()).limit(200)
    res = db.scalars(query_).all()

    data = list()
    for row in res:
        data.append(
            {
                "id": row.row_id,
                "url": row.url,
                "title": row.title,
                "pid": 0,
                "date": row.date_post,
            }
        )

    return data


# @app.route("/search/<query>")
app = Litestar(
    route_handlers=[index, latest, get_bounds, search, search_sites, search_refs],
    static_files_config=[StaticFilesConfig(directories=["static"], path="/static")],
    template_config=TemplateConfig(directory=".", engine=JinjaTemplateEngine),
)
