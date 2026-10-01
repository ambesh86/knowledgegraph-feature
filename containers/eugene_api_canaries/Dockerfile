FROM python:3.12-slim

WORKDIR /app

# ignore prompts for tzdata package
ENV DEBIAN_FRONTEND=noninteractive 

# set timezone for tzdata package
RUN ln -snf /usr/share/zoneinfo/$CONTAINER_TIMEZONE /etc/localtime && echo $CONTAINER_TIMEZONE > /etc/timezone

# ubuntu uses http for the package mirrors by default
# switch to https
# RUN cd /etc/apt/sources.list.d && \
#    sed --in-place --regexp-extended 's http https g' ubuntu.sources
# RUN cd /etc/apt && \
#     echo "set no_check_certificate 1" >> mirror.list

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

# source files
COPY api-canaries/requirements.txt /app

RUN mkdir -p /app/src

COPY api-canaries/src /app/src


# run time container
RUN useradd -ms /bin/sh eugene
ENV HOME=/home/eugene
RUN chown -R eugene:eugene /app && chown -R eugene:eugene /home/eugene

RUN chown -R eugene:eugene /home/eugene

USER eugene

CMD ["python", "src/canary_cli.py", "--difflabs", "--env", "staging"]