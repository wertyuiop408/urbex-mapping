#tags.py
from geopy.geocoders import Nominatim

from db import db

def main() -> None:
    db.connect()
    add_addresses_all()

    return

def add_tag(place_id, tag):
    db.get_cur().execute("INSERT OR IGNORE INTO tags VALUES (null, ?)", [tag])
    db.get_cur().execute("INSERT OR IGNORE INTO tag_rel SELECT ?, row_id FROM tags WHERE tag is ?", [place_id, tag])
    return

def add_address_tag(place_id, lat, lng):
    geolocator = Nominatim(user_agent="ux-map")
    location = geolocator.reverse(f"{lat}, {lng}")

    db.get_cur().execute("BEGIN")
    for x in location.raw['address']:
        data = f"{x}:{location.raw['address'][x]}"
        add_tag(place_id, data)
    db.get_cur().execute("COMMIT")


def add_addresses_all():
    db.get_cur().execute("SELECT row_id, lat, long FROM places")
    for place in db.get_cur().fetchall():
        add_address_tag(place["row_id"], place["lat"], place["long"])
    return
"""
select places.name, tag_rel.tag_id, tags.tag from places 
left join tag_rel on places.row_id=tag_rel.place_id
left join tags on tag_rel.tag_id=tags.row_id
where places.row_id = 296 



select places.*,tags.tag from tags 
LEFT JOIN tag_rel ON tags.row_id=tag_rel.tag_id
LEFT JOIN places ON tag_rel.place_id=places.row_id
WHERE tags.tag LIKE "%Royal%"
""" 

if __name__ == "__main__":
    main()