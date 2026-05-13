# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Создаем экземпляры расширений
db = SQLAlchemy()
login_manager = LoginManager()