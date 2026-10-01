FROM ubuntu:latest

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

RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential

# install latest libs and java
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y \
    dnsutils \
    iputils-ping \
    net-tools \
    ca-certificates \
    wget \
    unzip \
    openjdk-17-jdk \
    htop \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p downloads

# install ssm
RUN wget -q \
    --no-cookies \
    https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb \
    -O downloads/amazon-ssm-agent.deb

RUN cd downloads/ && dpkg -i amazon-ssm-agent.deb

# install aws cli
RUN wget -q \
    --no-cookies \
    https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip \
    -O downloads/awscliv2.zip

RUN cd downloads/ && \
    unzip awscliv2.zip && \
    ./aws/install

# install cypher shell
RUN wget -q \
    --no-cookies \
    https://dist.neo4j.org/cypher-shell/cypher-shell_5.26.9_all.deb \
    -O downloads/cypher-shell.deb

RUN cd downloads/ && dpkg -i cypher-shell.deb

# cleanup
RUN rm -rf downloads

CMD ["/bin/sh", "-c", "while true; do sleep 90; done"]