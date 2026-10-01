# MLFLOW Experiment

This directory holds a local mlflow experiment. It is ment to test prompt testing against open ai and claude on bedrock.



## Install

Install python 3.12+

Install `uv`

Install the virtual env

```
uv venv
```

Source the virtual env

```
source .venv/bin/activate
```

Install dependencies

```
uv sync
```


## To Run

Run mlflow ui

```
bin/run-local.sh
```

Visit the webpage


Run experiments for openai

Note: paste credentials in the command line as exported variable

```
python src/openai_eval.py --items on_topic
```


Run experiments for bedrock claude

Note: paste AIA AWS credentials in the command line as exported variables. Note: DIFFLABS AWS credentials will not work, since DIFFLABS does not give claude access

```
python src/bedrock_eval.py --items on_topic
```
