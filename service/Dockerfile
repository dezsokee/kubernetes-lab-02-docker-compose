FROM python:3.14-slim-trixie AS builder

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN python -m compileall -q -b app && find app -name '*.py' -delete

FROM python:3.14-slim-trixie

ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app

RUN useradd --create-home --uid 1000 app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status==200 else sys.exit(1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
