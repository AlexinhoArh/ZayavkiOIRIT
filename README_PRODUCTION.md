# Инструкция по запуску в продакшен-режиме (Windows)

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 2. Настройка конфигурации

Отредактируйте файл `config.json`:
- Замените `SECRET_KEY` на уникальный безопасный ключ
- Обновите параметры подключения к базе данных
- Настройте параметры Active Directory
- Укажите корректные настройки SMTP для отправки email
- При необходимости настройте прокси

**Важно:** Не храните пароли в репозитории! Используйте переменные окружения или защищённые хранилища.

## 3. Запуск через Waitress (рекомендуется для Windows)

Waitress — это production-ready WSGI сервер для Python, который отлично работает на Windows.

### Вариант A: Прямой запуск через командную строку

```bash
waitress-serve --host=0.0.0.0 --port=1313 app:app
```

### Вариант B: Создание скрипта запуска

Создайте файл `run_production.py`:

```python
from waitress import serve
from app import app

if __name__ == '__main__':
    print("Запуск приложения в продакшен-режиме...")
    print("Сервер доступен по адресу: http://0.0.0.0:1313")
    serve(app, host='0.0.0.0', port=1313, threads=8)
```

Запуск:
```bash
python run_production.py
```

### Вариант C: Запуск как служба Windows

Используйте NSSM (Non-Sucking Service Manager) или WinSW для запуска приложения как службы Windows.

#### С помощью NSSM:

1. Скачайте NSSM: https://nssm.cc/download
2. Распакуйте и откройте командную строку от имени администратора
3. Выполните команды:

```cmd
nssm install ZayavkiOIRIT "C:\Python\python.exe" "C:\path\to\run_production.py"
nssm set ZayavkiOIRIT DisplayName "Система управления заявками ОИРИТ"
nssm set ZayavkiOIRIT Description "WSGI сервер для приложения заявок"
nssm set ZayavkiOIRIT Start SERVICE_AUTO_START
nssm start ZayavkiOIRIT
```

## 4. Настройка брандмауэра

Откройте порт 1313 в брандмауэре Windows:

```cmd
netsh advfirewall firewall add rule name="ZayavkiOIRIT" dir=in action=allow protocol=TCP localport=1313
```

## 5. Настройка логгирования

Добавьте в начало файла `app.py` настройку логгирования:

```python
import logging
from logging.handlers import RotatingFileHandler
import os

# Создание директории для логов
if not os.path.exists('logs'):
    os.mkdir('logs')

# Настройка ротации логов
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Запуск приложения в продакшен-режиме')
```

## 6. Рекомендации по безопасности

1. **HTTPS**: Настройте обратный прокси через IIS или nginx для HTTPS
2. **Пароли**: Используйте переменные окружения для чувствительных данных
3. **Брандмауэр**: Ограничьте доступ к порту только доверенным IP
4. **Обновления**: Регулярно обновляйте зависимости
5. **Резервное копирование**: Настройте регулярное резервное копирование БД

## 7. Мониторинг

Для мониторинга работы приложения рекомендуется:
- Настроить мониторинг логов
- Использовать Windows Performance Monitor
- Настроить уведомления об ошибках

## 8. Отладка проблем

Если приложение не запускается:
1. Проверьте логи в файле `logs/app.log`
2. Убедитесь, что все зависимости установлены
3. Проверьте доступность сервера БД и LDAP
4. Убедитесь, что порт 1313 не занят другим приложением

```cmd
netstat -ano | findstr :1313
```
