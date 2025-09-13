from datetime import datetime
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import boto3
import os
import psycopg2

from dotenv import load_dotenv
load_dotenv()

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
app = FastAPI(title="MicroPay Transaction Service", version="1.0.0", root_path="/")

# Middleware CORS
app.add_middleware(
  CORSMiddleware,
  allow_credentials=True,    
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

# Modelos Pydantic
class TransactionRequest(BaseModel):
  email_from: EmailStr
  email_to: EmailStr
  amount: float

class TransactionModel(BaseModel):
  from_user_id: str
  to_user_id: str
  amount: float

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
def save_user_to_db(data: TransactionModel):
  conn = get_db_connection()
  try:
    cursor = conn.cursor()
    cursor.execute(
      "INSERT INTO transactions (from_user_id, to_user_id, amount) VALUES (%s, %s, %s)",
      (data.from_user_id, data.to_user_id, data.amount)
    )
    conn.commit()
  finally:
    cursor.close()
    conn.close()

# def validate_users_in_db(data: TransactionRequest):
#   conn = get_db_connection()
#   try:
#     cursor = conn.cursor()
#     cursor.execute(
#       "SELECT COUNT(*) FROM users WHERE id IN (%s, %s)",
#       (data.from_user_id, data.to_user_id)
#     )
#     count = cursor.fetchone()[0]
#     return count == 2
#   finally:
#     cursor.close()
#     conn.close()   

def get_user_id_by_email(email: str):
  conn = get_db_connection()
  try:
    cursor = conn.cursor()
    cursor.execute(
      "SELECT id FROM users WHERE email = %s",
      (email,)
    )
    row = cursor.fetchone()
    return row[0] if row else None
  finally:
    cursor.close()
    conn.close()

def fetch_all_transactions():
  conn = get_db_connection()
  try:
    cursor = conn.cursor()
    cursor.execute(
      '''
      SELECT 
        id,
        (SELECT email FROM users WHERE id = a.from_user_id) AS from_user,
        (SELECT email FROM users WHERE id = a.to_user_id) AS to_user,
        a.amount
      FROM transactions a
      ''')
    rows = cursor.fetchall()
    transactions = []
    for row in rows:
      transactions.append({
        "id": row[0],
        "from_user": row[1],
        "to_user": row[2],
        "amount": float(row[3])
      })
    return transactions
  finally:
    cursor.close()
    conn.close()

# Publicar mensaje en SNS
def publish_user_sns_message(subject: str, message_data: object):
  if not SNS_TOPIC_ARN:
    raise HTTPException(status_code=500, detail="SNS_TOPIC_ARN no configurado")
      
  sns_client = get_sns_client()

  response = sns_client.publish(
    TopicArn=SNS_TOPIC_ARN,
    Message=json.dumps(message_data),
    Subject=subject
  )
  
  return response['MessageId']    

@app.post("/transaction/process")
async def process_transaction(request: TransactionRequest):
  try:
    if request.amount <= 0:
      raise HTTPException(status_code=400, detail="El monto de la transacción debe ser mayor que cero")
    
    if not all([request.email_from, request.email_to]):
      raise HTTPException(status_code=400, detail="Los IDs de usuario no pueden estar vacíos")
    
    if request.email_from == request.email_to:
      raise HTTPException(status_code=400, detail="El ID del usuario remitente y destinatario no pueden ser iguales")

    transaction_model = TransactionModel(
      from_user_id=get_user_id_by_email(request.email_from),
      to_user_id=get_user_id_by_email(request.email_to),
      amount=request.amount
    )

    if not transaction_model.from_user_id or not transaction_model.to_user_id:
      raise HTTPException(status_code=404, detail="Uno o ambos usuarios no existen en la base de datos")

    save_user_to_db(transaction_model)

    message_data_from = {
      "event type": "Transaccion Realizada",
      "para email": request.email_from,
      "monto": request.amount,
      "timestamp": datetime.utcnow().isoformat()
    }
    
    message_data_to = {
      "event type": "Transaccion Recibida",
      "de email": request.email_to,
      "monto": request.amount,
      "timestamp": datetime.utcnow().isoformat()
    }
      
    publish_user_sns_message("Transaccion Realizada",message_data_from)      
    publish_user_sns_message("Transaccion Recibida", message_data_to)

    return {
      "message": "Transacción procesada exitosamente",
      "transaction": request.dict()
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/transaction/all")
async def get_all_transactions():
  try:
    transactions = fetch_all_transactions()
    return {
      "transactions": transactions,
      "count": len(transactions)
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))    

@app.get("/transaction")
async def root():
  return {
    "message": "MicroPay Auth Service", 
    "status": "running",
    "endpoints": {
      "/transaction/process": "POST - Nueva transaccion", 
      "/transaction/all": "GET - Todas las transacciones"
    },
    "version": "1.0.0",
    "config_status": {
      "aws_region": AWS_REGION,
      "cognito_configured": "✅" if all([COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET]) else "❌",
      "rds_configured": "✅" if all([RDS_HOST, RDS_PASS]) else "❌",
      "sns_configured": "✅" if SNS_TOPIC_ARN else "❌"
    }
  }

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
