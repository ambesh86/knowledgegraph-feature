FROM python:3.12-slim

WORKDIR /app

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y \
    build-essential \
    ca-certificates \
    wget \
    unzip \
    htop \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# source files
COPY api-canaries/requirements.txt /app

RUN mkdir -p /app/src

COPY api-canaries/src /app/src

RUN pip config set global.trusted-host \
    "pypi.org files.pythonhosted.org pypi.python.org" \
    --trusted-host=pypi.python.org \
    --trusted-host=pypi.org \
    --trusted-host=files.pythonhosted.org

RUN pip install \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    --no-cache-dir -r requirements.txt


# run time container
RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN chown -R eugene:eugene /app && chown -R eugene:eugene /home/eugene

RUN chown -R eugene:eugene /home/eugene

USER eugene

CMD ["python", "src/canary_cli.py", "--difflabs", "--env", "staging"]