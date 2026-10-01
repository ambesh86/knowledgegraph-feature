# euGENE Graph Database

euGENE (previously GENEieve) is a curated science knowledge graph stored in neo4j. 


## Install NEO4j

Install [neo4j on EC2](./MACHINE_SETUP.md). 

Note: We experimented with ECS and have scripts to install on ECS using docker (we never resolved/punted on the decision for ebs vs efs data volume attachment during restarts)

## Raw data

The raw data is located in s3 (difflabs account)

```
s3://knowledge-graph-external-data/edges_dedup.csv

s3://knowledge-graph-external-data/nodes.csv

s3://knowledge-graph-external-data/disease_features.csv

s3://knowledge-graph-external-data/drug_features.csv
```

## Connect to data

Data is loaded into neo4j at neo4j://10.88.203.244:7687

You can connect with a neo4j desktop browser after downloading the app https://neo4j.com/download/

Or you can connect with a cypher shell cli 

```
cypher-shell -a neo4j://10.88.203.244:7687 -u neo4j
```


## Clean the data
- Verify this step, but it should already be fixed and saved in s3 correctly.

- Remove the .0 from the ids in the relationships file. Otherwise I see an error in the import logs using —verbose
Vim replace :%s/\.0//g 
Also remove the last line as it has no ids

## Load data
Load foundational data using `neo4j-admin`. This step takes under 1 min.

```
sudo systemctl stop neo4j.service

sudo su neo4j

cd /var/lib/neo4j/import/eugene

neo4j-admin database import full --nodes=nodes.csv --relationships=edges_dedup.csv --overwrite-destination --verbose

Available resources:
  Total machine memory: 30.94GiB
  Free machine memory: 29.96GiB
  Max heap memory : 14.22GiB
  Max worker threads: 4
  Configured max memory: 13.99GiB
  High parallel IO: true

IMPORT DONE in 7s 607ms. 
Imported:
  129375 nodes
  4050249 relationships
  4567749 properties
Peak memory usage: 1.034GiB


Start the server back up and verify the data


sudo systemctl start neo4j.service
```

```
> cypher-shell -a neo4j+ssc://localhost:7687 -u neo4j 
neo4j@neo4j[UNAVAILABLE]> MATCH (n) RETURN count(n) as nodes;
+--------+
| nodes  |
+--------+
| 129375 |
+--------+

1 row
ready to start consuming query after 1613 ms, results consumed after another 13 ms
neo4j@neo4j> MATCH ()-[r]->() RETURN count(r) as count;
+---------+
| count   |
+---------+
| 4050249 |
+---------+
```

```
neo4j@neo4j> // Relationship types
             CALL db.relationshipTypes();
+------------------------------+
| relationshipType             |
+------------------------------+
| "protein_protein"            |
| "contraindication"           |
| "indication"                 |
| "off-label use"              |
| "drug_drug"                  |
| "drug_protein"               |
| "phenotype_protein"          |
| "phenotype_phenotype"        |
| "disease_phenotype_positive" |
| "disease_phenotype_negative" |
| "disease_protein"            |
| "disease_disease"            |
| "drug_effect"                |
| "bioprocess_bioprocess"      |
| "molfunc_protein"            |
| "molfunc_molfunc"            |
| "cellcomp_cellcomp"          |
| "cellcomp_protein"           |
| "bioprocess_protein"         |
| "exposure_protein"           |
| "exposure_disease"           |
| "exposure_exposure"          |
| "exposure_bioprocess"        |
| "exposure_molfunc"           |
| "exposure_cellcomp"          |
| "pathway_pathway"            |
| "pathway_protein"            |
| "anatomy_anatomy"            |
| "anatomy_protein_present"    |
| "anatomy_protein_absent"     |
+------------------------------+
```

## View schema
To view the schema

```
// Show schema
call db.schema.visualization();
```

## List Plugins

```
SHOW procedures;
```

# Update metadata
Update foundational data with additional metadata, this step takes a few hours. TODO: merge this data into the original `nodes.csv` and `edges.csv`, this step can be speed up if the data is merged into the above load.

copy `disease_features.csv` found in s3, to `resources/data`


```
time python src/batch_load_disease_features.py

INFO:__main__:loaded 44133 features for ingest, elapsed time: 0.7317650318145752 seconds
INFO:helper.driver_helper:uri = neo4j+ssc://10.88.xxx.xxx:7687
INFO:adapter.disease_feature_neo4j_adapter:starting batch step 0 start = 0, end = 1000...
INFO:adapter.disease_feature_neo4j_adapter:starting batch step 1 start = 1000, end = 2000...
INFO:adapter.disease_feature_neo4j_adapter:starting batch step 2 start = 2000, end = 3000...
...
INFO:adapter.disease_feature_neo4j_adapter:starting batch step 43 start = 43000, end = 44000...
INFO:adapter.disease_feature_neo4j_adapter:starting batch step 44 start = 44000, end = 45000...
INFO:adapter.disease_feature_neo4j_adapter:updated nodes in 45 iterations with steps of 1000
INFO:adapter.disease_feature_neo4j_adapter:apoc batches = 1104, apoc total = 44133 apoc errors = 0
INFO:__main__:ingest finished, elapsed time: 3190.9993028640747 seconds
python src/batch_load_disease_features.py  2.98s user 0.75s system 0% cpu 53:12.09 total
```


copy `drug_features.csv` to `resources/data`


```
time python src/batch_load_drug_features.py

INFO:__main__:loaded 7957 features for ingest, elapsed time: 0.0686190128326416...
INFO:helper.driver_helper:uri = neo4j+ssc://10.88.xx.xxx:7687
INFO:adapter.drug_feature_neo4j_adapter:starting batch step 0 start = 0, end = 1000...
...
INFO:adapter.drug_feature_neo4j_adapter:starting batch step 6 start = 6000, end = 7000...
INFO:adapter.drug_feature_neo4j_adapter:starting batch step 7 start = 7000, end = 8000...
INFO:adapter.drug_feature_neo4j_adapter:updated nodes in 8 iterations with steps of 1000
INFO:adapter.drug_feature_neo4j_adapter:apoc batches = 398, apoc total = 7957 apoc errors = 0
INFO:__main__:ingest finished, elapsed time: 573.556615114212 seconds...
python src/batch_load_drug_features.py  0.37s user 0.10s system 0% cpu 9:33.96 total
```