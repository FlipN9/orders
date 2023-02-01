Start vscode and reopen in container

```
vscode@nyu:/app$ make login
```

Create new IBM Cloud namespace
```
vscode@nyu:/app$ ibmcloud cr namespace-add yany
```
Export to new namespace and build // takes some time
```
vscode@nyu:/app$ export NAMESPACE=yany
vscode@nyu:/app$ make build
```
Use docker images to list the local images
```
vscode@nyu:/app$ docker images
REPOSITORY                 TAG       IMAGE ID       CREATED          SIZE
us.icr.io/yany/orders   1.0       62e2b26c2586   30 seconds ago   390MB
```

Use docker push to send to IBM Cloud Container Registry
```
vscode@nyu:/app$ docker push us.icr.io/yany/orders:1.0
The push refers to repository [us.icr.io/yany/orders]
bc151fe41219: Pushed 
44925dcc104e: Pushed 
9f267d2dedd6: Pushed 
9bbcb61a1092: Pushed 
a594c80eb584: Pushed 
9de0365805f7: Pushed 
755710f34a21: Pushed 
83aed24cdd2b: Pushed 
cc3de6b21a41: Pushed 
0255573f4829: Pushed 
43b3c4e3001c: Pushed 
1.0: digest: sha256:9191488a9482b431f503923e877d6855f88813618b533d0ac950a7776cf53538 size: 2626
```

Use ibmcloud cr images to list the IBM Cloud images
```
vscode@nyu:/app$ ibmcloud cr images
Listing images...

Repository                 Tag   Digest         Namespace   Created         Size     Security status   
us.icr.io/yany/orders   1.0   9191488a9482   yany     2 minutes ago   151 MB   No Issues   

OK
```

Use the kubectl get all command to see what is running in the **default** namespace
```
vscode@nyu:/app$ kubectl get all
NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
service/kubernetes   ClusterIP   172.21.0.1   <none>        443/TCP   5h41m
```

Create new namespace "dev" amd "prod":
```
vscode@nyu:/app/deploy$ kubectl create namespace dev
namespace/dev created
vscode@nyu:/app/deploy$ kubectl create namespace prod
namespace/prod created
```

Check namespace in kubernetes:
```
vscode@nyu:/app/deploy$ kubectl get namespace
NAME              STATUS   AGE
default           Active   2d4h
dev               Active   63s
ibm-cert-store    Active   2d3h
ibm-operators     Active   2d4h
ibm-system        Active   2d4h
kube-node-lease   Active   2d4h
kube-public       Active   2d4h
kube-system       Active   2d4h
prod              Active   8h
```

In order to get access to pull docker images in new kubernetes namespace, create new secret for new namespace.
At first check difference between "default" and "dev"
```
vscode@nyu:/app/deploy$ kc get secret -n default
NAME                  TYPE                                  DATA   AGE
all-icr-io            kubernetes.io/dockerconfigjson        1      2d4h
default-token-psxkw   kubernetes.io/service-account-token   3      2d4h
postgres-creds        Opaque
```

```
vscode@nyu:/app/deploy$ kc get secret -n dev
NAME                  TYPE                                  DATA   AGE
default-token-9ljvx   kubernetes.io/service-account-token   3      2m28s
```

Create secret for "dev":
```
vscode@nyu:/app/deploy$ kc get secret all-icr-io -o yaml > icr.yaml
```

Change namespace to "dev":
```
apiVersion: v1
data:
  .dockerconfigjson: eyAiYXVYXRlLmp...
kind: Secret
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: |
      {"apiVersion":"v1","data":{".dockerconfigjson":"eyAiYXV0aHMiOiB7..."},"kind":"Secret","metadata":{"annotations":{},"creationTimestamp":null,"name":"all-icr-io","namespace":"default"},"type":"kubernetes.io/dockerconfigjson"}
  creationTimestamp: "2022-07-18T21:22:26Z"
  name: all-icr-io
  namespace: dev
  resourceVersion: "336"
  uid: bd0a1ee7-32b7-463b-addb-30d7624fe2c9
type: kubernetes.io/dockerconfigjson

```

Update new configure:
```
vscode@nyu:/app/deploy$ kc create -f icr.yaml
secret/all-icr-io created
```

