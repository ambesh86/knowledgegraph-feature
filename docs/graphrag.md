# GRAPHRAG
This repo holds experiments around the use of gen ai to extract knowledge and summarize unstructured data. The GraphRAG term indicates the code will feed into a database to provide context to a chat bot or agent. The end goal is to develop an understanding of the different approaches and literature in the space. The goal is also to apply the technology to __enabling__ users to compare independent datasets  


## Setup

### Install python 3.12+

```
cd graphrag
pyenv virtualenv graphrag-env
pyenv activate graphrag-env
pip install -r requirements.txt
```

Currently there is not a clean entry point, depending on what code you run you may need to set env vars

Create a `.env` and set the following variables if needed. For example, OPEN_API_KEY is needed to connect to the ChatGPT LLM, AWS_* is needed to connect to the Bedrock LLM. 

```
OPENAI_API_KEY=
AWS_ACCESS_KEY_ID==
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
```

### Install and Setup AWS CLI - The pytests appear to need this

See, https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions


### Install and Setup Huggyface CLI to download models - The scripts for vectorization need this

The requirements.txt step should download the model, if not manually do so like this
```
pip install -U "huggingface_hub[cli]"
```

Then download the model locally
```
huggingface-cli download sentence-transformers/all-mpnet-base-v2
```


## 00. DEPRECATED: Run General GraphRAG (Optional)

First drop some sample `.pdf` files into `resources/data`

Next run the program

```
pyenv activate graphrag-env
python src/analyze.py
python src/link_docs.py
python src/store_triples.py
python src/graph_query.py
python src/store_summaries.py
```

## 0. Update foundational nodes

## 1. Ingest Additional Layers into euGENE Foundational Graph

1aa. *Log into the neo4j instance and run these steps first!* See the foundational graph ingest [steps](./eugene/README.md)

1ab. Activate the pyenv

```
pyenv activate graphrag-env
```

## 1a. Ingest drug aliases

```
python src/ingest_drug_aliases.py

INFO:graph.infra.db.graph_db_connection_factory:found neo4j creds neo4j@neo4j+ssc://10.88.203.251:7687
INFO:foundation.provider.drug_aliases_update_orchestrator:merging 7958 unique drug bank ids
INFO:foundation.infra.db.adapter.neo4j_drug_aliases_adapter:upserting aliases for 7958 drug(s)
...
INFO:annotation.timer_annotation:Function 'upsert_drug_aliases' executed in 2673.5842 seconds.
python src/ingest_drug_aliases.py  44.13s user 9.16s system 1% cpu 44:36.34 total
```

## 1b. DEPRECATED: Ingest Organizations into euGENE Foundational Graph

