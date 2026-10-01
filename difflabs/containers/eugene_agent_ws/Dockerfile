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

COPY difflabs/containers/eugene_agent_ws/requirements.txt /app
COPY difflabs/containers/eugene_agent_ws/bin/entrypoint.sh /app

RUN chmod 770 /app/entrypoint.sh

RUN pip install --upgrade pip

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

# source files
RUN mkdir -p /app/src
COPY agents/eugene-agent-ws/src /app/src

# run time container
RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN chown -R eugene:eugene /app && chown -R eugene:eugene /home/eugene

RUN chown -R eugene:eugene /home/eugene

USER eugene

EXPOSE 8000

ENTRYPOINT [ "/app/entrypoint.sh" ]
