# test_ldap3.py
import ssl
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE, Tls # Добавляем SUBTREE и Tls

# Настройки AD
AD_SERVER = 'ca-dc04.rosstat.local' # Ваш контроллер домена
AD_DOMAIN = 'rosstat.local'         # Ваш домен
AD_USER = '29.pishchukhinvs'      # Временный тестовый логин (например, ваш собственный)
AD_PASSWORD = 'dhfugfxrvjlt+H29'  # Пароль для тестового логина
AD_SEARCH_BASE = 'DC=rosstat,DC=local' # Уже нашли ранее

try:
    # Создаем сервер с обязательным SSL
    server = Server(AD_SERVER, get_info=ALL, use_ssl=True)

    # Создаем соединение с использованием SIMPLE аутентификации
    # user должен быть в формате UPN: username@domain.com
    user_upn = f'{AD_USER}@{AD_DOMAIN}' # Пример: 'ivanov@rosstat.local'
    print(f"Попытка подключения с UPN: {user_upn}")
    conn = Connection(server, user=user_upn, password=AD_PASSWORD, authentication=SIMPLE)

    # Открываем соединение
    if conn.bind():
        print("Успешное подключение к AD с SIMPLE аутентификацией!")
        print(f"Сервер info: {server.info}")
        print(f"Схема: {server.schema}")

        # Попробуем найти себя
        search_filter = f'(sAMAccountName={AD_USER})'
        conn.search(search_base=AD_SEARCH_BASE,
                    search_filter=search_filter,
                    search_scope=SUBTREE, # Теперь SUBTREE определена
                    attributes=['displayName', 'mail', 'memberOf'])

        if conn.entries:
            user_entry = conn.entries[0]
            print(f"\nНайден пользователь: {user_entry}")
            print(f"displayName: {user_entry.displayName.value}")
            print(f"mail: {user_entry.mail.value if user_entry.mail.value else 'Не указан'}")
        else:
            print(f"Пользователь '{AD_USER}' не найден в '{AD_SEARCH_BASE}'.")

        conn.unbind()
    else:
        print("Ошибка подключения к AD с SIMPLE аутентификацией.")
        print(f"Детали ошибки: {conn.result}")
        # Попробуем также вывести диагностическое сообщение сервера
        diagnostic_msg = conn.result.get('message', '')
        if diagnostic_msg:
            print(f"Сообщение сервера: {diagnostic_msg}")

except Exception as e:
    print(f"Произошла ошибка при установке соединения: {e}")
