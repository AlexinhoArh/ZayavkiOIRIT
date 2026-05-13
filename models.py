# models.py
"""
Модуль моделей данных приложения.

Содержит SQLAlchemy-модели для представления сущностей предметной области:
- User: Пользователи системы (экономисты, программисты, администраторы)
- Request: Заявки на выполнение работ
- TipZayavki: Типы заявок (классификатор)

Модели используют расширение Flask-SQLAlchemy для ORM-маппинга
и Flask-Login для аутентификации пользователей.

Примеры:
    Создание нового пользователя:
        user = User(username='ivanov', name='Иван Иванов', 
                    role='economist', department='Отдел статистики')
        db.session.add(user)
        db.session.commit()
    
    Получение всех заявок экономиста:
        requests = user.created_requests
    
    Назначение программиста на заявку:
        request.programmer_id = programmer.id
        request.status = 'В работе'
"""

from flask_login import UserMixin
from datetime import datetime
from typing import Optional, List

from extensions import db


class TipZayavki(db.Model):
    """
    Модель типа заявки.
    
    Классификатор видов работ по заявкам (например: "выборка из БД",
    "программирование", "DocMaker"). Используется для категоризации
    и фильтрации заявок.
    
    Атрибуты:
        id (int): Первичный ключ
        nazvaniye (str): Название типа заявки (уникальное)
        requests (List[Request]): Связь один-ко-многим с заявками
    
    Примеры:
        tip = TipZayavki(nazvaniye="выборка из БД")
        db.session.add(tip)
    """
    
    __tablename__ = 'tip_zayavki'

    id = db.Column(db.Integer, primary_key=True)
    nazvaniye = db.Column(db.String(255), nullable=False, unique=True)

    # Связь один-ко-многим: один тип заявки может быть у многих заявок
    requests = db.relationship('Request', backref='tip_obj', lazy=True)

    def __repr__(self) -> str:
        """Возвращает строковое представление типа заявки."""
        return f'<TipZayavki {self.nazvaniye}>'


class User(UserMixin, db.Model):
    """
    Модель пользователя системы.
    
    Представляет сотрудников организации, работающих с системой:
    - Экономисты: создают заявки
    - Программисты: выполняют заявки
    - Администраторы: управляют распределением заявок
    
    Интегрируется с Flask-Login через наследование UserMixin.
    Данные синхронизируются с Active Directory при входе.
    
    Атрибуты:
        id (int): Первичный ключ
        username (str): Учетная запись AD (уникальная)
        name (str): Отображаемое имя пользователя
        role (str): Роль ('economist', 'programmer', 'admin')
        department (str): Отдел сотрудника
        email (str): Email для уведомлений
        created_requests (List[Request]): Заявки, созданные пользователем
        assigned_requests (List[Request]): Заявки, назначенные пользователю
    
    Примеры:
        user = User.query.filter_by(username='ivanov').first()
        if user.role == 'admin':
            # Доступ к функциям администрирования
    """
    
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(200))
    email = db.Column(db.String(254))

    # Связи с заявками
    # foreign_keys явно указывает на поля в модели Request
    created_requests = db.relationship(
        'Request', 
        foreign_keys='Request.economist_id', 
        backref='economist_user',
        lazy=True
    )
    assigned_requests = db.relationship(
        'Request', 
        foreign_keys='Request.programmer_id', 
        backref='programmer_user',
        lazy=True
    )

    def __repr__(self) -> str:
        """Возвращает строковое представление пользователя."""
        return f'<User {self.username} ({self.name})>'


class Request(db.Model):
    """
    Модель заявки на выполнение работ.
    
    Основная сущность системы, представляющая заказ на выполнение
    определенной работы (выгрузка данных, программирование и т.д.).
    
    Жизненный цикл заявки:
        1. "На рассмотрении" - создана экономистом
        2. "В работе" - назначен программист
        3. "Выполнено" - работа завершена
        4. "Отклонено" - отклонена администратором/программистом
    
    Атрибуты:
        id (int): Первичный ключ
        zayavka_path (str): Путь к файлу заявки (опционально)
        date_zagruzki (datetime): Дата создания/загрузки
        nom_zayavki (str): Уникальный номер заявки (формат: ГОД-НОМЕР)
        forma (str): Форма предоставления данных
        economist_id (int): ID экономиста-создателя
        programmer_id (int): ID назначенного программиста
        tip_zayavki_id (int): ID типа заявки
        status (str): Текущий статус
        date_ready (datetime): Дата завершения
        primechanie (str): Примечания программиста
        otdel (str): Отдел заказчика
        data_zapolneniya (datetime): Дата заполнения
        srok_vypolneniya (datetime): Срок выполнения
        telefon_zakazchika (str): Телефон заказчика
        cel_zakaza (str): Цель заказа
        dop_informaciya (str): Дополнительная информация
        razmeshenie_rezultatov (str): Требования к размещению результатов
        formulirovka_zakaza (str): Подробное описание задачи
        spisok_poley (str): Список требуемых полей
        por_ydok_sort (str): Порядок сортировки данных
    
    Примеры:
        req = Request(
            nom_zayavki="2024-1",
            forma="Excel",
            economist_id=1,
            srok_vypolneniya=datetime(2024, 12, 31),
            cel_zakaza="Анализ данных"
        )
        db.session.add(req)
    """
    
    __tablename__ = 'request'

    id = db.Column(db.Integer, primary_key=True)
    zayavka_path = db.Column(db.String(500))
    date_zagruzki = db.Column(db.DateTime, default=datetime.utcnow)
    nom_zayavki = db.Column(db.String(255), nullable=False)
    forma = db.Column(db.String(255))
    economist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    programmer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tip_zayavki_id = db.Column(db.Integer, db.ForeignKey('tip_zayavki.id'))
    status = db.Column(db.String(50), default='На рассмотрении')
    date_ready = db.Column(db.DateTime)
    primechanie = db.Column(db.Text)

    # Детали заявки
    otdel = db.Column(db.String(200))
    data_zapolneniya = db.Column(db.DateTime, default=datetime.utcnow)
    srok_vypolneniya = db.Column(db.DateTime)
    telefon_zakazchika = db.Column(db.String(50))
    cel_zakaza = db.Column(db.String(300))
    dop_informaciya = db.Column(db.String(1000))
    razmeshenie_rezultatov = db.Column(db.String(500))
    formulirovka_zakaza = db.Column(db.String(5000))
    spisok_poley = db.Column(db.String(500))
    por_ydok_sort = db.Column(db.String(500))

    def __repr__(self) -> str:
        """Возвращает строковое представление заявки."""
        return f'<Request {self.nom_zayavki} ({self.status})>'