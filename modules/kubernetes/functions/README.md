### Test lambda function with a simple test

Requirements
- python=3.9.x

Setup

```
python3.9 -m venv .venv
source .venv/bin/activate
python --version
Python 3.9.22
```

Install run-time dependencies and testing dependencies

```
pip install -r requirements.txt
pip install aws_lambda_typing
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
python test.py
```

### Clean up

```
deactivate
rm -rf .venv
rm -f /tmp/kubeconfig
```
