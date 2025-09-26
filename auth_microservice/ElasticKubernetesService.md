## Preparing Microservice
```sh
cd auth_microservice
python -m venv venv
venv\Scripts\activate
pip list
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary boto3 python-dotenv pydantic[email]
pip freeze > requirements.txt
uvicorn main:app --reload
curl http://127.0.0.1:8000  # curl http://127.0.0.1:8000/docs
pip install -r requirements.txt
deactivate
```

---

## **ECR**: Elastic Container Registry
### Repositorio - products-service-repo
- **Repository name**: micropay-auth-service-repo
- **Image tag mutability**: Mutable
- **Mutable tag exclusions**:
- **Encryption configuration**: AES-256
- **View push commands**

---

## **CloudShell**:
### Consola CloudShell
```sh
docker system prune -a --volumes -f
docker builder prune -f
df -h
```
```sh
git clone https://github.com/TheNefelin/AWS_Payment_Microservices_Python.git
cd AWS_Payment_Microservices_Python
ls
```
```sh
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123.dkr.ecr.us-east-1.amazonaws.com
docker build -f auth_microservice/Dockerfile -t micropay-auth-service-repo ./auth_microservice
docker tag micropay-auth-service-repo:latest 123.dkr.ecr.us-east-1.amazonaws.com/micropay-auth-service-repo:latest
docker push 123.dkr.ecr.us-east-1.amazonaws.com/micropay-auth-service-repo:latest
```
```sh

docker images
docker builder prune -f
df -h
cd ..
rm -rf AWS_Payment_Microservices_Python
```

---

## **EKS**: Elastic Kubernetes Service
### Clusters
- **Configuration options**: Custom configuration
- **Use EKS Auto Mode**_ uncheck
- **Name**: micropay-eks-microservices
- **Cluster IAM role**: LabEksClusterRole
- **EKS API**: check
- **ARC Zonal shift**: disabled
- **VPC**: default
- **Subnets**: default
- **Additional security groups**: micropay-sg-web
- **Cluster endpoint access**: Public and private

### Clusters - Compute - Add node group
- **Name**: ng-general
- **Node IAM role**: LabRole
- **AMI type**: Amazon Linux 2023 (x86_64)
- **Instance types**: t3.medium
- **Disk size**: 20 GiB
- **Desired size**: 2
- **Minimum size**: 2
- **Maximum size**: 4
- **Subnets** default

---

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-microservice
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auth-microservice
  template:
    metadata:
      labels:
        app: auth-microservice
    spec:
      containers:
      - name: auth-microservice
        image: <YOUR_ECR_CATALOG_IMAGE>
        ports:
        - containerPort: 8000
        env:
        - name: AWS_REGION
          value: us-east-1
        - name: COGNITO_USER_POOL_ID
          value: <VALUE>
        - name: COGNITO_CLIENT_ID
          value: <VALUE>
        - name: COGNITO_CLIENT_SECRET
          value: <VALUE>
        - name: SNS_TOPIC_ARN
          value: <VALUE>
        - name: DB_HOST
          value: <VALUE>
        - name: DB_USER
          value: postgres
        - name: DB_NAME
          value: postgres
        - name: DB_PASS
          value: TestingDB
        - name: DB_PORT
          value: "5432"
---
apiVersion: v1
kind: Service
metadata:
  name: auth-microservice
spec:
  type: ClusterIP # LoadBalancer
  selector:
    app: auth-microservice
  ports:
  - port: 8000
    targetPort: 8000
```

---

## **CloudShell**:
### Consola CloudShell
- Uploda Kunernetes file kubernetes_auth.yaml
- Update Kubernetes Config (Connect kubectl to EKS)
```sh
aws eks update-kubeconfig --name micropay-eks-microservices --region us-east-1
```
```sh
kubectl get nodes
```
```sh
kubectl apply -f kubernetes_auth.yaml
```
```sh
kubectl get all
```
- Opcional
```sh
kubectl delete all --all
kubectl delete configmap --all
kubectl delete secret --all
```
- Cómo obtener estas URLs en tu cluster
- http://<nombre-servicio>.<namespace>.svc.cluster.local:<puerto>
```sh
kubectl get svc --all-namespaces
kubectl get svc -n default
kubectl describe svc auth-microservice -n default
```
- Auth Microservice
http://auth-microservice.default.svc.cluster.local:8000

---
