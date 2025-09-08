# AWSPayment Microservice Python 3.12.10

### Structure
```
AWS_Pagos_Python/
│
│── microservice_auth/
│   ├── .env
│   ├── Dockerfile
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
│
│── notifications_microservce/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
│── transactions_microservice/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
│── users_microservice/
│   ├── app/
│   │   ├── auth.py
│   │   ├── crud.py
│   │   ├── db.py
│   │   ├── main.py
│   │   └── models.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
│── .dockerignore
│── .gitignore
│── api-gateway.yaml
│── deployment-accounts.yaml
│── deployment-notifications.yaml
│── deployment-transactions.yaml
│── deployment-users.yaml
│── docker-compose.yml
│── README.md
└── run_all.bat
```

```mermaid
flowchart TD
  subgraph API_Gateway["API Gateway"]
    direction TB
    A1[Usuarios] -->|JWT| API_Gateway
    A2[Accounts] --> API_Gateway
    A3[Transactions] --> API_Gateway
  end

  subgraph Microservices["Microservicios"]
    direction LR
    Users[Usuarios & Auth] 
    Accounts[Cuentas]
    Transactions[Pagos/Transacciones] 
    Notifications[Notificaciones (SNS/SQS)]
  end

  Users --> Accounts
  Users --> Transactions
  Accounts --> Transactions
  Transactions --> Notifications
```

## Preparing Microservice
- microservice_auth
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

### micropay-sg-rds
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
  - HTTP
    - Type: Custom TCP
    - Protocol: TCP
    - Port range: 8000
    - Destination type: Anywhere-IPv4
    - Destination: 0.0.0.0/0
    - Description: Acceso Web    
- **Outbound rules**:
  - Outbound
    - Type: All traffic
    - Protocol: All
    - Port range: All
    - Destination type: Custom
    - Destination: 0.0.0.0/0
    - Description:    

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
- **Enhanced Monitoring**: Disabled  

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

---

## **CloudShell**:
### Consola CloudShell
- Subir el archivo comprimido
```sh
df -h
docker system prune -a --volumes -f
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
df -h
docker builder prune -f
df -h
cd ..
rm -rf AWS_Api_Worker_SQS_SNS_S3_.NET8
```

---



## **EKS**: Elastic Kubernetes Service
### Clusters
- **Configuration options**: Custom configuration
- **Use EKS Auto Mode**_ uncheck
- **Name**: micropay-eks-cluster
- **Cluster IAM role**: LabEksClusterRole
- **EKS API**: check
- **ARC Zonal shift**: disabled
- **VPC**: default
- **Subnets**: default
- **Additional security groups**: micropay-sg-service
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

### Clusters - Resources - Workload ???