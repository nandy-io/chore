FROM resin/raspberry-pi-alpine-python:3.6.1

RUN apk add git

COPY entry.sh /usr/bin/entry.sh

RUN mkdir -p /opt/service

WORKDIR /opt/service

ADD requirements.txt .

RUN pip install -r requirements.txt

ADD bin bin
ADD lib lib
ADD test test

ENV PYTHONPATH "/opt/service/lib:${PYTHONPATH}"

CMD "/opt/service/bin/daemon.py"
