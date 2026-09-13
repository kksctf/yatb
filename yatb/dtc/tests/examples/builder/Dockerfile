FROM rubikoid/yatb-k8s-builder-base:latest

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "/app/build.py" ]
