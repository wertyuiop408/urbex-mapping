import re
import time
import argparse

from db import db


def main() -> None:

    db.connect()
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("-q", type=int, default=1)
    parser.add_argument("filter", nargs="?")
    parser.add_argument("--min", type=int, default=0)
    args = parser.parse_args()

    #used for if we want to filter the reports that have a certain word. e.g. %hospital%
    filt = ""
    if args.filter:
        filt = f"and lower(title) like '{args.filter}'"

    query_list = list()

    #find all entries that don't have a PLACE ID and find the most common words (uses split to remove a lot of the unwanted)
    #q 0
    query_list.append(f"""
    WITH split(name, rest, lev) AS (
        SELECT
            NULL AS name,
            TRIM(
                LOWER(title),
            '!-().,"`?0123456789 &/')|| ' ' AS rest,
            1 AS lev FROM refs WHERE place_id IS 0 {filt}
        UNION ALL
        SELECT
            TRIM(
                LOWER(
                    substr(rest, 1, instr(rest, ' '))
                ),
            '!-().,"`?0123456789 &/'),
            substr(rest, instr(rest, ' ') + 1),
            lev + 1
        FROM split WHERE rest <> '' AND lev < 10
    )
    SELECT name, count(name) AS tot FROM split WHERE name <> ''
    GROUP BY name
    ORDER BY tot DESC
    LIMIT 200
    """)


    #select all reports that have no place ID, show the most common words
    #q 1
    query_list.append(f"""
    WITH split(name, rest, lev) AS (
        SELECT
            NULL AS name, 
            TRIM(
                REPLACE(
                    LOWER(title),
                'report -', ''),
            ',(') AS rest,
            1 AS lev FROM refs WHERE title LIKE 'Report%' 
        AND place_id IS 0 {filt}

        UNION ALL
        SELECT 
            TRIM(
                REPLACE(
                    LOWER(
                        substr(rest, 1, instr(rest, ' '))
                    ),
                'report -', ''),
            ',() /-&'),

            substr(rest, instr(rest, ' ') + 1),
            lev + 1
        FROM split WHERE rest <> '' AND lev < 10
    )

    SELECT name, count(name) AS tot FROM split WHERE name <> ''
    GROUP BY name HAVING tot > ?
    ORDER BY tot ASC
    """)

    #show the most popular beginning letters of a word from reports, e.g. "sheff"
    #q 2
    query_list.append("""
    SELECT
        SUBSTR(
            TRIM(
                SUBSTR(
                    RTRIM(title, 
                        REPLACE(title, '-', '')
                    ),/*neat trick. Remove a character and use r/l/trim to filter everything up to that point. we using it to remove everything after the last '-'*/
                10),/* grab part of title after 'Report -' */
            '- '),
        0, 5) as foo, /* grab the first 5 characters*/
        count(*) as cnt 
        FROM refs WHERE place_id IS 0
        AND title LIKE 'Report -%' AND foo <> ''
        GROUP BY foo HAVING cnt > ?
        ORDER By cnt DESC
    """)

    #select the most popular first word after x, e.g after report - 
    #q3
    query_list.append("""
    SELECT
        LOWER(
            TRIM(
                SUBSTR(title, 14,
                    INSTR(
                        SUBSTR(title, 14) /*14 is the length of 'report -_raf '*/
                    , ' ')
                ), ' ,-' /*remove unwanted chars from edges of the word*/
            )
        ) AS name,
        COUNT(*) as tot
    FROM refs
    WHERE title like 'report -_raf %' and place_id = 0 and name <> ''
    GROUP BY name having tot > ?
    ORDER BY tot ASC
    """)

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
    xx = (query_list[args.q], [args.min])

    for x in db.get_cur().execute(*xx):

        name = re.sub(r"\s+", "", x["name"])        
        if name not in word_list:
            print(x["tot"], name)


    end = time.perf_counter()
    ms = int(round((end-start) * 1000))
    print(f"{ms} ms")
    return


if __name__ == "__main__":
    main()