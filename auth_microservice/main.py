# main.py - Aplicación FastAPI local
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import boto3
import os
import hmac
import hashlib
import base64
import psycopg2
from psycopg2 import pool  # IMPORTACIÓN CORREGIDA
# from dotenv import load_dotenv

# Cargar variables de entorno
# load_dotenv()

# Variables de entorno GLOBALES (cargadas UNA SOLA VEZ)
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID')
CLIENT_SECRET = os.environ.get('COGNITO_CLIENT_SECRET')
RDS_HOST = os.environ.get('RDS_HOST')
RDS_NAME = os.environ.get('RDS_NAME', 'postgres')
RDS_USER = os.environ.get('RDS_USER', 'postgres')
RDS_PASS = os.environ.get('RDS_PASS')
RDS_PORT = os.environ.get('RDS_PORT', '5432')

# --- Configuración del pool de conexiones ---
db_pool = None

# Pool de conexiones (CORREGIDO)
try:
    db_pool = pool.SimpleConnectionPool(
        1, 20,
        host=RDS_HOST,
        database=RDS_NAME,  # Usar variable de entorno
        user=RDS_USER,
        password=RDS_PASS,
        port=RDS_PORT         # Usar variable de entorno
    )
    print("✅ Pool de conexiones a PostgreSQL creado exitosamente")
except Exception as e:
    print(f"❌ Error creando el pool de conexiones: {str(e)}")
    db_pool = None

app = FastAPI(title="MicroPay API", version="1.0.0")

# CORS para desarrollo
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

class TokenLogoutRequest(BaseModel):
    access_token: str

def calculate_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

@app.post("/auth/register")
async def register(request: RegisterRequest):    
    try:
        client = boto3.client('cognito-idp')
        secret_hash = calculate_secret_hash(request.email, CLIENT_ID, CLIENT_SECRET)
        conn = None

        # 1. Registrar usuario en Cognito
        response = client.sign_up(
            ClientId=CLIENT_ID,
            Username=request.email,
            Password=request.password,
            SecretHash=secret_hash,
            UserAttributes=[{'Name': 'email', 'Value': request.email}]
        )
        
        # 2. Verificar administrativamente
        client.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=request.email
        )
        
        # 3. Marcar email como verificado
        client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=request.email,
            UserAttributes=[
                {'Name': 'email_verified', 'Value': 'true'}
            ]
        )
        
        # 4. Guardar en PostgreSQL usando el POOL
        conn = db_pool.getconn()  # Obtener conexión del pool
        
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, cognito_sub) VALUES (%s, %s)",
            (request.email, response['UserSub'])
        )
        conn.commit()
        cur.close()
        
        return {
            "message": "Usuario registrado y verificado automáticamente",
            "userSub": response['UserSub'],
            "email": request.email
        }
        
    except client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya existe en el sistema")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            db_pool.putconn(conn)  # Devolver conexión al pool

@app.post("/auth/login")
async def login(request: LoginRequest):    
    try:
        client = boto3.client('cognito-idp')
        secret_hash = calculate_secret_hash(request.email, CLIENT_ID, CLIENT_SECRET)

        response = client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': request.email,
                'PASSWORD': request.password,
                'SECRET_HASH': secret_hash
            }
        )
        
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
        client = boto3.client('cognito-idp')

        secret_hash = calculate_secret_hash(request.email, CLIENT_ID, CLIENT_SECRET)
        
        client.admin_user_global_sign_out(
            UserPoolId=USER_POOL_ID,
            Username=request.email
        )
        
        return {"message": "Logout exitoso"}
        
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "MicroPay Auth Service", 
        "status": "running",
        "endpoints": {
            "/auth/register": "POST - Registrar usuario",
            "/auth/login": "POST - Login usuario",
            "/auth/logout": "POST - Logout usuario"
        },
        "vrsion": "1.0.0",
        AWS_REGION: AWS_REGION,
        USER_POOL_ID: USER_POOL_ID,
        CLIENT_ID: CLIENT_ID,
        CLIENT_SECRET: CLIENT_SECRET,
        RDS_HOST: RDS_HOST,
        RDS_NAME: RDS_NAME,
        RDS_USER: RDS_USER,
        RDS_PASS: RDS_PASS,
        RDS_PORT: RDS_PORT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)