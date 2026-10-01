FROM python:3.13-slim

WORKDIR /app

# Trust the corporate TLS-inspection root CA (e.g. Zscaler) so pip/apt can
# reach hosts that aren't on the proxy's SSL-bypass list (download.pytorch.org).
# No-op outside that network: update-ca-certificates just adds one more CA.
COPY docker/certs/zscaler-root-ca.crt /usr/local/share/ca-certificates/zscaler-root-ca.crt

# libGL/libglib are required by OpenCV (pulled in by doclayout-yolo). Without
# them `import cv2` fails at runtime with a bare linker error.
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN pip install --upgrade pip

# CPU-only PyTorch first — the default wheel drags in ~4.5GB of NVIDIA CUDA
# libraries this service will never use.
RUN pip install --no-cache-dir torch==2.7.0 torchvision==0.22.0 \
    --index-url https://download.pytorch.org/whl/cpu

COPY agents/eugene-ade/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY agents/eugene-ade/src /app/src

# Create the model-cache mount point IN THE IMAGE and own it as the runtime user.
# A named volume inherits the image path's ownership; if the directory only
# appears at mount time it is created root-owned and the uid-1000 process cannot
# write the downloaded weights.
RUN useradd -ms /bin/sh eugene \
    && mkdir -p /app/.hf_cache \
    && chown -R eugene:eugene /app

ENV HOME=/home/eugene \
    HF_HOME=/app/.hf_cache \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

USER eugene

EXPOSE 8000

CMD ["uvicorn", "ade.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
