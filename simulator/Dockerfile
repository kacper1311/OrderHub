FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# -u: logi bez buforowania, od razu widoczne w docker compose logs
CMD ["python", "-u", "main.py"]
