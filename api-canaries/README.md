# API Canaries

This directory holds canary source and deployment files to test and monitor the euGENE API



## Run locally baremetal

### Install

install python 3.12+

```
python -m venv venv

source venv/bin/activate
```


```
pip install -r requirements.txt
```

### Run

To run against the difflabs instance

Connect to VPN and run

```
python src/canary_cli.py --difflabs
```