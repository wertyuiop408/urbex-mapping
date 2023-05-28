import urllib.parse
from dataclasses import asdict, dataclass
from functools import reduce
from typing import Annotated

from db_base import session_factory
from db_tables import association_table, places, refs
from litestar import Litestar, Request, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response_containers import Template
from litestar.static_files.config import StaticFilesConfig
from litestar.template.config import TemplateConfig
from sqlalchemy import bindparam, insert, select, text
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.elements import BinaryExpression

Session = scoped_session(session_factory)

"""
http://127.0.0.1:8000/schema/redoc
http://127.0.0.1:8000/schema/elements
http://127.0.0.1:8000/schema/swagger
"""


async def after_response(request: Request) -> None:
    Session.remove()


@get("/")
async def index() -> Template:
    return Template(name="index.html")


@get("/latest")
async def latest() -> Template:
    return Template(name="latest.html")


@dataclass
class pid_form:
    value: str
    oldpid: str
    id: str  # rowid


@dataclass
class pet:
    ref_id: int
    place_id: int


@post("/edit")
async def edit_pid(
    data: Annotated[pid_form, Body(media_type=RequestEncodingType.URL_ENCODED)]
) -> str:
    try:
        if data.value.strip(" ") == data.oldpid.strip(" "):
            return data.oldpid.strip(" ")

        newpid = {int(elem.strip()) for elem in data.value.split(",") if elem}
        oldpid = {int(elem.strip()) for elem in data.oldpid.split(",") if elem}

        # https://stackoverflow.com/questions/4211209/remove-all-the-elements-that-occur-in-one-list-from-another
        deleted = list(reduce(lambda x, y: filter(lambda z: z != y, x), newpid, oldpid))
        added = list(reduce(lambda x, y: filter(lambda z: z != y, x), oldpid, newpid))
        out = list()

        with Session() as db:
            if len(added) > 0:
                in_data = [asdict(pet(int(data.id), add)) for add in added]
                insert_stmnt = insert(association_table).prefix_with("OR IGNORE")
                db.execute(insert_stmnt, in_data)

            if len(deleted) > 0:
                stmt = text(
                    "DELETE FROM place_rel WHERE ref_id = :rid AND place_id IN :pid"
                )
                stmt = stmt.bindparams(
                    bindparam("rid", value=int(data.id)),
                    bindparam("pid", value=deleted, expanding=True),
                )
                xx = db.execute(stmt)
                sel = db.execute(
                    text("SELECT place_id FROM place_rel WHERE ref_id = :rid"),
                    {"rid": int(data.id)},
                ).all()
                for x in sel:
                    out.append(str(x[0]))
            db.commit()
        return ", ".join(out)

    except Exception as e:
        print(e)
        return


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
    with Session() as db:
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

    # search the virtual table for the tag, and order it by the bm25 algorithm using 'rank'. Then grab the related place
    stmt = text(
        """
        SELECT places.row_id,
            places.long,
            places.lat,
            places.name,
            tags_ft.tag FROM tag_rel
        JOIN places ON places.row_id=tag_rel.place_id
        JOIN tags_ft ON tags_ft.rowid=tag_rel.tag_id
        WHERE tags_ft.tag match :query
        GROUP BY place_id
        ORDER BY tags_ft.rank
        LIMIT 15
        """
    )
    with Session() as db:
        res = db.execute(stmt, {"query": f"{query_}*"}).all()
    for row in res:
        """
        'loc' in properties dict is for the location, which used match ^roc OR ^county, then split by :.
        I do not know how to implement that into the SQL query, and getting it seperately is also expensive.
        """
        yy = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row[1], row[2]]},
            "properties": {"name": row[3], "pid": row[0], "loc": ""},
        }
        geojson["features"].append(yy)
    return geojson


def condition(row, value) -> BinaryExpression:
    value = urllib.parse.unquote(value)

    if value[:2] == ">=" or value[:2] == "<=" or value[:2] == "<>":
        if value[:2] == ">=":
            return row >= value[2:]

        elif value[:2] == "<=":
            return row <= value[2:]

        elif value[:2] == "<>":
            return row != value[2:]

    elif value[0] == ">" or value[0] == "<" or value[0] == "=":
        if value[0] == ">":
            return row > value[1:]

        elif value[0] == "<":
            return row < value[1:]

        elif value[0] == "=":
            return row == value[1:]
    else:
        return row.like(f"%{value}%")


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
        query_ = query_.where(condition(places.row_id, ID))

    if Name:
        query_ = query_.where(condition(places.name, Name))

    if Status:
        query_ = query_.where(condition(places.status, Status))

    query_ = query_.order_by(places.row_id.desc()).limit(200)
    # sometimes the webpage stops querying properly, never caught it before with below debug
    print(query_)
    with Session() as db:
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
    foo: str | None = None,
) -> list[dict[str, str | bool]]:
    with Session() as db:
        query_ = select(refs)

        if ID:
            query_ = query_.where(condition(refs.row_id, ID))

        if URL:
            query_ = query_.where(condition(refs.url, URL))

        if title:
            query_ = query_.where(condition(refs.title, title))

        if Date:
            query_ = query_.where(condition(refs.date_post, Date))

        if PID:
            # https://docs.sqlalchemy.org/en/20/orm/join_conditions.html#specifying-alternate-join-conditions
            query_ = query_.where(refs.assoc_place.any(condition(places.row_id, PID)))

        query_ = query_.order_by(refs.row_id.desc()).limit(200)

        res = db.scalars(query_).all()

        data = list()
        for row in res:
            pid = ", ".join([str(place.row_id) for place in row.assoc_place])
            data.append(
                {
                    "id": row.row_id,
                    "url": row.url,
                    "title": row.title,
                    "pid": pid,
                    "date": row.date_post,
                }
            )

    return data


app = Litestar(
    route_handlers=[
        index,
        latest,
        get_bounds,
        search,
        search_sites,
        search_refs,
        edit_pid,
    ],
    static_files_config=[StaticFilesConfig(directories=["static"], path="/static")],
    template_config=TemplateConfig(directory=".", engine=JinjaTemplateEngine),
    after_response=after_response,
)
