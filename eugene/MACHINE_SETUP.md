# Installing Neo4j

This document contains steps used to setup neo4j

# Setup


## Mount data EBS volume in /mnt/data

```
sudo ebsnvme-id /dev/nvme1n1 -u
lsblk

sudo file -s /dev/nvme1n1
Look for “data” as it shows empty

sudo mkfs -t xfs /dev/nvme1n1

sudo mkdir -p /mnt/data

sudo chown ec2-user /mnt/data/

blkid

sudo mount /dev/nvme1n1 /mnt/data -t xfs

/dev/nvme1n1p1 /mnt/data xfs discard,defaults,nofail 0 2
```

## Install Java

```
sudo yum install htop
sudo yum install java-21-amazon-corretto-headless
```

## Install new neo4j

```
rpm --import https://debian.neo4j.com/neotechnology.gpg.key
cat << EOF >  /etc/yum.repos.d/neo4j.repo
[neo4j]
name=Neo4j RPM Repository
baseurl=https://yum.neo4j.com/stable/5
enabled=1
gpgcheck=1
EOF

yum update

sudo yum search neo4j-*
```

Update neo4j.conf to use 50% ram from machine

```
sudo systemctl restart neo4j.service

systemctl status neo4j.service

tail -f /var/log/neo4j/neo4j.log 
```

## Setup Database Password

log into the shell the first time to change the root password

```
[ec2-user@ip-10-88-203-251 ~]$ cypher-shell -a neo4j+ssc://localhost:7687 -u neo4j 
<change password> 
Connected to Neo4j using Bolt protocol version 5.7 at neo4j+ssc://localhost:7687 as user neo4j.
Type :help for a list of available commands or :exit to exit the shell.
Note that Cypher queries must end with a semicolon.
neo4j@neo4j> show databases;
```

## Install neo4j plugins


https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/

apoc extended  - https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases?q=5.26&expanded=true

Move over apoc core from /var/lib/neo4j/labs/ to /var/lib/neo4j/plugins

Download apoc extended

```
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.25.0/apoc-5.25.0-extended.jar

sudo cp apoc-5.25.0-extended.jar /var/lib/neo4j/plugins/.
```

Download GDS
And gds - https://neo4j.com/docs/graph-data-science/current/installation/neo4j-server/

```
wget https://graphdatascience.ninja/neo4j-graph-data-science-2.13.2.zip
unzip neo4j-graph-data-science-2.13.2.zip

sudo cp downloads/neo4j-graph-data-science-2.13.2.jar /var/lib/neo4j/plugins/.
```

Install to plugins dir, enable the pluging in neo4j.conf
```
apoc.conf:apoc import file.enabled=true
apoc.conf:apoc.import.file.use_neo4j_config=true

neo4j.conf:dbms.security.procedures.unrestricted=apoc.meta.stats,gds.util.asNode,gds.beta.pipeline.linkPrediction.*
neo4j.conf:dbms.security.procedures.allowlist=apoc.help.*,apoc.map.*,apoc.coll.*,apoc.load.*,apoc.create.*,apoc.periodic.*,apoc.meta.*,gds.*
```

```
sudo systemctl restart neo4j.service

systemctl status neo4j.service

tail -f /var/log/neo4j/neo4j.log 
```


## Enable neo4j TLS

Enable TLS
https://neo4j.com/docs/upgrade-migration-guide/current/version-4/migration/drivers/ssl-bolt-https/

https://neo4j.com/docs/operations-manual/current/security/ssl-framework/
```
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:secp384r1 -nodes -out public.crt -keyout private.key -days 365 -subj "/C=US/ST=MD/L=Annapolis/O=Diffusion Labs/CN=Fuze/emailAddress=sterling.foster@cslbehring.com"

mkdir -p and install in /var/lib/neo4j/certificates/bolt
```

Update neo4j.conf per docs

```
sudo systemctl restart neo4j.service

systemctl status neo4j.service

tail -f /var/log/neo4j/neo4j.log 
```

Cypher shell will use self signed certs now
`cypher-shell -a neo4j+ssc://10.xx.xxx.xxx:7687 -u neo4j -p`

Neo4j desktop still does not use ssc for me


## Improve Vector Index

See, https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/

Uncomment this line in neo4j.conf

```
server.jvm.additional=--add-modules=jdk.incubator.vector
```


## Remove PhoneHome

Uncomment [reporting](https://neo4j.com/docs/operations-manual/current/configuration/configuration-settings/#config_dbms.usage_report.enabled) in `neo4j.conf`

```
# Anonymous usage data reporting
# To disable, uncomment this line
dbms.usage_report.enabled=false
```


## Import data

See [README.md](./README.md)

From s3 copy source csv files
Stage them on server

```
mkdir -p /var/lib/neo4j/import/geneieve
sudo mkdir -p /var/lib/neo4j/import/geneieve
sudo chown -R neo4j:neo4j /var/lib/neo4j/import
sudo mv *.csv /mnt/data/neo4j/import/geneieve

sudo systemctl stop neo4j.service
sudo su neo4j
cd /var/lib/neo4j/import/geneieve

neo4j-admin database import full --nodes=nodes.csv --relationships=edges_dedup.csv --overwrite-destination --verbose
```

## Update metadata

As seen here;
https://gitlab.com/cslagile/diffusion-labs/fuze-experiments/-/merge_requests/24
```
time python src/batch_load_drug_features.py
time python src/batch_load_disease_features.py
```
