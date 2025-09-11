# main.py - Notifications Microservice
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import boto3
import os
import psycopg2
from datetime import datetime
from typing import Optional, List
from enum import Enum

# Variables de entorno
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
RDS_HOST = os.environ.get('RDS_HOST')
RDS_NAME = os.environ.get('RDS_NAME', 'postgres')
RDS_USER = os.environ.get('RDS_USER', 'postgres')
RDS_PASS = os.environ.get('RDS_PASS')
RDS_PORT = os.environ.get('RDS_PORT', '5432')

app = FastAPI(title="MicroPay Notifications Service", version="1.0.0", root_path="/")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,    
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class NotificationType(str, Enum):
    REGISTRATION = "registration"
    PAYMENT = "payment"
    TRANSACTION = "transaction"
    GENERAL = "general"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

# Modelos Pydantic
class SendNotificationRequest(BaseModel):
    recipient_email: EmailStr
    notification_type: NotificationType
    subject: str
    message: str
    user_id: Optional[str] = None
    reference_id: Optional[str] = None  # payment_id, transaction_id, etc.

class NotificationResponse(BaseModel):
    id: str
    recipient_email: str
    notification_type: str
    subject: str
    status: str
    created_at: str
    sent_at: Optional[str] = None

# Función para obtener conexión DB
def get_db_connection():
    return psycopg2.connect(
        host=RDS_HOST,
        port=int(RDS_PORT),
        database=RDS_NAME,
        user=RDS_USER,
        password=RDS_PASS,
        connect_timeout=10
    )

# Función para enviar email via SES
def send_email_ses(recipient_email: str, subject: str, message: str):
    try:
        ses_client = boto3.client('ses', region_name=AWS_REGION)
        
        response = ses_client.send_email(
            Source='noreply@micropay.com',  # Cambiar por tu email verificado en SES
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': message, 'Charset': 'UTF-8'},
                    'Html': {'Data': f'<html><body><p>{message}</p></body></html>', 'Charset': 'UTF-8'}
                }
            }
        )
        
        return response['MessageId']
    except Exception as e:
        print(f"Error enviando email SES: {str(e)}")
        return None

# Función para enviar push notification via SNS
def send_push_notification(message: str, topic_arn: str = None):
    try:
        sns_client = boto3.client('sns', region_name=AWS_REGION)
        
        if topic_arn:
            response = sns_client.publish(
                TopicArn=topic_arn,
                Message=message,
                Subject='MicroPay Notification'
            )
        else:
            # Para desarrollo, solo log
            print(f"SNS Push (mock): {message}")
            return "mock-message-id"
            
        return response['MessageId']
    except Exception as e:
        print(f"Error enviando SNS: {str(e)}")
        return None

