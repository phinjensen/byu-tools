from datetime import datetime

from flask.templating import render_template
from flask import Flask, request
from peewee import SQL
from pytz import timezone

from models import Buildings, Events, Rooms, database

app = Flask(__name__)

DAY_MAP = {
    'Mon': 'M',
    'Tue': 'T',
    'Wed': 'W',
    'Thu': 'Th',
    'Fri': 'F',
    'Sat': 'Sa',
    'Sun': 'Su',
}

# TODO: make this dynamic for earliest/latest hours
TIMES = [f"{h % 12 or 12}:{m:02} {'AM' if h < 12 else 'PM'}" for h in range(6, 23) for m in range(0, 60, 15) ]

UTAH_TIMEZONE = timezone('US/Mountain')

@app.route('/')
def lookup():
    database.connect()
    result = []
    buildings = Buildings.select()
    show_results = 'none'
    if all(key in request.args for key in ['building', 'timeType']):
        result = Rooms.select(Rooms, Buildings) \
            .join(Buildings) \
            .where(Rooms.description == 'CLASSROOM')

        building_name = request.args.get('building', '')
        if building_name != '_any':
            building = Buildings.get(Buildings.name == building_name)
            result = result.where(Rooms.building == building)

        conflicting_events = Events.select()
        days = request.args.getlist("days")

        if request.args.get('timeType') == 'now':
            now = datetime.now(UTAH_TIMEZONE).time()
            day = DAY_MAP[now.strftime('%a')]
            conflicting_events = conflicting_events \
                .where(Events.days.contains(day)) \
                .where(
                    (Events.start_time <= now) & (Events.end_time > now)
                )
        elif request.args.get('timeType') == 'at':
            if 'timeAt' not in request.args:
                raise Exception("time required with timeType=at")
            time = request.args.get('timeAt')
            conflicting_events = conflicting_events \
                .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
                .where(
                    (Events.start_time <= time) & (Events.end_time > time)
                )
        else:
            if 'timeFrom' not in request.args or 'timeTo' not in request.args:
                raise Exception("from and to times required for time range")
            conflicting_events = conflicting_events \
                .where(SQL("days && ARRAY[%s]::weekday[]" % days)) \
                .where(
                    SQL(
                        "timerange(start_time::time, end_time::time, '()') && timerange('%s'::time, '%s'::time)" %
                        (request.args.get('timeFrom'), request.args.get('timeTo'))
                    )
                )

        result = result \
                .where(Rooms.id.not_in([*map(lambda x: x.room_id, conflicting_events)])) \
                .order_by(Buildings.name, Rooms.number)

        show_results = 'no_results' if len(result) == 0 else 'all'

    render = render_template(
        'index.html',
        show_results=show_results,
        result=result,
        buildings=buildings,
        times=TIMES
    )

    database.close()

    return render
