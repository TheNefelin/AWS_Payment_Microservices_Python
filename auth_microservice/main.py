# main.py - Auth Microservice Refactorizado
import datetime
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import boto3
import os
import psycopg2
import hmac
import hashlib
import base64

# Variables de entorno GLOBALES
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.environ.get('COGNITO_CLIENT_SECRET')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
RDS_HOST = os.environ.get('RDS_HOST')
RDS_NAME = os.environ.get('RDS_NAME', 'postgres')
RDS_USER = os.environ.get('RDS_USER', 'postgres')
RDS_PASS = os.environ.get('RDS_PASS')
RDS_PORT = os.environ.get('RDS_PORT', '5432')

# FastAPI App Setup
app = FastAPI(title="MicroPay Auth Service", version="1.0.0", root_path="/")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,    
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LogoutRequest(BaseModel):
    email: str

# Obtener cliente Cognito configurado
def get_cognito_client():
    return boto3.client('cognito-idp', region_name=AWS_REGION)

# Obtener cliente SNS configurado
def get_sns_client():
    return boto3.client('sns', region_name=AWS_REGION)

# Obtener conexión a PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=RDS_HOST,
        port=int(RDS_PORT),
        database=RDS_NAME,
        user=RDS_USER,
        password=RDS_PASS,
        connect_timeout=10
    )

# Guardar usuario en PostgreSQL
def save_user_to_db(cognito_id: str, email: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (cognito_id, email) VALUES (%s, %s)",
            (cognito_id, email)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Calcular secret hash para Cognito
def calculate_secret_hash(username: str) -> str:
    message = username + COGNITO_CLIENT_ID
    dig = hmac.new(
        COGNITO_CLIENT_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

# Registrar y configurar usuario en Cognito
def setup_cognito_user(client, email: str, password: str):
    secret_hash = calculate_secret_hash(email)
    
    # 1. Registrar usuario
    response = client.sign_up(
        ClientId=COGNITO_CLIENT_ID,
        Username=email,
        Password=password,
        SecretHash=secret_hash,
        UserAttributes=[{'Name': 'email', 'Value': email}]
    )
    
    # 2. Verificar administrativamente
    client.admin_confirm_sign_up(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email
    )
    
    # 3. Marcar email como verificado
    client.admin_update_user_attributes(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email,
        UserAttributes=[{'Name': 'email_verified', 'Value': 'true'}]
    )
    
    return response['UserSub']

# Iniciar sesión usuario en Cognito
def login_cognito_user(client, email: str, password: str):
    secret_hash = calculate_secret_hash(email)

    return client.admin_initiate_auth(
        UserPoolId=COGNITO_USER_POOL_ID,
        ClientId=COGNITO_CLIENT_ID,
        AuthFlow='ADMIN_NO_SRP_AUTH',
        AuthParameters={
            'USERNAME': email,
            'PASSWORD': password,
            'SECRET_HASH': secret_hash
        }
    )

# Cerrar sesión usuario en Cognito
def logout_cognito_user(client, email: str):
    client.admin_user_global_sign_out(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=email
    )

def publish_user_sns_message(event_type: str, email: str, user_id: str, extra_data: dict = None):
    sns_client = get_sns_client()

    message_data = {
        "event_type": event_type,
        "email": email,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    if extra_data:
        message_data.update(extra_data)
        
    response = sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message_data),
        Subject=f"User Event: {event_type}"
    )

    return response['MessageId']

@app.post("/auth/register")
async def register(request: RegisterRequest):    
    try:
        client = get_cognito_client()
        
        # Configurar usuario en Cognito
        user_sub = setup_cognito_user(client, request.email, request.password)
        
        # Guardar en PostgreSQL
        save_user_to_db(user_sub, request.email)
        
        # Publicar evento de registro en SNS
        publish_user_sns_message(
            event_type="user_registered",
            email=request.email,
            user_id=user_sub
        )

        return {
            "message": "Usuario registrado y verificado automáticamente",
            "userSub": user_sub,
            "email": request.email
        }
        
    except client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya existe en el sistema")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login")
async def login(request: LoginRequest):    
    try:
        client = get_cognito_client()
        response = login_cognito_user(client, request.email, request.password)        
        auth_result = response['AuthenticationResult']
        
        return {
            "message": "Login exitoso",
            "access_token": auth_result['AccessToken'],
            "refresh_token": auth_result['RefreshToken'],
            "expires_in": auth_result['ExpiresIn'],
            "token_type": auth_result['TokenType']
        }
        
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    except client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/logout")
async def logout(request: LogoutRequest):    
    try:
        client = get_cognito_client()
        logout_cognito_user(client, request.email)

        return {"message": "Logout exitoso"}        
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth")
async def root():
    return {
        "message": "MicroPay Auth Service", 
        "status": "running",
        "endpoints": {
            "/auth/register": "POST - Registrar usuario",
            "/auth/login": "POST - Login usuario", 
            "/auth/logout": "POST - Logout usuario"
        },
        "version": "1.0.0",
        "config_status": {
            "aws_region": AWS_REGION,
            "cognito_configured": "✅" if all([COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET]) else "❌",
            "rds_configured": "✅" if all([RDS_HOST, RDS_PASS]) else "❌"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)