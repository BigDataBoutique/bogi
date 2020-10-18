FROM python:3-alpine

WORKDIR /usr/src/app
CMD python3 ./bogi.py ./requests/

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
