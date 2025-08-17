FROM alpine:3.21

RUN apk --no-cache --no-progress upgrade && \
    apk --no-cache --no-progress add bash curl ip6tables iptables openvpn \
                shadow tini tzdata tcpdump && \
    addgroup -S vpn && \
    rm -rf /tmp/*

COPY ./fw.sh /fw.sh

ENTRYPOINT ["/usr/bin/openvpn", "--script-security=2", "--up=/fw.sh"]
