"""
Скрипт для запуска приложения в продакшен-режиме через Waitress.

Использование:
    python run_production.py

Для настройки параметров отредактируйте константы HOST, PORT и THREADS.
"""

from waitress import serve
from app import app

# Параметры сервера
HOST = '0.0.0.0'  # Слушать все интерфейсы
PORT = 1313       # Порт приложения
THREADS = 8       # Количество потоков обработки запросов

if __name__ == '__main__':
    print("=" * 60)
    print("Запуск системы управления заявками ОИРИТ")
    print("Режим: ПРОДАКШЕН (Waitress WSGI Server)")
    print("=" * 60)
    print(f"Адрес сервера: http://{HOST}:{PORT}")
    print(f"Количество потоков: {THREADS}")
    print("-" * 60)
    print("Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    try:
        serve(app, host=HOST, port=PORT, threads=THREADS)
    except KeyboardInterrupt:
        print("\n\nСервер остановлен пользователем.")
    except Exception as e:
        print(f"\n\nОшибка при запуске сервера: {e}")
        raise
