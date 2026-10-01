FROM python:3.13-slim

WORKDIR /app

# Trust the corporate TLS-inspection root CA (e.g. Zscaler) so pip/apt can
# reach hosts that aren't on the proxy's SSL-bypass list.
# No-op outside that network: update-ca-certificates just adds one more CA.
COPY docker/certs/zscaler-root-ca.crt /usr/local/share/ca-certificates/zscaler-root-ca.crt
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends build-essential ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN pip install --upgrade pip

COPY agents/eugene-scout/requirements.txt /app/
# No torch, no models, no Neo4j driver: this service only speaks HTTP to four public
# APIs and S3. Keeping it that way is what makes the image small and its restarts
# cheap enough that a redeploy never delays a scheduled scan.
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/eugene-scout/src /app/src
COPY agents/eugene-scout/tests /app/tests
COPY agents/eugene-scout/pyproject.toml /app/

# The research-area taxonomy is OWNED by the ingestion pipeline
# (ingestion/src/pipeline/config/research_areas.yaml) and copied here at build time
# rather than retyped. scout/areas.py looks for it at this path first. A second
# hand-maintained copy of the CSL franchise list is exactly the thing that would
# silently drift and then mis-scope an entire therapeutic area's scan.
COPY ingestion/src/pipeline/config/research_areas.yaml /app/config/research_areas.yaml

RUN useradd -ms /bin/sh eugene && chown -R eugene:eugene /app

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    SCOUT_AREAS_CONFIG=/app/config/research_areas.yaml

USER eugene

EXPOSE 8000

CMD ["uvicorn", "scout.api:app", "--host", "0.0.0.0", "--port", "8000"]
