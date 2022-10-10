BEGIN;

DROP TABLE IF EXISTS buildings CASCADE;

-- TODO: This could probably just use name for the primary key?
CREATE TABLE buildings (
  id    serial PRIMARY KEY,
  name  varchar(32) NOT NULL
);


DROP TABLE IF EXISTS rooms CASCADE;

CREATE TABLE rooms (
  id          serial PRIMARY KEY,
  building_id integer NOT NULL REFERENCES buildings(id)
              ON DELETE CASCADE ON UPDATE CASCADE,
  number      varchar(16) NOT NULL,
  description varchar(32) NOT NULL
);

DROP TYPE IF EXISTS weekday CASCADE;

CREATE TYPE weekday AS ENUM (
  'M',
  'T',
  'W',
  'Th',
  'F',
  'Sa',
  'Su'
);


DROP TABLE IF EXISTS events;

-- Alternatively, this could be represented as a classes table that is
-- referenced by multiple class periods, where classroom and start/end times
-- are contained in the class period table.
CREATE TABLE events (
  id          serial PRIMARY KEY,
  room_id     integer NOT NULL REFERENCES rooms(id)
              ON DELETE CASCADE ON UPDATE CASCADE,
  name        varchar(32) NOT NULL,
  days        weekday[] NOT NULL,
  start_time  time NOT NULL,
  end_time    time NOT NULL
);

CREATE OR REPLACE FUNCTION time_subtype_diff(x time, y time) RETURNS float8 AS
'SELECT EXTRACT(EPOCH FROM (x - y))' LANGUAGE sql STRICT IMMUTABLE;

DROP TYPE IF EXISTS timerange CASCADE;

CREATE TYPE timerange AS RANGE (
    subtype = time,
    subtype_diff = time_subtype_diff
);

COMMIT;
