# Maintenance

This document captures information around maintenance for EUGENE.


The order and list is ad hoc


* Neo4j has a SSL cert that expires close to end of the year, check the cert/bolt folder
* The load balancer has a self signed cert that is created and uploaded by me. The script is probably [here](../bin/alb/1.sh)
* Sometimes I have network hiccups from my laptop to CSL DIFFLABS AWS Account. I tends to go away after 10 mins, rarely longer. Maybe 1-2x per month
* The `eugene_ws` service in the difflabs account is monitored by `api-canaries`. You can visit the cloudwatch alarms page and see if a endpoint is failing and for how long
* Sometimes neo4j will crash if a lot of heavy analytics queries are running. Log into the machine and service restart it, and it should recover in minutes
* During deployments, sometimes you need to reset the target group target hosts. This happens since the loadbalancer and target groups are managed in independent terraform scripts
* Information about data loaded into eugene is exposed at the [stats endpoint](https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/stats). 

Sample output

```
{
  "node_count": "484.3k",
  "relationship_count": "21.4m",
  "drug_count": "4.6k",
  "drug_synonym_count": 0,
  "disease_count": "17.1k",
  "gene_protein_count": "27.7k",
  "uspto_count": "0",
  "clinical_trial_count": "49.3k",
  "therapeutic_area_count": "0",
  "therapeutic_area_subgroup_count": "0",
  "pubmed_count": "0",
  "pubmed_researcher_count": "0",
  "organization_count": "26.1k",
  "disambiguated_organization_count": "0"
}
```

notice the endpoints and data for pubmed, theraputic area and uspto and patents are empty. The data was deleted and never reloaded from the ingest notebook.

* The similarity endpoint requires a projected graph that happens out of band in the `patents_trainer` docker task. You can run that script manually. The script is found in the `eugene` cypher scipts. If the projected graph is not found the query will fail. The projected graph only lives until a server restart and is not persisted across restarts.
* Python 3.14 is less stable than 3.12 in terms of subtle package installation errors
