from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
import logging

# Logger setup taake terminal mein pata chale masla kya hai
logger = logging.getLogger("uvicorn")

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    # ✅ FIX: Gmail ke liye STARTTLS true aur SSL false hona chahiye
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email_to: str, otp: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 400px; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
        <h2 style="color: #6A1FB0;">NOVA AI Assistant</h2>
        <p>Hi,</p>
        <p>Your verification code is:</p>
        <div style="background: #f4f4f4; padding: 10px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #4A1B7B;">
            {otp}
        </div>
        <p>This OTP is valid for 5 minutes. Please do not share it with anyone.</p>
    </div>
    """

    message = MessageSchema(
        subject="NOVA Assistant - Verification Code",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"✅ OTP Email sent to {email_to}")
    except Exception as e:
        logger.error(f"❌ Failed to send email: {str(e)}")
        # Backend ko crash hone se bachane ke liye hum error raise nahi kar rahe
        # lekin log mein error print kar rahe hain