Check authority of "dev":
```
vscode@nyu:/app/deploy$ kc get secret -n dev
NAME                  TYPE                                  DATA   AGE
all-icr-io            kubernetes.io/dockerconfigjson        1      43s
default-token-9ljvx   kubernetes.io/service-account-token   3      7m39s
```

The same for "prod". Then just delete .yaml
```
vscode@nyu:/app/deploy$ rm icr.yaml
```

Apply relevent yaml files and check status of server, pods etc..
```
vscode@nyu:/app/deploy$ kubectl apply -f dev_postgresql.yaml 
statefulset.apps/postgres created
service/postgres created
secret/postgres-creds created
```

```
vscode@nyu:/app/deploy$ kubectl get all -n dev
NAME             READY   STATUS    RESTARTS   AGE
pod/postgres-0   1/1     Running   0          45s

NAME               TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
service/postgres   NodePort   172.21.123.88   <none>        5432:31032/TCP   45s

NAME                        READY   AGE
statefulset.apps/postgres   1/1     47s
```

```
vscode@nyu:/app/deploy$ kubectl create -f dev_deployment.yaml 
deployment.apps/orders created
```

```
vscode@nyu:/app/deploy$ kubectl get all -l app=orders -n dev
NAME                          READY   STATUS    RESTARTS   AGE
pod/orders-7584588978-222x5   1/1     Running   0          45s
pod/orders-7584588978-zzkwp   1/1     Running   0          45s

NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/orders   2/2     2            2           46s

NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/orders-7584588978   2         2         2       46s
```

```
vscode@nyu:/app/deploy$ kubectl logs orders-7584588978-222x5 -n dev
[2022-07-21 01:48:47 +0000] [1] [INFO] Starting gunicorn 20.1.0
[2022-07-21 01:48:47 +0000] [1] [INFO] Listening at: http://0.0.0.0:8080 (1)
[2022-07-21 01:48:47 +0000] [1] [INFO] Using worker: sync
[2022-07-21 01:48:48 +0000] [7] [INFO] Booting worker with pid: 7
[2022-07-21 01:48:53 +0000] [INFO] [log_handlers] Logging handler established
[2022-07-21 01:48:53 +0000] [INFO] [__init__] **********************************************************************
[2022-07-21 01:48:53 +0000] [INFO] [__init__] ************* O R D E R   S E R V I C E   R U N N I N G  *************
[2022-07-21 01:48:53 +0000] [INFO] [__init__] **********************************************************************
[2022-07-21 01:48:54 +0000] [INFO] [__init__] Service initialized!
```

Deploy the service:
```
vscode@nyu:/app/deploy$ kubectl create -f dev_service.yaml 
service/orders created
```

```
vscode@nyu:/app/deploy$ kubectl get service -n dev
NAME       TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
orders     NodePort   172.21.122.11   <none>        8080:31001/TCP   22s
postgres   NodePort   172.21.123.88   <none>        5432:31032/TCP   4m36s
```

Check all status:
```
vscode@nyu:/app/deploy$ vscode@nyu:/app/deploy$ kubectl get all -n dev
NAME                          READY   STATUS    RESTARTS   AGE
pod/orders-7584588978-222x5   1/1     Running   0          4m16s
pod/orders-7584588978-zzkwp   1/1     Running   0          4m16s
pod/postgres-0                1/1     Running   0          5m56s

NAME               TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
service/orders     NodePort   172.21.122.11   <none>        8080:31001/TCP   103s
service/postgres   NodePort   172.21.123.88   <none>        5432:31032/TCP   5m57s

NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/orders   2/2     2            2           4m17s

NAME                                DESIRED   CURRENT   READY   AGE
replicaset.apps/orders-7584588978   2         2         2       4m17s
```

Get pod IP address:
```
vscode@nyu:/app/deploy$ ibmcloud ks workers --cluster nyu-devops
OK
ID                                                     Public IP        Private IP       Flavor   State    Status   Zone    Version   
kube-cbasr26f0j1vn6j31kog-nyudevops-default-000000af   159.122.174.70   10.144.216.178   free     normal   Ready    mil01   1.23.8_1535*   

* To update to 1.23.8_1537 version, run 'ibmcloud ks worker update'. Review and make any required version changes before you update: 'https://ibm.biz/upworker'
```

Visit ip:port:
picture 1
picture 2





If there is issue when loggin, try to reset docker environment:
```
$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

```
docker system prune -f
docker volume prune -f
```