@app.post("/notifications/send", response_model=dict)
async def send_notification(request: SendNotificationRequest):
    """Enviar notificación (email + push)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Guardar notificación en BD (estado pending)
        cursor.execute("""
            INSERT INTO notifications (recipient_email, notification_type, subject, message, user_id, reference_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.recipient_email,
            request.notification_type.value,
            request.subject,
            request.message,
            request.user_id,
            request.reference_id,
            NotificationStatus.PENDING.value,
            datetime.utcnow()
        ))
        
        notification_id = cursor.fetchone()[0]
        
        # 2. Intentar enviar email via SES
        email_message_id = send_email_ses(
            request.recipient_email,
            request.subject,
            request.message
        )
        
        # 3. Intentar enviar push notification
        push_message_id = send_push_notification(
            f"{request.subject}: {request.message}"
        )
        
        # 4. Actualizar estado en BD
        status = NotificationStatus.SENT.value if (email_message_id or push_message_id) else NotificationStatus.FAILED.value
        
        cursor.execute("""
            UPDATE notifications 
            SET status = %s, sent_at = %s, email_message_id = %s, push_message_id = %s
            WHERE id = %s
        """, (
            status,
            datetime.utcnow() if status == NotificationStatus.SENT.value else None,
            email_message_id,
            push_message_id,
            notification_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "message": "Notificación procesada",
            "notification_id": str(notification_id),
            "status": status,
            "email_sent": bool(email_message_id),
            "push_sent": bool(push_message_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications/registration")
async def send_registration_notification(recipient_email: EmailStr, user_id: str):
    """Notificación de registro exitoso"""
    request = SendNotificationRequest(
        recipient_email=recipient_email,
        notification_type=NotificationType.REGISTRATION,
        subject="¡Bienvenido a MicroPay!",
        message=f"Tu cuenta ha sido creada exitosamente. ¡Gracias por registrarte en MicroPay!",
        user_id=user_id
    )
    return await send_notification(request)

@app.post("/notifications/payment")
async def send_payment_notification(recipient_email: EmailStr, amount: float, payment_id: str, user_id: str = None):
    """Notificación de pago exitoso"""
    request = SendNotificationRequest(
        recipient_email=recipient_email,
        notification_type=NotificationType.PAYMENT,
        subject="Pago Procesado - MicroPay",
        message=f"Tu pago de ${amount:.2f} ha sido procesado exitosamente. ID: {payment_id}",
        user_id=user_id,
        reference_id=payment_id
    )
    return await send_notification(request)

@app.post("/notifications/transaction")
async def send_transaction_notification(recipient_email: EmailStr, amount: float, transaction_type: str, transaction_id: str, balance: float = None, user_id: str = None):
    """Notificación de transacción"""
    balance_text = f" Tu balance actual es: ${balance:.2f}" if balance else ""
    
    request = SendNotificationRequest(
        recipient_email=recipient_email,
        notification_type=NotificationType.TRANSACTION,
        subject=f"Transacción {transaction_type} - MicroPay",
        message=f"Transacción de {transaction_type} por ${amount:.2f} completada.{balance_text} ID: {transaction_id}",
        user_id=user_id,
        reference_id=transaction_id
    )
    return await send_notification(request)

@app.get("/notifications/{user_id}", response_model=List[dict])
async def get_user_notifications(user_id: str, limit: int = 10):
    """Obtener notificaciones de un usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, recipient_email, notification_type, subject, message, status, created_at, sent_at
            FROM notifications 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_id, limit))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                "id": str(row[0]),
                "recipient_email": row[1],
                "notification_type": row[2],
                "subject": row[3],
                "message": row[4],
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "sent_at": row[7].isoformat() if row[7] else None
            })
        
        cursor.close()
        conn.close()
        
        return notifications
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications")
async def get_all_notifications(limit: int = 20, status: Optional[NotificationStatus] = None):
    """Obtener todas las notificaciones (admin)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, recipient_email, notification_type, subject, status, created_at, sent_at
            FROM notifications 
        """
        params = []
        
        if status:
            query += " WHERE status = %s"
            params.append(status.value)
            
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                "id": str(row[0]),
                "recipient_email": row[1],
                "notification_type": row[2],
                "subject": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "sent_at": row[6].isoformat() if row[6] else None
            })
        
        cursor.close()
        conn.close()
        
        return {"notifications": notifications, "total": len(notifications)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "MicroPay Notifications Service", 
        "status": "running",
        "endpoints": {
            "POST /notifications/send": "Enviar notificación personalizada",
            "POST /notifications/registration": "Notificación de registro",
            "POST /notifications/payment": "Notificación de pago",
            "POST /notifications/transaction": "Notificación de transacción",
            "GET /notifications/{user_id}": "Obtener notificaciones del usuario",
            "GET /notifications": "Obtener todas las notificaciones (admin)"
        },
        "version": "1.0.0",
        "config_status": {
            "aws_region": AWS_REGION,
            "ses_configured": "⚠️ Necesita email verificado en SES",
            "sns_configured": "⚠️ Mock mode (desarrollo)",
            "rds_configured": "✅" if all([RDS_HOST, RDS_PASS]) else "❌"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    