FROM klotio/nginx:0.1

COPY etc/kubernetes.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /opt/service

WORKDIR /opt/service

ADD www www
