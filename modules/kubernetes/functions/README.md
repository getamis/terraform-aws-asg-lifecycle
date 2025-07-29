### Test lambda function with a simple test
---

Pipenv install run-time dependencies and testing dependencies

```
pipenv install
```

### Update pip

```
pipenv update
```

Generate requirements.txt

```
pipenv requirements > requirements.txt
```

### Run the test

Copy environment variables from lambda Configuration/Environment variables

```
export AWS_REGION=

export CLUSTER_NAME=dev-cluster
export KUBERNETES_NODE_ROLE=worker
export KUBE_CONFIG_BUCKET=dev-asg
export KUBE_CONFIG_OBJECT=kubeconfig
export LAUNCHING_TIMEOUT=550
export TERMINATING_TIMEOUT=850
```

Copy data sns event to test.py

```python
data = {'Records': [{...}]}
```

Run the test (with local aws credentials)

```
pipenv run python test.py
```

### Clean up

```
deactivate
rm -rf .venv
rm -f /tmp/kubeconfig
```
