FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /tmp/ide_yonetici \
 && chown -R appuser:appuser /app /tmp/ide_yonetici
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/diagnostic', timeout=3).read()" || exit 1

CMD ["python", "main.py"]
