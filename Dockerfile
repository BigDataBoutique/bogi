FROM python:3-alpine
RUN apk add --no-cache tzdata
RUN ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime

WORKDIR /usr/src/app
CMD python3 ./bogi.py ./requests/

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
