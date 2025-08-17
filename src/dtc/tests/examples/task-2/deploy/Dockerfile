# syntax=docker/dockerfile:1.4
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /python-docker

RUN pip3 install flask

COPY . .

CMD [ "python3", "main.py"]