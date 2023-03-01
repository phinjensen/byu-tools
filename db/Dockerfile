FROM postgres:15

ENV POSTGRES_DB byu_tools
ENV POSTGRES_PASSWORD example

COPY dump.sql /docker-entrypoint-initdb.d/dump.sql
