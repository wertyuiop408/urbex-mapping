from db_base import session_factory
from db_tables import places
from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response_containers import Template
from litestar.static_files.config import StaticFilesConfig
from litestar.template.config import TemplateConfig
from sqlalchemy import select

"""
http://127.0.0.1:8000/schema/redoc
http://127.0.0.1:8000/schema/elements
http://127.0.0.1:8000/schema/swagger
"""


@get("/")
async def index() -> Template:
    return Template(name="index.html")


@get("/a/{name:str}")
async def greeter(name: str) -> str:
    return "Hello, " + name


@get("/bounds/{ne_lat: decimal}/{ne_lng: decimal}/{sw_lat: decimal}/{sw_lng: decimal}")
async def get_bounds(
    ne_lat: int, ne_lng: int, sw_lat: int, sw_lng: int
) -> list[dict[str, str | bool]]:
    db = session_factory()
    mysel = (
        select(places)
        .where(places.lat < ne_lat)
        .where(places.lat > sw_lat)
        .where(places.long < ne_lng)
        .where(places.long > sw_lng)
    )
    # res = db.execute(mysel).all()
    # print(len(res))
    geojson = {"type": "FeatureCollection", "features": list()}

    for row in db.scalars(mysel):
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
async def search(query_: str) -> str:
    return ""


# @app.route("/search/<query>")
app = Litestar(
    route_handlers=[index, greeter, get_bounds, search],
    static_files_config=[StaticFilesConfig(directories=["static"], path="/static")],
    template_config=TemplateConfig(directory=".", engine=JinjaTemplateEngine),
)
