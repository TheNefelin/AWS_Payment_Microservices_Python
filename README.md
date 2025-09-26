# AWS Payment Microservice Python 3.12.10

### Structure
```
AWS_Payment_Microservices_Python/
│
│── auth_microservice/
│   ├── .env
│   ├── .env.dev
│   ├── Dockerfile
│   ├── dockerrun.aws.json
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
│
│── transaction_microservice/
│   ├── .env
│   ├── .env.dev
│   ├── Dockerfile
│   ├── dockerrun.aws.json
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
│
│── .dockerignore
│── .gitignore
│── docker-compose.yml
│── kubernetes_auth.yaml
│── kubernetes_transaction.yaml
│── LICENSE.txt
│── PostgreSQL.sql
│── README.md
└── run_docker_local.bat
```

```mermaid
flowchart TD
  subgraph Client["Cliente"]
    WEB[Web App]
    MOBILE[Mobile App]
    API_CLIENT[API Client]
  end

  subgraph AWS_APIGW["AWS API Gateway"]
    APIGW[HTTP API Gateway<br/>micropay-api-gateway<br/>VPC Link Integration]
  end

  subgraph EKS_Cluster["EKS Cluster - micropay-eks-microservices"]
    subgraph Discovery["Service Discovery"]
      SD[Service Registry<br/>ConfigMap + ClusterIP<br/>Internal K8s DNS]
    end
    
    subgraph Auth_Service["Auth Microservice Pod"]
      AUTH[auth-microservice<br/>ClusterIP Service<br/>Port 8000<br/>register, login, logout]
    end
    
    subgraph Transaction_Service["Transaction Microservice Pod"]
      TRANSACTION[transaction-microservice<br/>ClusterIP Service<br/>Port 8000<br/>Transaction History<br/>Balance Management]
    end
  end

  subgraph AWS_Data["AWS Data Layer"]
    RDS[(PostgreSQL RDS<br/>micropay-rds-pgdb<br/>users, transactions)]
    COGNITO[(AWS Cognito<br/>micropay-cognito<br/>User Pool)]
  end

  subgraph AWS_Notifications["AWS Notification Services"]
    SNS[AWS SNS<br/>micropay-sns<br/>Push Notifications]
    SES[AWS SES<br/>Email Service]
  end

  subgraph External["External Payment Services"]
    STRIPE[Stripe API<br/>Payment Processing]
    PAYPAL[PayPal API<br/>Alternative Payments]
  end

  %% Client connections
  WEB --> APIGW
  MOBILE --> APIGW
  API_CLIENT --> APIGW

  %% API Gateway to EKS through VPC Link
  APIGW -->|VPC Link<br/>micropay-vpc-link| AUTH
  APIGW -->|VPC Link<br/>micropay-vpc-link| TRANSACTION

  %% Internal Service Discovery
  SD -.->|DNS Resolution| AUTH
  SD -.->|DNS Resolution| TRANSACTION

  %% Service interactions within cluster
  AUTH -->|Internal K8s DNS| TRANSACTION
  TRANSACTION -->|Internal K8s DNS| AUTH

  %% External connections from EKS
  AUTH --> COGNITO
  AUTH --> RDS
  TRANSACTION --> RDS
  TRANSACTION --> SNS
  AUTH --> SES
  TRANSACTION --> STRIPE
  TRANSACTION --> PAYPAL

  %% Styling
  classDef auth fill:#e1f5fe,stroke:#01579b
  classDef service fill:#f3e5f5,stroke:#4a148c
  classDef data fill:#e8f5e8,stroke:#1b5e20
  classDef external fill:#fff3e0,stroke:#e65100
  classDef aws fill:#ff9800,stroke:#e65100
  classDef eks fill:#2196f3,stroke:#0d47a1
  
  class AUTH auth
  class TRANSACTION service
  class RDS,COGNITO data
  class STRIPE,PAYPAL external
  class APIGW,SNS,SES aws
  class SD,EKS_Cluster eks
```

