# auth.py
"""
Модуль аутентификации пользователей.

Обеспечивает интеграцию с Active Directory для проверки учетных данных
пользователей и автоматическую синхронизацию данных пользователей между
AD и локальной базой данных приложения.

Функциональность:
- Аутентификация через LDAP с использованием ldap3
- Автоматическое создание пользователей в БД при первом входе
- Синхронизация данных пользователя (имя, отдел, email)
- Проверка и запрос email у новых пользователей
- Интеграция с Flask-Login

Примеры:
    Аутентификация пользователя:
        result = login_user_func('username', 'password')
        if result['user'] and not result['needs_email']:
            # Успешный вход
"""

from flask_login import login_user, current_user
from models import User
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
import json
import re
from typing import Dict, Any, Optional, Tuple

from extensions import db

# --- Константы конфигурации ---
CONFIG_FILE_PATH = 'config.json'


def _load_config() -> dict:
    """Загружает конфигурацию из JSON файла."""
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


# Загрузка настроек Active Directory
_CONFIG = _load_config()
_AD_CONFIG = _CONFIG['ACTIVE_DIRECTORY']
AD_SERVER = _AD_CONFIG['SERVER']
AD_DOMAIN = _AD_CONFIG['DOMAIN']
AD_SEARCH_BASE = _AD_CONFIG['SEARCH_BASE']


def is_valid_email(email: str) -> bool:
    """
    Проверяет корректность формата email адреса.
    
    Args:
        email: Строка email адреса для проверки
        
    Returns:
        True если email корректен, False иначе
        
    Примеры:
        >>> is_valid_email('test@example.com')
        True
        >>> is_valid_email('invalid-email')
        False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def authenticate_user(username: str, password: str) -> Optional[Tuple[User, bool]]:
    """
    Аутентифицирует пользователя в Active Directory и возвращает объект User из БД.
    
    Выполняет следующие шаги:
    1. Подключение к AD серверу через LDAP
    2. Проверка учетных данных пользователя
    3. Получение информации о пользователе из AD
    4. Поиск/создание/обновление пользователя в локальной БД
    5. Проверка наличия email
    
    Args:
        username: Имя пользователя (sAMAccountName в AD)
        password: Пароль пользователя
        
    Returns:
        Кортеж (User, needs_email) где:
        - User: Объект пользователя из БД или None при ошибке
        - needs_email: True если требуется ввод email, False иначе
        
    Примеры:
        user, needs_email = authenticate_user('ivanov', 'password123')
        if user and needs_email:
            # Перенаправить на страницу ввода email
    """
    try:
        # Подключение к серверу Active Directory
        server = Server(AD_SERVER, get_info=ALL, use_ssl=True)
        user_upn = f'{username}@{AD_DOMAIN}'
        
        conn = Connection(server, user=user_upn, password=password, authentication=SIMPLE)
        
        if not conn.bind():
            print(f"Ошибка аутентификации в AD для пользователя '{username}': {conn.result}")
            return None
        
        print(f"Успешная аутентификация в AD для пользователя: {username}")
        
        # Поиск пользователя в AD
        search_filter = f'(sAMAccountName={username})'
        conn.search(
            search_base=AD_SEARCH_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['displayName', 'mail', 'sAMAccountName', 'department', 'distinguishedName']
        )
        
        if not conn.entries:
            print(f"Пользователь '{username}' не найден в SEARCH_BASE '{AD_SEARCH_BASE}'")
            conn.unbind()
            return None
        
        ad_user = conn.entries[0]
        
        # Извлечение информации из AD
        department = ad_user.department.value if ad_user.department.value else ''
        dn_str = ad_user.distinguishedName.value
        
        # Извлечение отдела из distinguished name
        ou_parts = []
        for part in dn_str.split(','):
            part = part.strip()
            if part.upper().startswith('OU='):
                ou_parts.append(part[3:])
        department_from_ou = ou_parts[0] if ou_parts else ''
        final_department = department if department else department_from_ou
        
        # Email из AD
        ad_email = ad_user.mail.value if ad_user.mail.value else ''
        
        user_info = {
            'username': ad_user.sAMAccountName.value,
            'name': ad_user.displayName.value or username,
            'email': ad_email,
            'department': final_department
        }
        print(f"Найден пользователь в AD: {user_info}")
        
        conn.unbind()
        
        # Синхронизация с локальной БД
        user_db = User.query.filter_by(username=username).first()
        
        if user_db:
            # Обновление существующего пользователя
            print(f"Пользователь '{username}' найден в локальной БД.")
            update_needed = False
            
            if user_db.name != user_info['name']:
                user_db.name = user_info['name']
                update_needed = True
                
            if user_db.department != user_info['department']:
                user_db.department = user_info['department']
                update_needed = True
            
            # Обновление email только если в БД он пуст
            if not user_db.email and user_info['email']:
                user_db.email = user_info['email']
                update_needed = True
            
            if update_needed:
                db.session.commit()
                print(f"Информация о пользователе '{username}' обновлена.")
        else:
            # Создание нового пользователя
            print(f"Создание нового пользователя '{username}' в БД...")
            user_db = User(
                username=user_info['username'],
                name=user_info['name'],
                role='economist',  # Роль по умолчанию
                department=user_info['department'],
                email=user_info['email']
            )
            db.session.add(user_db)
            db.session.commit()
            print(f"Пользователь '{username}' создан в БД.")
        
        # Проверка необходимости ввода email
        if not user_db.email:
            return (user_db, True)
        
        return (user_db, False)
        
    except Exception as e:
        print(f"Ошибка при проверке AD: {e}")
        return None


def login_user_func(username: str, password: str) -> Dict[str, Any]:
    """
    Выполняет вход пользователя в систему.
    
    Обертка над authenticate_user, которая интегрируется с Flask-Login.
    
    Args:
        username: Имя пользователя
        password: Пароль пользователя
        
    Returns:
        Словарь с ключами:
        - 'user': Объект User или None
        - 'needs_email': Требуется ли ввод email
        
    Примеры:
        result = login_user_func('ivanov', 'password123')
        if result['user']:
            if result['needs_email']:
                # Перенаправить на страницу ввода email
            else:
                # Пользователь уже вошел через login_user()
    """
    result = authenticate_user(username, password)
    
    if result:
        user_db, needs_email = result
        
        if needs_email:
            return {'user': user_db, 'needs_email': True}
        
        if user_db and user_db.role:
            login_user(user_db)
            print(f"Вход выполнен: {user_db.username} ({user_db.name}, "
                  f"роль: {user_db.role}, отдел: {user_db.department})")
            return {'user': user_db, 'needs_email': False}
    
    print(f"Неудачная попытка входа для пользователя '{username}'")
    return {'user': None, 'needs_email': False}
