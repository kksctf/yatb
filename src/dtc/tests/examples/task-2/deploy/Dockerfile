FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY src src

ENTRYPOINT [ "uvicorn", "src:app" ]
CMD [ "--host=0.0.0.0", "--port=80" ]
