FROM python:3.7

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /app

COPY . .

CMD ["python", "confluence2notion.py"]
