# latest neo4j 6 is not backwards compatible with 5.26
FROM neo4j:5.26.9-community-bullseye

WORKDIR /var/lib/neo4j

# install latest libs
RUN apt-get \
    update -y \
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
    --no-check-certificate \
    https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb \
    -O downloads/amazon-ssm-agent.deb

RUN cd downloads/ && dpkg -i amazon-ssm-agent.deb

# install aws cli
RUN wget -q \
    --no-cookies \
    --no-check-certificate https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip \
    -O downloads/awscliv2.zip

RUN cd downloads/ && \
    unzip awscliv2.zip && \
    ./aws/install

# install plugings
RUN cp labs/apoc-*-core.jar plugins/.

RUN wget -q \
    --no-cookies \
    --no-check-certificate \
    https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.26.1/apoc-5.26.1-extended.jar \
    -O downloads/apoc-5.26.1-extended.jar

RUN wget -q \
    --no-cookies \
    --no-check-certificate \
    --no-check-certificate https://github.com/neo4j/graph-data-science/releases/download/2.13.4/neo4j-graph-data-science-2.13.4.jar \
    -O downloads/neo4j-graph-data-science-2.13.4.zip

RUN cd downloads/ && unzip neo4j-graph-data-science-2.13.4.zip && cd ..

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
COPY difflabs/containers/eugene_neo4j_ce/conf/apoc.conf /var/lib/neo4j/conf/apoc.conf
COPY difflabs/containers/eugene_neo4j_ce/conf/neo4j.conf /var/lib/neo4j/conf/neo4j.conf

# ENTRYPOINT ["/startup/docker-entrypoint.sh" ]
# CMD [ "neo4j" ]

ENTRYPOINT [ "/bin/sh" ]
CMD [ "-c", "while true; do sleep 90; date -Is && ps -ef | grep [m]anaged-agents; date -Is; done" ]
