FROM alpine:3.21

WORKDIR /app

RUN apk add iproute2 iputils-ping iptables bash

ENTRYPOINT [ "bash" ]
CMD ["-c", "sleep 10000000"]
