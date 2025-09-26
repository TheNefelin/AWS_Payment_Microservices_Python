## Preparing Microservice
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

---

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
ls
```
```sh
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123.dkr.ecr.us-east-1.amazonaws.com
docker build -f transaction_microservice/Dockerfile -t micropay-transaction-service-repo ./transaction_microservice
docker tag micropay-transaction-service-repo:latest 123.dkr.ecr.us-east-1.amazonaws.com/micropay-transaction-service-repo:latest
docker push 123.dkr.ecr.us-east-1.amazonaws.com/micropay-transaction-service-repo:latest
```
```sh
docker images
docker builder prune -f
df -h
cd ..
rm -rf AWS_Payment_Microservices_Python
```

---

<!-- ## **EC2**: Elastic Compute Cloud
### **Load Balancers**
- **Load balancer types**: Network Load Balancer
- **Load balancer name**: micropay-nlb
- **Scheme**: Internet-facing (ideal Internal para red privada)
- **VPC**: default
- **Availability Zones and subnets**: default
- **Security groups**: micropay-sg-web -->

---

## **ECS**: Elastic Container Service
### ECS - Cluster
- **Task definition family**: micropay-ecs-microservices-cluster
- **AWS Fargate**: check
- **Amazon EC2 instances**: unchek

### ECS - Task definitions
- **Task definition family**: micropay-ecs-transaction-task
- **AWS Fargate**: check
- **Task role**: LabRole
- **Task execution role**: LabRole
- **Container details**: dotnet-transaction
- **Image URI**: ...amazonaws.com/micropay-transaction-service-repo:latest
- **Container port**: 8000
- **Environment variables**: 
  - **AWS_REGION**: us-east-1
  - **SNS_TOPIC_ARN**: AddValue
  - **COGNITO_USER_POOL_ID**: AddValue
  - **COGNITO_CLIENT_ID**: AddValue
  - **COGNITO_CLIENT_SECRET**: AddValue
  - **RDS_HOST**: AddValue
  - **RDS_PORT**: 5432  
  - **RDS_PASS**: TestingDB
  - **RDS_NAME**: postgres
  - **RDS_USER**: postgres

### ECS - Clouster - Service
- **Task definition family**: micropay-ecs-transaction-task
- **Task definition revision**: 1
- **Service name**: micropay-ecs-transaction-task-service
- **Capacity provider**: FARGATE
- **VPC**: default
- **Subnets**: default
- **Security group name**: micropay-sg-web
- **Public IP**: Turned on
<!-- - **Load balancer type**: Network Load Balancer
- **Container**: dotnet-transaction 8000:8000
- **Create a new load balancer**: check
- **Create new listener**: 80 HTTP
- **Create new target group**: 8000 HTTP -->

---