This step will disambiguate organization names using an LLM. Input, checkout, and output runs are in S3 [here](s3://knowledge-graph-external-data/organization/). To reproduce do the following;

1ba. Activate the pyenv. For example;

```source venv_graphrag_ingest/bin/activate```

1bb. Analyze organizations using an LLM. This takes about 4.5 hours per input file. Or 9 hrs for both. If you stop and restart the processing, checkpoint files will be used saving costs in reprocessing an organization name using an LLM.

Generate checkpoint files, this is the expensive LLM step

```
nohup python src/analyze_organizations.py --resource-file resources/data/organization/organizations.all.txt --checkpoint-basedir output/checkpoint &
```

1bc. Export the organization checkpoint files into master CSV

Read checkpoint directory, merge organizations, assign an id, and export to a csv

Note: todo: The ids are generated all in the same processing batch, it would be nice to add new orgs without regenerating all org ids

```
# remove old files
rm -rf output/export/organization/organization_mappings_minimized.$(date -I).csv && rm -rf output/export/organization/organization_mappings_full.$(data -I).csv  

# generate an export using just offical name and spellings
python src/export_organizations.py  --checkpoint-basedir output/checkpoint/organization/ --minimize-fields --out output/export/organization/organization_mappings_minimized.$(date -I).csv

# generate an export trying to also include a parent org rollup
python src/export_organizations.py  --checkpoint-basedir output/checkpoint/organization/ --out output/export/organization/organization_mappings_full.$(date -I).csv
```

Verify the export csv against the orginal input file
```
# take the original list and verify the results
python src/lookup_organization_ids.py --mappings-file ./output/export/organization/organization_mappings_minimized.10-13-25.csv
```

1bd. Ingest organizations into `neo4j`. **NOTE: DEPRECATED: THIS IS NOT FINISHED AND IS A WORK IN PROGRESS. The orgs may be ingested from a different method**

```
python src/ingest_organizations.py --checkpoint-basedir output/checkpoint/organization
```

## 2. DEPRECATED: Layer PubMed Data into euGENE Foundational Graph

2a. Download free pubmed central `.pdf` files into `resources/data`. The pubmed query contains diseases and drugs we have interest in. Modify the queries as needed.

```
nohup time python src/download_pubmed.py --search-terms 'von Willebrand Disease' 'aGVHD' &
```

You should have `.pdf` files in a `tmp` directory. Copy those files into `resource/data/pubmed`

2b. Extract knowledge, ingest and link PubMed documents into euGENE.

```
nohup time python src/link_pubmed_articles.py &
```

## 3. DEPRECATED: Layer ClinicalTrial Data into euGENE Foundational Graph

_These steps are not accurate. Update this section..._

3a. Download clincal trial data

```
python src/download_clinicaltrail.py --drug prednisone --disease GvHD
```

## 4. DEPRECATED: Link PubMed Data And ClinicalTrial Data into euGENE Foundational Graph

4a. Fix PubMed nodes and link nodes to clinical trials nodes. The fix script allows you to fix pubmed articles based on pmcids or file names. Also the script can make updates to the foundational graph by labels.

```
nohup time python src/fix_pubmed_articles.py --fix-by-pmcids --fix-nodes anatomy gene_protein drug disease &
```

## 5. DEPRECATED: Layer Patent Data into euGENE Foundational Graph

5a. Download and link patent data.

```
nohup time python src/download_and_link_patent_applications.py --max-applications 2 &
```

## 6. Layer TPP Data into euGENE Foundational Graph

### 6a. Analyze. Download and link CSL TPP data. Copy `pptx` files into `resources/data/tpp`

```
nohup time python src/analyze_tpps.py  &
```

### 6b. Train

**May Be Optional At The Time of Reading:** Fix the graph labels and node_ids. Added one hot encoding and embeddings which may be needed for training.
```
nohup time python src/fix_foundations_nodes.py & 
```

Train TPP for RAG search
```
python src/train_for_search.py
```

Train using `Docker`
```
# clean old images if needed
sudo docker system prune -a --volumes

sudo docker build -f containers/patent_search_trainer/Dockerfile . -t patent_search_trainer

sudo docker run --mount type=bind,source=./.env,target=/app/.env,ro -it patent_search_trainer /bin/bash
```

### 6c. Search. Query TPP and USPTO patents. Look up the TPP `node_id` and pass in the command line

```
time python src/query_patents.py query-embeddings --include "Hemophilia A non-viral, in vivo GenMeds" --exclude "von Willebrand Disease"

time python src/query_patents.py query-tpp --tpp-id dd485875e4b59bc35883471d7fc9f01d

time python src/query_patents.py query-tpp-question --tpp-id dd485875e4b59bc35883471d7fc9f01d --question indication

time python src/query_patents.py query-tpp-and-graph-embeddings --tpp-id 2b991311ba1be0062e29509a1e140329
```

## 9. Develop Webservices

See [developing eugene_ws](eugene_ws.md)

## Documents

[Knowlege Graph: Current Landscape] - https://cslbehring.atlassian.net/l/cp/UjejBqj8
[Knowledge Graph Pitch] - https://cslbehring.atlassian.net/l/cp/9V11j4fv
[GraphRAG] - https://arxiv.org/html/2404.16130v1
[HybridRAG] - https://arxiv.org/html/2408.04948v1




