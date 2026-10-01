#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\docker\eugene_agent_ws
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

COPY agents/eugene-agent-ws/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install the optional Anthropic SDK for explicitly configured provider/fallback use.
RUN pip install --no-cache-dir anthropic

# Stage 1 hardening extras: rate limiting, structured logging
RUN pip install --no-cache-dir \
    "slowapi==0.1.9" \
    "python-json-logger==2.0.7"

COPY agents/eugene-agent-ws/src /app/src

RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN mkdir -p /home/eugene/.strands \
    && chown -R eugene:eugene /app /home/eugene

USER eugene

EXPOSE 8000

CMD ["uvicorn", "eugene_chat_ws:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
