# Develop Eugene Webservices

setup env

```
python -m venv venv_eugene_ws
pip install -r difflabs/containers/eugene_ws/requirements.txt
```

start webserver

```
uvicorn eugene_ws:app --app-dir src --reload
```

visit http://localhost:8000/docs

## Tests

Run the tests with `pytest`

```
source venv/bin/activate
pytest
```


## Install new pacakges

If you pip install a new package make sure to remember to add it to the docker build


```
pip install <pkg>
# difflabs docker
pip freeze > difflabs/containers/eugene_ws/requirements.txt
# aia docker
pip freeze > containers/eugene_ws/requirements.txt
```