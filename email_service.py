import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


def send_email(recipient: str, subject: str, message: str):
    msg = MIMEMultipart()
    msg["From"] = Config.EMAIL_ADDRESS
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
    server.starttls()
    server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
    server.sendmail(Config.EMAIL_ADDRESS, recipient, msg.as_string())
    server.quit()


def send_appointment_reminder(name: str, recipient: str, appointment_time_display: str, custom_message: str = ""):
    subject = "APPOINTMENT REMINDER"
    if custom_message:
        # Let the booker personalize their own message with these tokens.
        message = custom_message.replace("{name}", name).replace("{time}", appointment_time_display)
    else:
        message = f"{name}, YOUR APPOINTMENT TIME IS {appointment_time_display}. PLEASE COME ON TIME"
    send_email(recipient, subject, message)
