ARG BASE
FROM ${BASE}

COPY etc/kubernetes.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /opt/nandy-io

WORKDIR /opt/nandy-io

ADD www www
