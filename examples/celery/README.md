# Readme

Run a worker:

```shell
PYTHONPATH=../.. celery -A tasks worker --loglevel=info
```

Run a client:

```shell
PYTHONPATH=../.. python client.py
```
