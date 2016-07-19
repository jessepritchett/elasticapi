# elasticapi
Toy REST API for Elasticsearch

* Listens on http://localhost:5001 by default
* Connects to Elasticsearch at http://localhost:9200 by default

```
usage: [-l <local url>] [-t <target url>] [-n]
```

## Quickstart

* Install [Python] (https://www.python.org/downloads)
* Install [Pip] (https://pip.pypa.io/en/stable/installing)
* In clone directory:

```
pip install flask
pip install requests
pip install elasticsearch
python elasticapi.py
```