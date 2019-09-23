FROM python:3

RUN mkdir /usr/spyboy/

WORKDIR /usr/spyboy/

COPY *.py ./
COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python", "./app.py"]
