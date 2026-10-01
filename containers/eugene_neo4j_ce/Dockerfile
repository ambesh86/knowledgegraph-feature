# latest neo4j 6 is not backwards compatible with 5.26
FROM neo4j:5.26.9-community-bullseye

ENV S3_STAGING_BUCKET=aia-scop-experiment-eugene-data

WORKDIR /var/lib/neo4j

# Note: this is a different source file than the py images
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y \
    dnsutils \
    iputils-ping \
    net-tools \
    ca-certificates \
    wget \
    unzip \
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

# install plugings
RUN cp labs/apoc-*-core.jar plugins/.

RUN wget -q \
    --no-cookies \
    https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.26.1/apoc-5.26.1-extended.jar \
    -O downloads/apoc-5.26.1-extended.jar


RUN wget -q \
    --no-cookies \
    https://github.com/neo4j/graph-data-science/releases/download/2.13.4/neo4j-graph-data-science-2.13.4.jar \
    -O downloads/neo4j-graph-data-science.jar

RUN cp downloads/*.jar plugins/.

RUN rm -rf downloads

# install certificates
RUN cd $NEO4J_HOME && cd certificates && \
    mkdir -p bolt && \
    cd bolt && \
    openssl req -x509 \
    -newkey ec \
    -pkeyopt ec_paramgen_curve:secp384r1 \
    -nodes -out public.crt \
    -keyout private.key \
    -days 730 \
    -subj "/C=US/ST=MD/L=Annapolis/O=Digital I&t Enterprise Architecture/CN=Fuze/emailAddress=sterling.foster@cslbehring.com"

# install configuration updates
COPY containers/eugene_neo4j_ce/conf/apoc.conf /var/lib/neo4j/conf/apoc.conf
COPY containers/eugene_neo4j_ce/conf/neo4j.conf /var/lib/neo4j/conf/neo4j.conf

# CMD [ "neo4j" ]

ENTRYPOINT [ "/bin/sh" ]
CMD [ "-c", "while true; do sleep 90; date -Is && ps -ef | grep [m]anaged-agents; date -Is; done" ]
