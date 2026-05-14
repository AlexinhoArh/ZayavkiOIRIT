# extensions.py
"""
Модуль для инициализации расширений Flask.

Этот модуль содержит экземпляры расширений Flask-SQLAlchemy и Flask-Login,
которые используются во всем приложении. Разделение инициализации расширений
от создания приложения позволяет избежать циклических импортов.

Примеры:
    Для использования в других модулях:
        from extensions import db, login_manager
        
        # В factory функции приложения:
        def create_app():
            app = Flask(__name__)
            db.init_app(app)
            login_manager.init_app(app)
            return app
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Инициализация расширения работы с базой данных
# Используется для ORM-моделирования и управления сессиями БД
db = SQLAlchemy()

# Инициализация менеджера аутентификации пользователей
# Управляет сессиями пользователей, загрузкой и проверкой прав доступа
login_manager = LoginManager()