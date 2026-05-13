# email_sender.py
"""
Модуль отправки email-уведомлений.

Обеспечивает отправку электронных писем через SMTP сервер с поддержкой:
- SSL/TLS шифрования
- Проксирования соединений (SOCKS4, SOCKS5, HTTP)
- Различных типов уведомлений системы заявок

Типы уведомлений:
- Новая заявка (для администраторов)
- Назначение заявки (для программистов)
- Выполнение заявки (для экономистов)
- Отклонение заявки (для экономистов)

Примеры:
    Отправка простого письма:
        send_email('user@example.com', 'Тема', 'Текст письма')
    
    Уведомление о новой заявке:
        send_new_request_notification('admin@example.com', '2024-1', 'Иванов И.И.')
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import socks
import socket
import json
from typing import Optional

# --- Константы конфигурации ---
CONFIG_FILE_PATH = 'config.json'


def _load_config() -> dict:
    """Загружает конфигурацию из JSON файла."""
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


# Загрузка настроек
_CONFIG = _load_config()
_EMAIL_CONFIG = _CONFIG['EMAIL']
_PROXY_CONFIG = _CONFIG['PROXY']

# Настройки SMTP сервера
EMAIL_SERVER = _EMAIL_CONFIG['SERVER']
EMAIL_PORT = _EMAIL_CONFIG['PORT']
EMAIL_USE_SSL = _EMAIL_CONFIG['USE_SSL']
EMAIL_USE_TLS = _EMAIL_CONFIG['USE_TLS']
EMAIL_USERNAME = _EMAIL_CONFIG['USERNAME']
EMAIL_PASSWORD = _EMAIL_CONFIG['PASSWORD']

# Настройки прокси
PROXY_ENABLED = _PROXY_CONFIG['ENABLED']
PROXY_TYPE_VAL = _PROXY_CONFIG['TYPE']
PROXY_HOST = _PROXY_CONFIG['HOST']
PROXY_PORT = _PROXY_CONFIG['PORT']
PROXY_USERNAME = _PROXY_CONFIG['USERNAME']
PROXY_PASSWORD = _PROXY_CONFIG['PASSWORD']

# Логгер модуля
logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    password: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    use_ssl: Optional[bool] = None,
    use_tls: Optional[bool] = None
) -> None:
    """
    Отправляет электронное письмо через SMTP сервер.
    
    Поддерживает подключение через прокси-сервер и различные методы
    шифрования (SSL, TLS).
    
    Args:
        to_email: Адрес получателя
        subject: Тема письма
        body: Текст письма (plain text)
        from_email: Адрес отправителя (по умолчанию из конфига)
        password: Пароль SMTP (по умолчанию из конфига)
        smtp_server: SMTP сервер (по умолчанию из конфига)
        smtp_port: Порт SMTP (по умолчанию из конфига)
        use_ssl: Использовать SSL (по умолчанию из конфига)
        use_tls: Использовать STARTTLS (по умолчанию из конфига)
        
    Примеры:
        send_email('user@example.com', 'Тест', 'Привет!')
        
        send_email(
            'user@example.com',
            'Важно',
            'Срочное сообщение',
            smtp_server='smtp.example.com',
            smtp_port=587,
            use_tls=True
        )
    """
    # Применение значений по умолчанию из конфигурации
    from_email = from_email or EMAIL_USERNAME
    password = password or EMAIL_PASSWORD
    smtp_server = smtp_server or EMAIL_SERVER
    smtp_port = smtp_port or EMAIL_PORT
    use_ssl = use_ssl if use_ssl is not None else EMAIL_USE_SSL
    use_tls = use_tls if use_tls is not None else EMAIL_USE_TLS
    
    original_socket = socket.socket
    
    try:
        # Настройка прокси при необходимости
        if PROXY_ENABLED:
            proxy_type_map = {
                "SOCKS4": socks.SOCKS4,
                "SOCKS5": socks.SOCKS5,
                "HTTP": socks.HTTP
            }
            proxy_type = proxy_type_map.get(PROXY_TYPE_VAL.upper())
            
            if proxy_type is None:
                logger.error(f"Неизвестный тип прокси: {PROXY_TYPE_VAL}")
                return
            
            socks.set_default_proxy(
                proxy_type,
                PROXY_HOST,
                PROXY_PORT,
                username=PROXY_USERNAME,
                password=PROXY_PASSWORD
            )
            socket.socket = socks.socksocket
            logger.info(f"Прокси включен: {PROXY_TYPE_VAL}://{PROXY_HOST}:{PROXY_PORT}")
        else:
            logger.info("Прокси отключен. Прямое соединение.")
        
        # Подключение к SMTP серверу
        logger.info(f"Подключение к SMTP серверу {smtp_server}:{smtp_port}")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            if use_tls:
                logger.info("Включение TLS шифрования")
                server.starttls()
        
        # Аутентификация
        logger.info("Аутентификация на SMTP сервере")
        server.login(from_email, password)
        
        # Создание и отправка сообщения
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        logger.info(f"Отправка письма получателю {to_email}")
        server.sendmail(from_email, to_email, msg.as_string())
        logger.info(f"Письмо успешно отправлено {to_email}")
        
        server.quit()
        
    except smtplib.SMTPConnectError as e:
        logger.error(f"Ошибка подключения к SMTP серверу {smtp_server}:{smtp_port}: {e}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Ошибка аутентификации SMTP для пользователя {from_email}: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"Получатель отвергнут SMTP сервером: {e}")
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"Отправитель отвергнут SMTP сервером: {e}")
    except smtplib.SMTPDataError as e:
        logger.error(f"Ошибка данных SMTP: {e}")
    except TimeoutError as e:
        logger.error(f"Таймаут подключения к {smtp_server}:{smtp_port}: {e}")
    except OSError as e:
        logger.error(f"Ошибка ОС (проблемы сети/прокси) при подключении к {smtp_server}:{smtp_port}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке письма {to_email}: {e}")
    finally:
        # Восстановление оригинального сокета
        if PROXY_ENABLED:
            socket.socket = original_socket
            logger.info("Оригинальный сокет восстановлен")


def send_new_request_notification(admin_email: str, request_number: str, requester_name: str) -> None:
    """
    Отправляет уведомление администратору о новой заявке.
    
    Args:
        admin_email: Email администратора
        request_number: Номер заявки
        requester_name: Имя заявителя
        
    Примеры:
        send_new_request_notification('admin@example.com', '2024-1', 'Иванов И.И.')
    """
    subject = "Новая заявка"
    body = f"Поступила новая заявка {request_number} от {requester_name}. Необходимо назначить исполнителя"
    send_email(admin_email, subject, body)


def send_assignment_notification(programmer_email: str, request_number: str, requester_name: str) -> None:
    """
    Отправляет уведомление программисту о назначении заявки.
    
    Args:
        programmer_email: Email программиста
        request_number: Номер заявки
        requester_name: Имя заявителя
        
    Примеры:
        send_assignment_notification('dev@example.com', '2024-1', 'Иванов И.И.')
    """
    subject = "Новая заявка"
    body = f"На Вас назначена заявка {request_number} от {requester_name}"
    send_email(programmer_email, subject, body)


def send_completion_notification(requester_email: str, request_number: str, programmer_name: str) -> None:
    """
    Отправляет уведомление заявителю о выполнении заявки.
    
    Args:
        requester_email: Email заявителя
        request_number: Номер заявки
        programmer_name: Имя программиста
        
    Примеры:
        send_completion_notification('user@example.com', '2024-1', 'Петров П.П.')
    """
    subject = "Заявка выполнена"
    body = f"""Здравствуйте!

Ваша заявка {request_number} выполнена. Ответственный программист: {programmer_name}

Данное письмо было создано автоматически. Пожалуйста, не отвечайте на него. По всем вопросам обращайтесь в отдел ИРиТ"""
    send_email(requester_email, subject, body)


def send_rejection_notification(requester_email: str, request_number: str, rejector_name: str) -> None:
    """
    Отправляет уведомление заявителю об отклонении заявки.
    
    Args:
        requester_email: Email заявителя
        request_number: Номер заявки
        rejector_name: Имя отклонившего специалиста
        
    Примеры:
        send_rejection_notification('user@example.com', '2024-1', 'Администратор')
    """
    subject = "Заявка отклонена"
    body = f"""Здравствуйте!

Ваша заявка {request_number} была отклонена специалистом ОИРиТ {rejector_name}

Данное письмо было создано автоматически. Пожалуйста, не отвечайте на него. По всем вопросам обращайтесь в отдел ИРиТ"""
    send_email(requester_email, subject, body)