## Preparing Microservice
- auth_microservice
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
- transaction_microservice
```sh
cd transaction_microservice
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

# AWS
## **Seciruty Group**:
### micropay-sg-rds
- **Name**: micropay-sg-rds
- **Description**: Acceso RDS
- **VPC**: default
- **Inbound rules**:
  - PostgreSQL
    - Type: PostgreSQL
    - Protocol: TCP
    - Port range: 5432
    - Destination type: Custom
    - Destination: micropay-sg-web
    - Description: Acceso PostgreSQL
- **Outbound rules**:
  - Outbound
    - Type: All traffic
    - Protocol: All
    - Port range: All
    - Destination type: Custom
    - Destination: 0.0.0.0/0
    - Description:

### micropay-sg-web
- **Name**: micropay-sg-web
- **Description**: Acceso Web
- **VPC**: default
- **Inbound rules**:
  - HTTP
    - Type: HTTP
    - Protocol: TCP
    - Port range: 80
    - Destination type: Anywhere-IPv4
    - Destination: 0.0.0.0/0
    - Description: Acceso Web
  - Custom TCP
    - Type: Custom TCP
    - Protocol: TCP
    - Port range: 8000
    - Destination type: Anywhere-IPv4
    - Destination: 0.0.0.0/0
    - Description: Acceso Web
  - PostgreSQL
    - Type: PostgreSQL
    - Protocol: TCP
    - Port range: 5432
    - Destination type: Custom
    - Destination: micropay-sg-rds
    - Description: Acceso PostgreSQL
- **Outbound rules**:
  - Outbound
    - Type: All traffic
    - Protocol: All
    - Port range: All
    - Destination type: Custom
    - Destination: 0.0.0.0/0
    - Description:

---

## **SNS**: Simple Notification Service 
### Topics
- **Topics**: Standard
- **Name**: micropay-sns

---

## **RDS**: Relational Database Service
### PostgreSQL
- **Creation method**: Standard create
- **Engine type**: PostgreSQL
- **Templates**: Sandbox
- **Availability and durability**: Single-AZ DB instance deployment (1 instance)
- **DB instance**: micropay-rds-pgdb
- **Master username**: postgres
- **Credentials management**: ********
- **Instance configuration**:
    - Burstable classes (includes t classes)
    - db.t3.micro
- **Allocated storage**: 20 GiB
- **Enable storage autoscaling**: check
- **Compute resource**: Don’t connect to an EC2 compute resource
- **VPC**: default
- **DB subnet group**: default
- **Public access**: Yes
- **Security groups**: micropay-sg-rds
- **Monitoring**: Database Insights - Standard
- **Enable Performance insights**: Disabled  

### [PostgreSQL.sql](PostgreSQL.sql)

---

## **Cognito**:
### Create user pool
- **Application type**: Machine-to-machine application
- **Name**: micropay-cognito

### Cognito - User Pool
- User pool ID

### Cognito - App clients - micropay-cognito
- Client ID
- Client secret

### Cognito - App clients - micropay-cognito - edit
- **Sign in with username and password: ALLOW_USER_PASSWORD_AUTH**: check
- **Sign in with server-side administrative credentials: ALLOW_ADMIN_USER_PASSWORD_AUTH**: check

---

## **ECR**: Elastic Container Registry
### Repositorio - products-service-repo
- **Repository name**: micropay-auth-service-repo
- **Image tag mutability**: Mutable
- **Mutable tag exclusions**:
- **Encryption configuration**: AES-256
- **View push commands**

## **ECR**: Elastic Container Registry
### Repositorio - products-service-repo
- **Repository name**: micropay-transaction-service-repo
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
```
```sh
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123.dkr.ecr.us-east-1.amazonaws.com
```
```sh
docker build -f auth_microservice/Dockerfile -t micropay-auth-service-repo ./auth_microservice
docker tag micropay-auth-service-repo:latest 123.dkr.ecr.us-east-1.amazonaws.com/micropay-auth-service-repo:latest
docker push 123.dkr.ecr.us-east-1.amazonaws.com/micropay-auth-service-repo:latest
```
```sh
docker build -f transaction_microservice/Dockerfile -t micropay-transaction-service-repo ./transaction_microservice
docker tag micropay-transaction-service-repo:latest 123.dkr.ecr.us-east-1.amazonaws.com/micropay-transaction-service-repo:latest
docker push 123.dkr.ecr.us-east-1.amazonaws.com/micropay-transaction-service-repo:latest
```
```sh
docker images
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

## **CloudShell**:
### Consola CloudShell
- Uploda Kunernetes file (kubernetes_auth.yaml) (kubernetes_transaction.yaml)
- Update Kubernetes Config (Connect kubectl to EKS)
```sh
aws eks update-kubeconfig --name micropay-eks-microservices --region us-east-1
```
```sh
kubectl get nodes
```
```sh
kubectl apply -f kubernetes_auth.yaml
kubectl apply -f kubernetes_transaction.yaml
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
# Ver todos los servicios en todos los namespaces
kubectl get svc --all-namespaces
# Ver servicios en el namespace default (donde tienes tus microservicios)
kubectl get svc -n default
# Ver detalles específicos de un servicio
kubectl describe svc auth-microservice -n default
kubectl describe svc transaction-microservice -n default
```
- Auth Microservice
http://auth-microservice.default.svc.cluster.local:8000
- Transaction Microservice  
http://transaction-microservice.default.svc.cluster.local:8000

---

## **Api Gateway**:
- **Choose an API type**: HTTP API
- **API name**: micropay-api-gateway

### Api Gateway - VPC links
- **Choose a VPC link version**: VPC link for HTTP APIs
- **Name**: micropay-vpc-link
- **VPC**: default
- **Subnets**: default
- **Security groups**: micropay-sg-web

### Api Gateway - Integrations
- **Attach this integration to a route**: http://10.100.127.183:8000
- **Integration type**: Private resource
- **VPC link**: micropay-vpc-link

---

## **EB**: Elastic Beanstalk (opcional 2)
- auth_microservice
[ECR + EB + auth microservice](/auth_microservice/Dockerfile)
[Dockerrun.aws.json](/auth_microservice/Dockerrun.aws.json)

- transaction_microservice
[ECR + EB + transaction microservice](/transaction_microservice/Dockerfile)
[Dockerrun.aws.json](/transaction_microservice/Dockerrun.aws.json)

---
