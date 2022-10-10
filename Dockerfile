FROM python:3.10-alpine

RUN apk add build-base postgresql-dev

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT ["gunicorn", "rooms:app"]
