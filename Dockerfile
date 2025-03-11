FROM python:3.12-slim

LABEL org.opencontainers.image.title="Barda Portal"
LABEL org.opencontainers.image.description="A web portal for connecting to external services"
LABEL org.opencontainers.image.vendor="Barda"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"] 