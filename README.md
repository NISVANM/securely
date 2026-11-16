# Patient API DevSecOps sample

This is a local learning project based on the provided guide. The records in
`/patients` are synthetic. Do not add real patient information or use this as a
production healthcare service.

## Port map

| Service | Address from your Mac | Destination |
| --- | --- | --- |
| Jenkins | `http://localhost:8080` | Jenkins on port 8080 |
| API in Docker | `http://localhost:8081` | Container port 8080 |
| API in Kubernetes | `http://localhost:9000` after port-forwarding | Service port 80 to container port 8080 |

Keep the API's container port at 8080; only its host-side Docker port is 8081.
This leaves Jenkins free to use host port 8080.

## Run locally

With Python 3.12 and pip installed:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest
gunicorn -b 127.0.0.1:8081 app:app
```

In another terminal, verify `http://127.0.0.1:8081/health` and
`http://127.0.0.1:8081/patients`. Port 8080 is used by Jenkins on this Mac.
Build and run the container with:

```sh
docker build -t patient-api:local .
docker run --rm -p 8081:8080 patient-api:local
```

## Docker

Docker Desktop is installed and working in the current Mac environment. To
repeat the container check:

```sh
docker info
docker build -t patient-api:local .
docker run --rm -p 8081:8080 patient-api:local
```

In another terminal, try `curl http://127.0.0.1:8081/health` and
`curl http://127.0.0.1:8081/patients`. Stop the container with Ctrl+C.

## Kubernetes with Minikube

`kubectl` and Minikube are installed. The local cluster is running and the
sample has been deployed to it. To repeat the deployment:

```sh
minikube start --driver=docker --cpus=2 --memory=4096
docker build -t patient-api:local .
minikube image load patient-api:local
sed 's/IMAGE_TAG/local/' k8s/deployment.yaml | kubectl apply -f -
kubectl -n healthcare rollout status deployment/patient-api --timeout=120s
kubectl -n healthcare get pods,svc
```

Access it in one terminal with
`kubectl -n healthcare port-forward svc/patient-api 9000:80`, then in another:

```sh
curl http://127.0.0.1:9000/health
curl http://127.0.0.1:9000/patients
```

Stop port forwarding with Ctrl+C. To stop the cluster when finished, run
`minikube stop`; use `minikube start` to resume it.

`k8s/deployment.yaml` contains a restricted namespace, non-root/read-only
container settings, resource limits, and default-deny network policies. The API
ingress policy permits traffic only from pods in the `healthcare` namespace;
configure a separately reviewed ingress policy if access from another namespace
or an ingress controller is required. The policies require a CNI that enforces
NetworkPolicies, such as Calico.

Important: the existing local cluster uses `kindnet`, so the API objects are
installed but NetworkPolicy enforcement is not verified and should not be
assumed. To try Calico without deleting the current cluster, create a second
Minikube profile:

```sh
minikube start -p patient-api-calico --driver=docker --cni=calico --cpus=2 --memory=4096
minikube image load -p patient-api-calico patient-api:local
kubectl config use-context patient-api-calico
sed 's/IMAGE_TAG/local/' k8s/deployment.yaml | kubectl apply -f -
kubectl -n healthcare rollout status deployment/patient-api --timeout=120s
kubectl get pods -A | grep -i calico
```

Allow time for Calico pods to become Ready before relying on policies. The
profile switch changes the current `kubectl` context. Return to the original
cluster with `kubectl config use-context minikube`.

## Jenkins

Jenkins LTS is installed and running locally at
`http://localhost:8080`. Open `http://localhost:8080/login` in a browser. If
Jenkins asks to be unlocked, find the initial password file under the Jenkins
home directory (commonly `~/.jenkins/secrets/initialAdminPassword`) and enter
its contents in the local Jenkins setup screen. Install the suggested plugins
and create an admin account. Do not share that initial password.

The project is currently only in this local folder; Jenkins' “Pipeline script
from SCM” needs a Git remote it can read. Create a private repository in your
Git host, then from this folder:

```sh
git add .
git commit -m "Add patient API DevSecOps sample"
git branch -M main
git remote add origin <your-private-repository-url>
git push -u origin main
```

In Jenkins, create **New Item → Pipeline**. Under **Pipeline**, select
**Pipeline script from SCM**, choose **Git**, enter the repository URL, and
save. Add credentials through Jenkins' Credentials UI if the repository is
private; never put tokens in the Jenkinsfile or Git. Then choose **Build Now**
and inspect **Console Output**.

The local Jenkins service runs as your Mac user. The pipeline needs that user
to be able to run `docker`, `kubectl`, and `minikube`, and the active kubectl
context must point to the cluster you intend to use. If a build reports
“command not found,” ensure those tools are on the Jenkins service PATH and
restart Jenkins with `brew services restart jenkins-lts`. Jenkins' local
controller executor is suitable only for this disposable learning setup, not
for an internet-exposed or production CI service.

`Jenkinsfile` expects a Jenkins agent with a POSIX shell, Docker CLI, kubectl,
and Minikube configured and accessible to the Jenkins user. It runs secret,
SAST, dependency, Dockerfile, image, deployment, and ZAP baseline checks. The
image scan uses a saved image archive instead of mounting the host Docker
socket, which also works with Docker Desktop's socket setup. ZAP ignores
warnings (`-I`) but scanner errors/failures stop the pipeline; its temporary
container, network, and image archive are cleaned up afterward.

The pipeline uses example scanner image tags from the guide. For a maintained
CI setup, pin scanner images to reviewed versions or digests and update them
through a controlled process. Giving Jenkins access to the Docker socket is
effectively privileged access to the host; use an appropriately isolated,
disposable learning machine.

This sample does not configure Jenkins, install system packages, create a
cluster, configure credentials, or establish HIPAA/GDPR compliance. Those
steps require environment-specific administration and qualified security and
compliance review. Do not deploy this unauthenticated sample with real data.
# securely
