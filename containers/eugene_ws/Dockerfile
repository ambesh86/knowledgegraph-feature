FROM python:3.13-slim

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

COPY containers/eugene_ws/requirements.txt /app
COPY containers/eugene_ws/bin/entrypoint.sh /app

RUN chmod 770 /app/entrypoint.sh

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/src
COPY src /app/src

# run time container
RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN chown -R eugene:eugene /app && chown -R eugene:eugene /home/eugene

# install s3 staging files
# install huggyface models, the network does not have access to download at runtime
RUN mkdir -p /home/eugene/.cache/huggingface/hub/minishlab
# RUN cd /home/eugene/.cache/huggingface/hub \
#     && aws s3 cp s3://$S3_STAGING_BUCKET/build/minishlab.zip . \
#     && unzip minishlab.zip \
#     && rm -rf minishlab.zip

# COPY ./tmp/models/minishlab /home/eugene/.cache/huggingface/hub/minishlab
RUN chown -R eugene:eugene /home/eugene

USER eugene

EXPOSE 8000

ENTRYPOINT [ "/app/entrypoint.sh" ]