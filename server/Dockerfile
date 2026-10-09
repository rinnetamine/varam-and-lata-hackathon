FROM python:3.12-alpine

WORKDIR /app
COPY seed_people.py app.py benefits.py vsaa.py ./

ENV HOST=0.0.0.0 PORT=8000 DB_PATH=/data/people.db
VOLUME /data
EXPOSE 8000

CMD ["python3", "app.py"]
