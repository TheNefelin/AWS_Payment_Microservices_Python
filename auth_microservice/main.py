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
from psycopg2 import pool
import logging
# from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def create_db_pool():
    """Crear pool de conexiones con manejo de errores detallado"""
    global db_pool
    try:
        logger.info(f"Intentando crear pool de conexiones...")
        logger.info(f"Host: {RDS_HOST}, Database: {RDS_NAME}, User: {RDS_USER}, Port: {RDS_PORT}")
        
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,  # min y max conexiones
            host=RDS_HOST,
            database=RDS_NAME,
            user=RDS_USER,
            password=RDS_PASS,
            port=int(RDS_PORT),
            # Parámetros adicionales para mejor debugging
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=5,
            keepalives_count=5,
        )
        logger.info("✅ Pool de conexiones creado exitosamente")
        
        # Probar una conexión inmediatamente
        test_conn = db_pool.getconn()
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT 1;")
        result = test_cursor.fetchone()
        test_cursor.close()
        db_pool.putconn(test_conn)
        
        logger.info(f"✅ Pool probado exitosamente: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando pool de conexiones: {str(e)}")
        logger.error(f"❌ Tipo de error: {type(e).__name__}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        db_pool = None
        return False

# Inicializar pool al arrancar
pool_created = create_db_pool()

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

class CognitoTestRequest(BaseModel):
    email: EmailStr
    password: str

# ===== MÉTODO ESPECÍFICO PARA RDS =====
@app.get("/test/rds")
async def test_rds_connection():
    """Método específico para testear solo RDS - SELECT ALL de users"""
    conn = None
    try:
        # Verificar que el pool exista
        if db_pool is None:
            return {
                "status": "error",
                "message": "Pool de conexiones no está disponible",
                "details": "El pool no se creó correctamente al iniciar"
            }
        
        logger.info("🔍 Iniciando test de RDS...")
        
        # Obtener conexión del pool
        conn = db_pool.getconn()
        logger.info("✅ Conexión obtenida del pool")
        
        # Usar RealDictCursor para obtener resultados como diccionarios
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Verificar conexión básica
        cursor.execute("SELECT NOW() as current_time, version() as db_version;")
        connection_info = cursor.fetchone()
        logger.info("✅ Conexión básica exitosa")
        
        # 2. Verificar si existe la tabla users
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            ) as table_exists;
        """)
        table_check = cursor.fetchone()
        logger.info(f"✅ Verificación de tabla: {table_check['table_exists']}")
        
        # 3. Si la tabla existe, hacer SELECT ALL
        users_data = []
        users_count = 0
        
        if table_check['table_exists']:
            # Contar registros
            cursor.execute("SELECT COUNT(*) as total FROM users;")
            count_result = cursor.fetchone()
            users_count = count_result['total']
            
            # Obtener todos los usuarios (limitar a 100 por seguridad)
            cursor.execute("""
                SELECT id, cognito_id, email, created_at 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 100;
            """)
            users_data = cursor.fetchall()
            logger.info(f"✅ SELECT ALL exitoso: {users_count} usuarios encontrados")
        else:
            logger.warning("⚠️ Tabla 'users' no existe")
        
        # 4. Información del esquema de la tabla (si existe)
        table_schema = []
        if table_check['table_exists']:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            table_schema = cursor.fetchall()
        
        cursor.close()
        
        return {
            "status": "success",
            "message": "Test de RDS completado exitosamente",
            "connection_info": {
                "current_time": str(connection_info['current_time']),
                "db_version": connection_info['db_version'][:50] + "..." if len(connection_info['db_version']) > 50 else connection_info['db_version']
            },
            "table_info": {
                "exists": table_check['table_exists'],
                "total_users": users_count,
                "schema": table_schema
            },
            "users": users_data,
            "config": {
                "host": RDS_HOST,
                "database": RDS_NAME,
                "user": RDS_USER,
                "port": RDS_PORT
            }
        }
        
    except psycopg2.OperationalError as e:
        error_msg = f"Error de conexión a PostgreSQL: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "error_type": "OperationalError",
            "details": "Problema de conectividad con RDS"
        }
    except psycopg2.ProgrammingError as e:
        error_msg = f"Error de SQL/Programación: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "error_type": "ProgrammingError",
            "details": "Problema con la consulta SQL o estructura de DB"
        }
    except Exception as e:
        error_msg = f"Error inesperado en RDS: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": error_msg,
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
    finally:
        if conn:
            try:
                db_pool.putconn(conn)
                logger.info("✅ Conexión devuelta al pool")
            except Exception as e:
                logger.error(f"❌ Error devolviendo conexión: {e}")

# ===== MÉTODO ESPECÍFICO PARA COGNITO =====
@app.post("/test/cognito")
async def test_cognito_only(request: CognitoTestRequest):
    """Método específico para testear solo Cognito sin tocar RDS"""
    try:
        logger.info(f"🔍 Iniciando test de Cognito para: {request.email}")
        
        # 1. Verificar variables de entorno
        missing_vars = []
        if not USER_POOL_ID:
            missing_vars.append('COGNITO_USER_POOL_ID')
        if not CLIENT_ID:
            missing_vars.append('COGNITO_CLIENT_ID')
        if not CLIENT_SECRET:
            missing_vars.append('COGNITO_CLIENT_SECRET')
            
        if missing_vars:
            return {
                "status": "error",
                "message": f"Variables faltantes: {', '.join(missing_vars)}",
                "details": "Configuración incompleta de Cognito"
            }
        
        # 2. Crear cliente de Cognito
        client = boto3.client('cognito-idp', region_name=AWS_REGION)
        logger.info("✅ Cliente Cognito creado")
        
        # 3. Verificar información del User Pool
        try:
            pool_info = client.describe_user_pool(UserPoolId=USER_POOL_ID)
            logger.info("✅ User Pool accesible")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error accediendo al User Pool: {str(e)}",
                "error_type": type(e).__name__,
                "details": "Verificar USER_POOL_ID y permisos IAM"
            }
        
        # 4. Verificar información del Client
        try:
            client_info = client.describe_user_pool_client(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID
            )
            logger.info("✅ User Pool Client accesible")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error accediendo al Client: {str(e)}",
                "error_type": type(e).__name__,
                "details": "Verificar CLIENT_ID"
            }
        
        # 5. Calcular secret hash
        def calculate_secret_hash(username, client_id, client_secret):
            message = username + client_id
            dig = hmac.new(
                client_secret.encode('utf-8'),
                msg=message.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            return base64.b64encode(dig).decode()
        
        try:
            secret_hash = calculate_secret_hash(request.email, CLIENT_ID, CLIENT_SECRET)
            logger.info("✅ Secret hash calculado")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error calculando secret hash: {str(e)}",
                "details": "Verificar CLIENT_SECRET"
            }
        
        # 6. Intentar registrar usuario (SOLO PARA TEST)
        cognito_operations = {}
        
        try:
            # Sign Up
            signup_response = client.sign_up(
                ClientId=CLIENT_ID,
                Username=request.email,
                Password=request.password,
                SecretHash=secret_hash,
                UserAttributes=[{'Name': 'email', 'Value': request.email}]
            )
            cognito_operations['signup'] = {
                "status": "success",
                "user_sub": signup_response.get('UserSub'),
                "message": "Usuario registrado en Cognito"
            }
            logger.info("✅ Sign up exitoso")
            
            # Admin Confirm Sign Up
            client.admin_confirm_sign_up(
                UserPoolId=USER_POOL_ID,
                Username=request.email
            )
            cognito_operations['confirm'] = {
                "status": "success",
                "message": "Usuario confirmado"
            }
            logger.info("✅ Confirmación exitosa")
            
            # Marcar email como verificado
            client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=request.email,
                UserAttributes=[
                    {'Name': 'email_verified', 'Value': 'true'}
                ]
            )
            cognito_operations['email_verified'] = {
                "status": "success",
                "message": "Email verificado"
            }
            logger.info("✅ Email verificado")
            
            # Test Login
            login_response = client.admin_initiate_auth(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': request.email,
                    'PASSWORD': request.password,
                    'SECRET_HASH': secret_hash
                }
            )
            cognito_operations['login'] = {
                "status": "success",
                "message": "Login exitoso",
                "has_tokens": bool(login_response.get('AuthenticationResult'))
            }
            logger.info("✅ Login exitoso")
            
            # Cleanup: Eliminar usuario de prueba
            try:
                client.admin_delete_user(
                    UserPoolId=USER_POOL_ID,
                    Username=request.email
                )
                cognito_operations['cleanup'] = {
                    "status": "success",
                    "message": "Usuario de prueba eliminado"
                }
                logger.info("✅ Usuario de prueba eliminado")
            except Exception as e:
                cognito_operations['cleanup'] = {
                    "status": "warning",
                    "message": f"No se pudo eliminar usuario de prueba: {str(e)}"
                }
            
        except client.exceptions.UsernameExistsException:
            cognito_operations['signup'] = {
                "status": "warning",
                "message": "Usuario ya existe (esto es normal para testing)"
            }
            # Si el usuario ya existe, intentar login directamente
            try:
                login_response = client.admin_initiate_auth(
                    UserPoolId=USER_POOL_ID,
                    ClientId=CLIENT_ID,
                    AuthFlow='ADMIN_NO_SRP_AUTH',
                    AuthParameters={
                        'USERNAME': request.email,
                        'PASSWORD': request.password,
                        'SECRET_HASH': secret_hash
                    }
                )
                cognito_operations['existing_user_login'] = {
                    "status": "success",
                    "message": "Login con usuario existente exitoso"
                }
            except Exception as login_error:
                cognito_operations['existing_user_login'] = {
                    "status": "error",
                    "message": f"Login falló: {str(login_error)}"
                }
                
        except Exception as e:
            cognito_operations['signup'] = {
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__
            }
        
        return {
            "status": "success",
            "message": "Test de Cognito completado",
            "pool_info": {
                "pool_name": pool_info['UserPool']['Name'],
                "pool_id": pool_info['UserPool']['Id'],
                "region": AWS_REGION
            },
            "client_info": {
                "client_name": client_info['UserPoolClient'].get('ClientName', 'N/A'),
                "client_id": CLIENT_ID
            },
            "operations": cognito_operations,
            "config": {
                "region": AWS_REGION,
                "user_pool_id": USER_POOL_ID,
                "client_id": CLIENT_ID,
                "has_client_secret": bool(CLIENT_SECRET)
            }
        }
        
    except Exception as e:
        error_msg = f"Error inesperado en Cognito: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": error_msg,
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

# ===== MÉTODO PARA RECREAR EL POOL =====
@app.post("/admin/recreate-pool")
async def recreate_db_pool():
    """Recrear el pool de conexiones manualmente"""
    global db_pool

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
        "AWS_REGION": AWS_REGION,
        "USER_POOL_ID": USER_POOL_ID,
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "RDS_HOST": RDS_HOST,
        "RDS_NAME": RDS_NAME,
        "RDS_USER": RDS_USER,
        "RDS_PASS": RDS_PASS,
        "RDS_PORT": RDS_PORT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)