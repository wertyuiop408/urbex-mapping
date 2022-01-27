import re
import time
import argparse

from db import db


def main() -> None:

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("filter", nargs="?")
    parser.add_argument("--min", type=int)
    args = parser.parse_args()


    filt = ""
    if args.filter:
        filt = f"and lower(title) like '{args.filter}'"

    query = f"""
    with split(name, rest, lev) as (
        select NULL as name, trim(lower(title), '!-().,"`?0123456789 &/')|| ' ' as rest, 1 as lev from refs where place_id is NULL {filt}
        union all
        select trim(lower(substr(rest, 1, instr(rest, ' '))), '!-().,"`?0123456789 &/'),
                 substr(rest, instr(rest, ' ') + 1),
                 lev + 1
        from split where rest <> '' and lev < 10
    )
    select name, count(name) as tot from split where name <> ''
    group by name
    order by tot desc
    limit 200
    """

    query2 = f"""
    WITH split(name, rest, lev) AS (
        SELECT NULL AS name, TRIM(REPLACE(LOWER(title), 'report -', ''), ',(') AS rest, 1 AS lev FROM refs WHERE title LIKE 'Report%' 
        AND place_id IS NULL {filt}
        UNION ALL
        SELECT TRIM(
            REPLACE(LOWER(
                substr(rest, 1, instr(rest, ' '))
            ), 'report -', '')
        , ',() /-&'),
                 substr(rest, instr(rest, ' ') + 1),
                 lev + 1
        FROM split WHERE rest <> '' AND lev < 10
    )
    SELECT name, count(name) as tot from split where name <> ''
    GROUP BY name
    ORDER BY tot asc
    """

    #replacing all of these in SQL is not pretty
    word_list = [
        "on",
        "to",
        "the",
        "of",
        "and",
        "in",
        "or",
        "lead",
        "a",
        "for",
        "rumour",
        "'",
        "-",
        "question",
        "report",
        "january",
        "jan",
        "february",
        "feb",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "aug",
        "september",
        "sept",
        "october",
        "oct",
        "november",
        "nov",
        "december",
        "\nabandoned"
    ]

    start = time.perf_counter()

    for x in db.get_cur().execute(query2):
        if args.min and x["tot"] < args.min:
            continue

        name = re.sub(r"\s+", "", x["name"])        
        if name not in word_list:
            print(x["tot"], name)


    end = time.perf_counter()
    ms = int(round((end-start) * 1000))
    print(f"{ms} ms")
    return


if __name__ == "__main__":
    main()