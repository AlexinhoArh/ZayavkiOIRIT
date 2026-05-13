# email_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import socks
import socket
import json # Импортируем json

# --- Чтение конфигурации из JSON ---
CONFIG_FILE_PATH = 'config.json' # Путь к файлу конфигурации
with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# --- Получение настроек ---
EMAIL_CONFIG = CONFIG['EMAIL']
EMAIL_SERVER = EMAIL_CONFIG['SERVER']
EMAIL_PORT = EMAIL_CONFIG['PORT']
EMAIL_USE_SSL = EMAIL_CONFIG['USE_SSL']
EMAIL_USE_TLS = EMAIL_CONFIG['USE_TLS']
EMAIL_USERNAME = EMAIL_CONFIG['USERNAME']
EMAIL_PASSWORD = EMAIL_CONFIG['PASSWORD']

PROXY_CONFIG = CONFIG['PROXY']
PROXY_ENABLED = PROXY_CONFIG['ENABLED']
PROXY_TYPE_VAL = PROXY_CONFIG['TYPE'] # Используем другое имя, чтобы не пересекалось с socks.TYPE
PROXY_HOST = PROXY_CONFIG['HOST']
PROXY_PORT = PROXY_CONFIG['PORT']
PROXY_USERNAME = PROXY_CONFIG['USERNAME']
PROXY_PASSWORD = PROXY_CONFIG['PASSWORD']

logger = logging.getLogger(__name__)

def send_email(to_email, subject, body, from_email=None, password=None, smtp_server=None, smtp_port=None, use_ssl=None, use_tls=None):
    """
    Отправляет электронное письмо.

    Args:
        to_email (str): Адрес получателя.
        subject (str): Тема письма.
        body (str): Текст письма.
        from_email (str, optional): Адрес отправителя (берется из конфига, если не указан).
        password (str, optional): Пароль отправителя (берется из конфига, если не указан).
        smtp_server (str, optional): SMTP сервер (берется из конфига, если не указан).
        smtp_port (int, optional): Порт SMTP сервера (берется из конфига, если не указан).
        use_ssl (bool, optional): Использовать SMTP_SSL (берется из конфига, если не указан).
        use_tls (bool, optional): Использовать STARTTLS (берется из конфига, если не указан).
    """
    if from_email is None:
        from_email = EMAIL_USERNAME
    if password is None:
        password = EMAIL_PASSWORD
    if smtp_server is None:
        smtp_server = EMAIL_SERVER
    if smtp_port is None:
        smtp_port = EMAIL_PORT
    if use_ssl is None:
        use_ssl = EMAIL_USE_SSL
    if use_tls is None:
        use_tls = EMAIL_USE_TLS

    original_socket = socket.socket
    try:
        if PROXY_ENABLED:
            proxy_type_map = {
                "SOCKS4": socks.SOCKS4,
                "SOCKS5": socks.SOCKS5,
                "HTTP": socks.HTTP
            }
            # Используем PROXY_TYPE_VAL вместо PROXY_TYPE
            proxy_type = proxy_type_map.get(PROXY_TYPE_VAL.upper())

            if proxy_type is None:
                logger.error(f"Unknown proxy type: {PROXY_TYPE_VAL}")
                return

            socks.set_default_proxy(
                proxy_type,
                PROXY_HOST,
                PROXY_PORT,
                username=PROXY_USERNAME,
                password=PROXY_PASSWORD
            )
            socket.socket = socks.socksocket
            logger.info(f"Socket patched for proxy: {PROXY_TYPE_VAL}://{PROXY_HOST}:{PROXY_PORT}")
        else:
            logger.info("Proxy is disabled. Using direct connection.")

        logger.info(f"Attempting to connect to SMTP server: {smtp_server}:{smtp_port} using {'SSL' if use_ssl else 'STARTTLS/plain'}.")
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            if use_tls: # Используем переменную из аргументов функции или конфига
                logger.info("Starting TLS encryption.")
                server.starttls()
        logger.info("Logging in to SMTP server.")
        server.login(from_email, password)
        logger.info("Creating message.")
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        text = msg.as_string()
        logger.info(f"Sending email to {to_email}.")
        server.sendmail(from_email, to_email, text)
        logger.info(f"Email sent successfully to {to_email}")
        server.quit()
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP Connect Error when connecting to {smtp_server}:{smtp_port} - Error: {e}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error for user {from_email} - Error: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"SMTP Recipients Refused - Error: {e}")
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"SMTP Sender Refused - Error: {e}")
    except smtplib.SMTPDataError as e:
        logger.error(f"SMTP Data Error - Error: {e}")
    except TimeoutError as e:
        logger.error(f"Timeout Error when connecting to {smtp_server}:{smtp_port} - Error: {e}")
    except OSError as e: # Общая ошибка ОС, включает WinError 10060
        logger.error(f"OS Error (likely network/connection issue via proxy) when connecting to {smtp_server}:{smtp_port} - Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when sending email to {to_email}: {e}")
    finally:
        if PROXY_ENABLED:
            socket.socket = original_socket
            logger.info("Original socket restored.")
        else:
            logger.info("No proxy was enabled, socket not changed.")

def send_new_request_notification(admin_email, request_number, requester_name):
    subject = "Новая заявка"
    body = f"Поступила новая заявка {request_number} от {requester_name}. Необходимо назначить исполнителя"
    send_email(admin_email, subject, body)

def send_assignment_notification(programmer_email, request_number, requester_name):
    subject = "Новая заявка"
    body = f"На Вас назначена заявка {request_number} от {requester_name}"
    send_email(programmer_email, subject, body)

def send_completion_notification(requester_email, request_number, programmer_name):
    subject = "Заявка выполнена"
    body = f"""Здравствуйте!

Ваша заявка {request_number} выполнена. Ответственный программист: {programmer_name}

Данное письмо было создано автоматически. Пожалуйста, не отвечайте на него. По всем вопросам обращайтесь в отдел ИРиТ"""
    send_email(requester_email, subject, body)

def send_rejection_notification(requester_email, request_number, rejector_name):
    """Отправляет уведомление составителю заявки об отклонении."""
    subject = "Заявка отклонена"
    body = f"""Здравствуйте!

Ваша заявка {request_number} была отклонена специалистом ОИРиТ {rejector_name}

Данное письмо было создано автоматически. Пожалуйста, не отвечайте на него. По всем вопросам обращайтесь в отдел ИРиТ"""
    send_email(requester_email, subject, body)
