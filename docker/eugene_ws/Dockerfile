FROM python:3.13-slim

WORKDIR /app

# Trust the corporate TLS-inspection root CA (e.g. Zscaler) so pip/apt can
# reach hosts that aren't on the proxy's SSL-bypass list (download.pytorch.org).
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

# Install CPU-only PyTorch first (skips ~4.5GB of NVIDIA/CUDA dependencies).
# Pinned to the app's tested version so the build is reproducible.
RUN pip install --no-cache-dir torch==2.7.0 --index-url https://download.pytorch.org/whl/cpu

COPY containers/eugene_ws/requirements.txt /app/
# Install remaining deps. The CPU PyTorch index is added as an extra source so
# that if anything transitively resolves torch it resolves the CPU wheel (no
# ~4.5GB of nvidia-*-cu12 CUDA libraries). torch is already installed above and
# is intentionally NOT pinned in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Stage 1 hardening extras: rate limiting, structured logging
RUN pip install --no-cache-dir \
    "slowapi==0.1.9" \
    "python-json-logger==2.0.7"

COPY src /app/src

RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
# Create the volume mount points IN THE IMAGE and own them as `eugene`. Docker
# initializes a named volume from the image path's contents *and ownership*; if
# these directories only spring into existence at mount time they are created
# root-owned and the uid-1000 process cannot write them — which is what silently
# broke milvus-lite (PermissionError on its .lock file) and the HF model cache.
RUN mkdir -p /home/eugene/.cache/huggingface/hub /app/.db /app/.hf_cache \
    && chown -R eugene:eugene /app /home/eugene

USER eugene

EXPOSE 8000

CMD ["uvicorn", "eugene_ws:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
