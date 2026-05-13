# auth.py
# --- Удаляем инициализацию login_manager и db из auth.py ---
# from flask_login import LoginManager, login_user, logout_user, current_user
# from models import User, db # <-- Убираем db из импорта здесь
from flask_login import login_user, logout_user, current_user # <-- Импортируем только функции
from models import User # <-- Импортируем только модели
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
import json # Импортируем json
import re # Для проверки email

# --- Удаляем строку инициализации ---
# login_manager = LoginManager()
# login_manager.login_view = 'login'
# login_manager.login_message = 'Пожалуйста, войдите для доступа к странице.'

# --- Читаем конфигурацию из JSON ---
CONFIG_FILE_PATH = 'config.json' # Путь к файлу конфигурации
with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# --- Извлекаем настройки AD ---
AD_CONFIG = CONFIG['ACTIVE_DIRECTORY']
AD_SERVER = AD_CONFIG['SERVER']
AD_DOMAIN = AD_CONFIG['DOMAIN']
AD_SEARCH_BASE = AD_CONFIG['SEARCH_BASE']

# --- Удаляем функцию load_user из auth.py ---
# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))

def is_valid_email(email):
    """Проверяет, является ли строка корректным email адресом."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def authenticate_user(username, password):
    """
    Проверяет пользователя в AD через ldap3 и возвращает объект User из БД.
    Если пользователя нет в БД, создаёт с ролью 'economist'.
    """
    try:
        # --- Используем локальные переменные AD_SERVER, AD_DOMAIN, AD_SEARCH_BASE ---
        server = Server(AD_SERVER, get_info=ALL, use_ssl=True)

        user_upn = f'{username}@{AD_DOMAIN}'
        conn = Connection(server, user=user_upn, password=password, authentication=SIMPLE)

        if conn.bind():
            print(f"Успешная аутентификация в AD для пользователя: {username}")

            search_filter = f'(sAMAccountName={username})'
            conn.search(
                search_base=AD_SEARCH_BASE, # --- Используем локальную переменную ---
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['displayName', 'mail', 'sAMAccountName', 'department', 'distinguishedName']
            )

            if conn.entries:
                ad_user = conn.entries[0]

                department = ad_user.department.value if ad_user.department.value else ''
                dn_str = ad_user.distinguishedName.value
                ou_parts = []
                for part in dn_str.split(','):
                    part = part.strip()
                    if part.upper().startswith('OU='):
                        ou_parts.append(part[3:])
                department_from_ou = ou_parts[0] if ou_parts else ''
                final_department = department if department else department_from_ou

                # Используем email из AD, если он есть
                ad_email = ad_user.mail.value if ad_user.mail.value else ''

                user_info = {
                    'username': ad_user.sAMAccountName.value,
                    'name': ad_user.displayName.value or username,
                    'email': ad_email, # Сохраняем email из AD
                    'department': final_department
                }
                print(f"Найден пользователь в AD: {user_info}")
            else:
                print(f"Пользователь '{username}' найден в AD (аутентификация прошла), но не найден в SEARCH_BASE '{AD_SEARCH_BASE}'.") # --- Используем локальную переменную ---
                conn.unbind()
                return None

            conn.unbind()

            # --- Поиск/создание/обновление пользователя в локальной БД Flask ---
            # --- Предполагаем, что db будет доступна из models ---
            from extensions import db # Импортируем db внутри функции, чтобы избежать циклической зависимости на старте
            user_db = User.query.filter_by(username=username).first()
            if user_db:
                print(f"Пользователь '{username}' найден в локальной БД.")
                update_needed = False
                if user_db.name != user_info['name']:
                    user_db.name = user_info['name']
                    update_needed = True
                if user_db.department != user_info['department']:
                    user_db.department = user_info['department']
                    update_needed = True
                # Обновляем email из AD, если он был, но не перезаписываем, если пользователь сам его указал и он отличается
                # Пусть будет приоритет у значения в БД, если оно есть и не совпадает с AD
                if user_db.email != user_info['email'] and not user_db.email:
                    # Обновляем email из AD только если в БД он пуст
                    user_db.email = user_info['email']
                    update_needed = True

                if update_needed:
                    db.session.commit()
                    print(f"Информация о пользователе '{username}' в БД обновлена.")
            else:
                print(f"Пользователь '{username}' аутентифицирован в AD, но не найден в локальной БД Flask. Создаём с ролью 'economist'...")
                # Создаём нового пользователя с информацией из AD и ролью 'economist'
                user_db = User(
                    username=user_info['username'],
                    name=user_info['name'],
                    role='economist', # Автоматически присваиваем роль 'economist'
                    department=user_info['department'],
                    email=user_info['email'] # Сохраняем email из AD
                )
                db.session.add(user_db)
                db.session.commit()
                print(f"Пользователь '{username}' создан в локальной БД.")

            # Проверяем, заполнен ли email
            # Если email пуст, возвращаем специальный маркер, чтобы показать форму
            if not user_db.email:
                # Возвращаем кортеж: (user_object, needs_email_input)
                return (user_db, True) # True означает, что нужно ввести email

            return user_db # Возвращаем объект пользователя, если email заполнен

        else:
            print(f"Ошибка аутентификации в AD для пользователя '{username}': {conn.result}")
            return None

    except Exception as e:
        print(f"Ошибка при проверке AD (ldap3): {e}")
        return None

def login_user_func(username, password):
    result = authenticate_user(username, password)
    if result:
        # Проверяем, является ли результат кортежем (нужен email)
        if isinstance(result, tuple):
            user_db, needs_email = result
            if needs_email:
                # Возвращаем пользователя, которому нужен email
                # Флаг нужен, чтобы в app.py направить на форму
                return {'user': user_db, 'needs_email': True}
        else:
            # Это обычный пользователь с заполненным email
            user_db = result
            if user_db and user_db.role:
                login_user(user_db)
                print(f"Пользователь '{user_db.username}' ({user_db.name}, роль: {user_db.role}, отдел: {user_db.department}) вошел в систему.")
                return {'user': user_db, 'needs_email': False}
    print(f"Неудачная попытка входа для пользователя '{username}' или требуется ввод email.")
    return {'user': None, 'needs_email': False}
