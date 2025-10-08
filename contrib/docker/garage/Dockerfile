FROM dxflrs/garage:v2.1.0 as garage

FROM debian:stable-slim

ENV RUST_BACKTRACE=1
ENV RUST_LOG=garage=info

COPY --from=garage /garage /garage

COPY ./run.sh /run.sh
RUN chmod +x /run.sh

ENTRYPOINT ["/run.sh"]
