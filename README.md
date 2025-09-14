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

  subgraph Discovery["Service Discovery"]
    SD[Service Registry<br/>AWS ELB/Route53]
  end

  subgraph Gateway["API Gateway"]
    APIGW[API Gateway<br/>Authentication Layer]
  end

  subgraph Auth["Authentication Service"]
    AUTH[auth_microservice<br/>register, login, logout<br/>Cognito + RDS]
  end

  subgraph Services["Protected Microservices"]
    direction TB
    PAYMENT[payment_microservice<br/>Stripe/PayPal Integration<br/>Payment Processing]
    
    TRANSACTION[transactions_microservice<br/>Transaction History<br/>Balance Management]
    
    NOTIFICATION[notifications_microservice<br/>Email SES<br/>Push Notifications<br/>Webhooks]
  end

  subgraph Data["Data Layer"]
    RDS[(PostgreSQL RDS<br/>users, transactions<br/>payments, notifications)]
    COGNITO[(AWS Cognito<br/>User Pool)]
  end

  subgraph External["External Services"]
    SES[AWS SES<br/>Email]
    SNS[AWS SNS<br/>Push Notifications]
    STRIPE[Stripe API<br/>Payments]
  end

  %% Client connections
  WEB --> APIGW
  MOBILE --> APIGW
  API_CLIENT --> APIGW

  %% Service Discovery
  SD -.->|Service Registration| AUTH
  SD -.->|Service Registration| PAYMENT
  SD -.->|Service Registration| TRANSACTION
  SD -.->|Service Registration| NOTIFICATION

  %% API Gateway routing
  APIGW -->|Authentication Required| AUTH
  APIGW -->|JWT Validation| PAYMENT
  APIGW -->|JWT Validation| TRANSACTION
  APIGW -->|JWT Validation| NOTIFICATION

  %% Service interactions
  AUTH --> COGNITO
  AUTH --> RDS
  
  PAYMENT -->|Create Transaction| TRANSACTION
  PAYMENT -->|Send Receipt| NOTIFICATION
  PAYMENT --> STRIPE
  PAYMENT --> RDS
  
  TRANSACTION -->|Balance Updates| NOTIFICATION
  TRANSACTION --> RDS
  
  NOTIFICATION --> SES
  NOTIFICATION --> SNS
  NOTIFICATION --> RDS

  %% Styling
  classDef auth fill:#e1f5fe
  classDef service fill:#f3e5f5
  classDef data fill:#e8f5e8
  classDef external fill:#fff3e0
  
  class AUTH auth
  class PAYMENT,TRANSACTION,NOTIFICATION service
  class RDS,COGNITO data
  class SES,SNS,STRIPE external
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
    - Destination type: Anywhere-IPv4
    - Destination: 0.0.0.0/0
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
    - Destination type: Anywhere-IPv4
    - Destination: 0.0.0.0/0
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
```sh
cd AWS_Payment_Microservices_Python
```
- Update Kubernete Config (Connect kubectl to EKS)
```sh
aws eks update-kubeconfig --name micropay-eks-microservices --region <REGION>
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

---

## **EB**: Elastic Beanstalk (opcional 1)
- auth_microservice
[ECR + EB + auth microservice](/auth_microservice/Dockerfile)
[Dockerrun.aws.json](/auth_microservice/Dockerrun.aws.json)

- transaction_microservice
[ECR + EB + transaction microservice](/transaction_microservice/Dockerfile)
[Dockerrun.aws.json](/transaction_microservice/Dockerrun.aws.json)

---

## **Api Gateway**:
- **Choose an API type**: HTTP API
- **API name**: micropay-api-gateway
### Api Gateway - Authorization - Create
- **Authorizer settings**: micropay-jwt-authorizer
- **Issuer URL**: Cognito - Token signing key URL
- **Audience**: Cognito - App clients - Client ID

## **Api Gateway**:
- **Choose an API type**: HTTP API
- **API name**: micropay-api-gateway
  - **Integrations**:
    - HTTP
    - Method: ANY
    - URL endpoint: http://micropay-eb-auth-service-env.eba-123.us-east-1.elasticbeanstalk.com
- **Configure routes**:
  - Auth
    - **Method**: ANY
    - **Resource path**: /
    - **Integration target**: URL endpoint Auth

---
