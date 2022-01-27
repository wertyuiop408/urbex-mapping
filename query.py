import re
import time
import argparse

from db import db


def main() -> None:

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("filter", nargs="?")
    parser.add_argument("--min", type=int)
    args = parser.parse_args()

    #used for if we want to filter the reports that have a certain word. e.g. %hospital%
    filt = ""
    if args.filter:
        filt = f"and lower(title) like '{args.filter}'"

    #find all entries that don't have a PLACE ID and find the most common words (uses split to remove a lot of the unwanted)
    query = f"""
    WITH split(name, rest, lev) AS (
        SELECT
            NULL AS name,
            TRIM(
                LOWER(title),
            '!-().,"`?0123456789 &/')|| ' ' AS rest,
            1 AS lev FROM refs WHERE place_id IS NULL {filt}
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
    """


    #select all reports that have no place ID, show the most common words
    query2 = f"""
    WITH split(name, rest, lev) AS (
        SELECT
            NULL AS name, 
            TRIM(
                REPLACE(
                    LOWER(title),
                'report -', ''),
            ',(') AS rest,
            1 AS lev FROM refs WHERE title LIKE 'Report%' 
        AND place_id IS NULL {filt}

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

    SELECT name, count(name) as tot from split where name <> ''
    GROUP BY name
    ORDER BY tot ASC
    """

    #show the most popular beginning letters of a word from reports, e.g. "sheff"
    query3 = """
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
        FROM refs WHERE place_id IS NULL
        AND title LIKE 'Report -%' AND foo <> ''
        GROUP BY foo
        ORDER By cnt DESC
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