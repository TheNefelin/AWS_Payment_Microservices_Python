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

## **EB**: Elastic Beanstalk
- **Environment tier**: Web server environment
- **Application name**: micropay-eb-auth-service
- **Platform**: Docker
- **Platform branch**: Docker running on 64bit Amazon Linux 2023
- **Platform version**: 4.7.0
- **Upload your code**: check
- **Version labe**: 1
- **Local file**: Dockerrun.aws.zip
- **Single instance**: check
- **Service role**: LabRole
- **EC2 instance profile**: LabInstanceProfile
- **EC2 key pair**: vockey
- **VPC**: default
- **Public IP address**: Enable
- **Instance subnets**: us-east-1a
- **EC2 security groups**: micropay-sg-web
- **Health reporting**: Basic
- **Managed updates**: uncheck
- **Environment properties**: 
  - **AWS_REGION**: us-east-1
  - **COGNITO_USER_POOL_ID**: USER_POOL_ID
  - **COGNITO_CLIENT_ID**: CLIENT_ID
  - **COGNITO_CLIENT_SECRET**: CLIENT_SECRET
  - **SNS_TOPIC_ARN**: SNS_ARN
  - **RDS_HOST**: RDS_ENDPOINT
  - **RDS_NAME**: postgres
  - **RDS_USER**: postgres
  - **RDS_PASS**: *****
  - **RDS_PORT**: 5432

### (Redeploy image) Micropay-eb-auth-service-env - Upload and deploy
- **Upload application**: Dockerrun.aws.zip
- **Version label**: 2
- **Deploy**:

```json
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "123.dkr.ecr.us-east-1.amazonaws.com/micropay-auth-service-repo:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": 8000
    }
  ],
  "Environment": [
    {
      "Name": "AWS_REGION",
      "Value": "us-east-1"
    },
    {
      "Name": "COGNITO_USER_POOL_ID",
      "Value": ""
    },
    {
      "Name": "COGNITO_CLIENT_ID",
      "Value": ""
    },
    {
      "Name": "COGNITO_CLIENT_SECRET",
      "Value": ""
    },
    {
      "Name": "SNS_TOPIC_ARN",
      "Value": ""
    },
    {
      "Name": "RDS_HOST",
      "Value": ""
    },
    {
      "Name": "RDS_NAME",
      "Value": "postgres"
    },
    {
      "Name": "RDS_USER",
      "Value": "postgres"
    },
    {
      "Name": "RDS_PASS",
      "Value": "TestingDB"
    },
    {
      "Name": "RDS_PORT",
      "Value": "5432"
    }
  ]
}
```
