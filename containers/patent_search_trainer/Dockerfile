# Note: python 3.12 is needed to install the graspologic library, 3.13 does not work
FROM python:3.12-slim

WORKDIR /app

ENV S3_STAGING_BUCKET=aia-scop-experiment-eugene-data

RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential

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

RUN mkdir -p downloads

# install aws cli
RUN wget -q \
    --no-cookies \
    https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip \
    -O downloads/awscliv2.zip

RUN cd downloads/ && \
    unzip awscliv2.zip && \
    ./aws/install

RUN rm -rf downloads/

COPY containers/patent_search_trainer/bin/entrypoint.sh /app

RUN chmod 770 /app/entrypoint.sh

RUN mkdir -p /app/src

COPY src /app/src

COPY requirements.txt /app

# Note: python 3.12 is needed to install the graspologic library, 3.13 does not work
RUN pip install --no-cache-dir -r requirements.txt

# run time container
RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN chown -R eugene:eugene /app && chown -R eugene:eugene /home/eugene
USER eugene

ENTRYPOINT [ "/app/entrypoint.sh" ]