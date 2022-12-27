### USAGE:
# Run python scrape.py from the same folder that has the `out` directory, with the first argument
# being the semester to scrape in YYYYT format (with T being a term, 1-5) and then a Postgres connection
# string, e.g.:
#
# python scrape.py 20224 postgresql://localhost:5342/byu
#
# Note that the terms are a bit odd. It seems to be:
# Winter: 1
# Spring: 3
# Summer: 4
# Fall: 5
#
# Just check the requests in the web app.
import os
import re
import sys
import time

from bs4 import BeautifulSoup
import psycopg2
import requests


COLUMNS = {
    "course": 0,
    "class_period": 7,
    "days": 8,
}

TIME_FORMAT = "%I:%M%p"

YEAR_TERM = sys.argv[1]


def open_or_download_file(filename, fetch_fn):
    try:
        with open(f"out/{YEAR_TERM}/{filename}", "r") as fh:
            html = fh.read()
    except FileNotFoundError:
        html = fetch_fn()
        with open(f"out/{YEAR_TERM}/{filename}", "w") as fh:
            print(html, file=fh)
        time.sleep(0.1)  # to avoid overwhelming the server
    return html


def get_class_info(row):
    start, end = (
        row.find_all("td")[COLUMNS["class_period"]]
        .text.strip()
        .replace("a", "am")
        .replace("p", "pm")
        .split(" - ")
    )
    start = time.strptime(start, TIME_FORMAT)
    end = time.strptime(end, TIME_FORMAT)
    days = row.find_all("td")[COLUMNS["days"]].text.strip()
    return {
        "name": row.find_all("td")[COLUMNS["course"]].text.strip(),
        "start": start,
        "end": end,
        # TODO: There is a "Daily" value that appears in the days field
        "days": ["M", "T", "W", "Th", "F"]
        if days == "Daily"
        else re.findall(r"(Th|Sa|Su|M|T|W|F)", days),
    }


def get_room_info(building, room):
    html = open_or_download_file(
        f"{building}-{room}.html",
        lambda: requests.post(
            "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
            data={
                "year_term": YEAR_TERM,
                "building": building,
                "room": room,
            },
        ).text,
    )
    result = {}
    soup = BeautifulSoup(html, "html.parser")
    result["description"] = soup.find("input", attrs={"name": "room_desc"})["value"]
    result["capacity"] = int(soup.find("input", attrs={"name": "capacity"})["value"])
    result["classes"] = []
    schedule_table = soup.find("th", string=re.compile("Instructor"))  # .parent.parent
    if schedule_table:
        schedule_table = schedule_table.parent.parent
        for row in schedule_table.find_all("tr")[1:]:
            result["classes"].append(get_class_info(row))
    return result


def get_buildings_rooms(buildings):
    for building in buildings:
        html = open_or_download_file(
            f"{building}-list.html",
            lambda: requests.post(
                "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
                data={
                    "e": "@loadRooms",
                    "year_term": YEAR_TERM,
                    "building": building,
                },
            ).text,
        )
        soup = BeautifulSoup(html, "html.parser")
        yield (building, [tag.text for tag in soup.find("table").find_all("a")])


def main():
    try:
        os.mkdir(f"out/{YEAR_TERM}")
    except FileExistsError:
        print("Folder exists.")
    # TODO: env variables
    conn = psycopg2.connect(sys.argv[2])
    cur = conn.cursor()
    cur.execute("TRUNCATE buildings CASCADE")
    index = open_or_download_file(
        "classRoom2.cgi",
        lambda: requests.post(
            "https://y.byu.edu/class_schedule/cgi/classRoom2.cgi",
            data={ "year_term": YEAR_TERM, },
        ).text
    )

    soup = BeautifulSoup(index, "html.parser")
    buildings = [
        tag["value"]
        for tag in soup.find("select", attrs={"name": "Building"}).find_all(
            "option"
        )
    ]

    classes = 0
    for building, rooms in get_buildings_rooms(buildings):
        print(building)
        cur.execute(
            "INSERT INTO buildings (name) VALUES (%s) RETURNING id", (building,)
        )
        building_id = cur.fetchone()[0]
        for room in rooms:
            room_info = get_room_info(building, room)
            cur.execute(
                "INSERT INTO rooms (building_id, number, description) VALUES (%s, %s, %s) RETURNING id",
                (building_id, room, room_info["description"]),
            )
            room_id = cur.fetchone()[0]
            for class_ in room_info["classes"]:
                print(f"    {classes:04}: {class_['name']}")
                classes += 1
                # TODO: How do we deal with time zones? Might be best to not store them and simply
                # look up the current time in mountain time to query a "now" value?
                cur.execute(
                    """INSERT INTO events (room_id, name, days, start_time, end_time)
                       VALUES (%s, %s, %s::weekday[], %s, %s)""",
                    (
                        room_id,
                        class_["name"],
                        class_["days"],
                        time.strftime("%H:%M:00 MST", class_["start"]),
                        time.strftime("%H:%M:00 MST", class_["end"]),
                    ),
                )
            conn.commit()


if __name__ == "__main__":
    main()
