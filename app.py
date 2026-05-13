# app.py
import json
import urllib.parse
import logging
from datetime import datetime, date

import pytz
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

# Импортируем расширения из отдельного файла
from extensions import db, login_manager

from email_sender import (
    send_new_request_notification,
    send_assignment_notification,
    send_completion_notification,
    send_rejection_notification
)

# --- Чтение конфигурации из JSON ---
CONFIG_FILE_PATH = 'config.json'
try:
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    print(f"Ошибка: Файл конфигурации {CONFIG_FILE_PATH} не найден!")
    exit(1)
except json.JSONDecodeError:
    print(f"Ошибка: Файл конфигурации {CONFIG_FILE_PATH} содержит некорректный JSON!")
    exit(1)

# --- Создание Flask приложения ---
app = Flask(__name__)
app.config['SECRET_KEY'] = CONFIG['SECRET_KEY']

# --- Настройка подключения к базе данных ---
DB_CONFIG = CONFIG['DATABASE']
DB_USERNAME = DB_CONFIG['USERNAME']
DB_PASSWORD = DB_CONFIG['PASSWORD']
ENCODED_DB_PASSWORD = urllib.parse.quote_plus(DB_PASSWORD)
SQLALCHEMY_DATABASE_URI = (
    f'mssql+pyodbc://{DB_USERNAME}:{ENCODED_DB_PASSWORD}'
    f'@{DB_CONFIG["SERVER"]}/{DB_CONFIG["NAME"]}?driver=ODBC+Driver+17+for+SQL+Server'
)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Инициализация расширений с приложением ---
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к системе.'

# --- Глобальные переменные ---
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
ADMIN_USERNAME = CONFIG['ADMIN_USERNAME']

# --- Импорт моделей ПОСЛЕ инициализации db ---
from models import User, Request, TipZayavki


# --- Функция загрузки пользователя для Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Вспомогательные функции ---
def get_next_nom_zayavki():
    """Генерирует следующий номер заявки по году."""
    current_year = datetime.now().year
    count_this_year = Request.query.filter(
        db.func.extract('year', Request.date_zagruzki) == current_year
    ).count()
    return f"{current_year}-{count_this_year + 1}"


def get_moscow_time(dt):
    """Конвертирует UTC время в московское."""
    if dt:
        return dt.replace(tzinfo=pytz.utc).astimezone(MOSCOW_TZ)
    return None


# --- Маршруты ---

@app.route('/')
@login_required
def index():
    """Главная страница со списком заявок."""
    # Получаем параметры фильтрации
    filter_nom = request.args.get('filter_nom', '').strip()
    filter_forma = request.args.get('filter_forma', '').strip()
    filter_economist = request.args.get('filter_economist', '').strip()
    filter_programmer_id = request.args.get('filter_programmer', '').strip()
    filter_tip_id = request.args.get('filter_tip', '').strip()
    filter_status = request.args.get('filter_status', '').strip()

    # Базовый запрос
    query = Request.query

    # Применяем фильтры
    if filter_nom:
        query = query.filter(Request.nom_zayavki.ilike(f'%{filter_nom}%'))

    if filter_forma:
        query = query.filter(Request.forma.ilike(f'%{filter_forma}%'))

    if filter_economist:
        query = query.join(Request.economist_user).filter(
            User.name.ilike(f'%{filter_economist}%')
        )

    if filter_programmer_id and filter_programmer_id.isdigit():
        query = query.filter(Request.programmer_id == int(filter_programmer_id))

    if filter_tip_id and filter_tip_id.isdigit():
        query = query.filter(Request.tip_zayavki_id == int(filter_tip_id))

    if filter_status:
        query = query.filter(Request.status == filter_status)

    # Выполняем запрос
    requests = query.order_by(Request.date_zagruzki.desc()).all()

    # Добавляем московское время для отображения
    for req in requests:
        req.date_zagruzki_msk = get_moscow_time(req.date_zagruzki)

    # Данные для фильтров
    users_programmer = User.query.filter_by(role='programmer').all()
    tipy_zayavok = TipZayavki.query.all()

    # Уникальные значения для выпадающих списков
    unique_statuses = [
        status[0] for status in db.session.query(Request.status).distinct().all()
        if status[0]
    ]

    unique_tip_ids = [
        tid[0] for tid in db.session.query(Request.tip_zayavki_id).distinct().all()
        if tid[0]
    ]
    unique_tip_objects = TipZayavki.query.filter(TipZayavki.id.in_(unique_tip_ids)).all()

    unique_prog_ids = [
        pid[0] for pid in db.session.query(Request.programmer_id).distinct().all()
        if pid[0]
    ]
    unique_prog_objects = User.query.filter(User.id.in_(unique_prog_ids)).all()

    return render_template(
        'index.html',
        requests=requests,
        users_programmer=users_programmer,
        tipy_zayavok=tipy_zayavok,
        unique_statuses=unique_statuses,
        unique_tip_objects=unique_tip_objects,
        unique_prog_objects=unique_prog_objects,
        filter_nom=filter_nom,
        filter_forma=filter_forma,
        filter_economist=filter_economist,
        filter_programmer=filter_programmer_id,
        filter_tip=filter_tip_id,
        filter_status=filter_status
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа."""
    from auth import login_user_func, is_valid_email

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        login_result = login_user_func(username, password)
        user_db = login_result['user']
        needs_email = login_result['needs_email']

        if user_db:
            if needs_email:
                session['pending_user_id'] = user_db.id
                return redirect(url_for('enter_email'))
            else:
                login_user(user_db)
                return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.')

    return render_template('login.html')


@app.route('/enter_email', methods=['GET', 'POST'])
def enter_email():
    """Страница ввода email для новых пользователей."""
    from auth import is_valid_email

    pending_user_id = session.get('pending_user_id')
    if not pending_user_id:
        flash("Сессия истекла или не была инициирована.")
        return redirect(url_for('login'))

    user = User.query.get(pending_user_id)
    if not user:
        flash('Ошибка: пользователь не найден.')
        session.pop('pending_user_id', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form['email'].strip()

        if not email:
            flash('Email обязателен для заполнения.')
        elif not is_valid_email(email):
            flash('Некорректный формат email.')
        else:
            user.email = email
            db.session.commit()
            flash('Email успешно сохранён.')

            session.pop('pending_user_id', None)
            login_user(user)
            return redirect(url_for('index'))

    return render_template('enter_email.html', user=user)


@app.route('/logout')
@login_required
def logout():
    """Выход из системы."""
    logout_user()
    return redirect(url_for('login'))


def validate_create_request_form(form_data):
    """Функция для проверки данных формы создания заявки."""
    errors = []
    forma = form_data.get('forma', '').strip()
    srok_vypolneniya_str = form_data.get('srok_vypolneniya', '').strip()
    telefon_zakazchika = form_data.get('telefon_zakazchika', '').strip()
    cel_zakaza = form_data.get('cel_zakaza', '').strip()

    if not forma:
        errors.append("Поле 'Форма' обязательно для заполнения.")

    if not srok_vypolneniya_str:
        errors.append("Поле 'Срок выполнения' обязательно для заполнения.")
    else:
        try:
            srok_vypolneniya = datetime.strptime(srok_vypolneniya_str, '%Y-%m-%d')
            if srok_vypolneniya.date() < date.today():
                errors.append("Срок выполнения не может быть раньше текущего дня.")
        except ValueError:
            errors.append("Некорректный формат даты 'Срок выполнения'. Используйте YYYY-MM-DD.")

    if not telefon_zakazchika:
        errors.append("Поле 'Телефон заказчика' обязательно для заполнения.")

    if not cel_zakaza:
        errors.append("Поле 'Цель заказа' обязательно для заполнения.")

    return errors, forma, srok_vypolneniya_str, telefon_zakazchika, cel_zakaza

@app.route('/create_request', methods=['GET', 'POST'])
@login_required
def create_request():
    if current_user.role != 'economist':
        flash('Только экономисты могут создавать заявки.', 'error')
        return redirect(url_for('index'))

    # Для GET запроса
    if request.method == 'GET':
        return render_template('create_request.html', today_date=date.today().strftime('%Y-%m-%d'))

    # Для POST запроса
    # Проверяем, было ли подтверждение
    confirmation_received = request.form.get('confirmed') == 'yes'

    forma = request.form.get('forma', '').strip()
    srok_vypolneniya_str = request.form.get('srok_vypolneniya', '').strip()
    telefon_zakazchika = request.form.get('telefon_zakazchika', '').strip()
    cel_zakaza = request.form.get('cel_zakaza', '').strip()

    errors = []
    if not forma:
        errors.append("Поле 'Форма' обязательно для заполнения.")
    if not srok_vypolneniya_str:
        errors.append("Поле 'Срок выполнения' обязательно для заполнения.")
    else:
        try:
            srok_vypolneniya = datetime.strptime(srok_vypolneniya_str, '%Y-%m-%d')
            if srok_vypolneniya.date() < date.today():
                errors.append("Срок выполнения не может быть раньше текущего дня.")
        except ValueError:
            errors.append("Некорректный формат даты. Используйте ГГГГ-ММ-ДД.")

    if not telefon_zakazchika:
        errors.append("Поле 'Телефон заказчика' обязательно для заполнения.")
    if not cel_zakaza:
        errors.append("Поле 'Цель заказа' обязательно для заполнения.")

    # Если есть ошибки валидации, возвращаем форму с сообщениями.
    if errors:
        for error in errors:
            flash(error, 'error')
        # Возвращаем форму с данными пользователя
        return render_template('create_request.html',
                               today_date=date.today().strftime('%Y-%m-%d'),
                               forma=forma,
                               srok_vypolneniya=srok_vypolneniya_str,
                               telefon_zakazchika=telefon_zakazchika,
                               cel_zakaza=cel_zakaza,
                               dop_informaciya=request.form.get('dop_informaciya', ''),
                               razmeshenie_rezultatov=request.form.get('razmeshenie_rezultatov', ''),
                               formulirovka_zakaza=request.form.get('formulirovka_zakaza', ''),
                               spisok_poley=request.form.get('spisok_poley', ''),
                               por_ydok_sort=request.form.get('por_ydok_sort', ''))

    # Если ошибок нет, но подтверждение не получено — возвращаем форму
    if not confirmation_received:
        return render_template('create_request.html',
                               today_date=date.today().strftime('%Y-%m-%d'),
                               forma=forma,
                               srok_vypolneniya=srok_vypolneniya_str,
                               telefon_zakazchika=telefon_zakazchika,
                               cel_zakaza=cel_zakaza,
                               dop_informaciya=request.form.get('dop_informaciya', ''),
                               razmeshenie_rezultatov=request.form.get('razmeshenie_rezultatov', ''),
                               formulirovka_zakaza=request.form.get('formulirovka_zakaza', ''),
                               spisok_poley=request.form.get('spisok_poley', ''),
                               por_ydok_sort=request.form.get('por_ydok_sort', ''))

    # --- Если ошибок нет и подтверждение получено ---
    # Тогда создаём заявку
    nom_zayavki = get_next_nom_zayavki()
    otdel = current_user.department
    data_zapolneniya = datetime.utcnow()
    srok_vypolneniya = datetime.strptime(srok_vypolneniya_str, '%Y-%m-%d')

    new_req = Request(
        nom_zayavki=nom_zayavki,
        forma=forma,
        economist_id=current_user.id,
        otdel=otdel,
        data_zapolneniya=data_zapolneniya,
        srok_vypolneniya=srok_vypolneniya,
        telefon_zakazchika=telefon_zakazchika,
        cel_zakaza=cel_zakaza,
        dop_informaciya=request.form.get('dop_informaciya', '').strip()[:1000],
        razmeshenie_rezultatov=request.form.get('razmeshenie_rezultatov', '').strip()[:500],
        formulirovka_zakaza=request.form.get('formulirovka_zakaza', '').strip()[:5000],
        spisok_poley=request.form.get('spisok_poley', '').strip()[:500],
        por_ydok_sort=request.form.get('por_ydok_sort', '').strip()[:500]
    )
    db.session.add(new_req)
    db.session.commit()
    flash(f'Заявка успешно создана! Номер: {new_req.nom_zayavki}', 'success')

    # --- Отправка уведомления ВСЕМ админам с заполненным email ---
    admin_users_with_email = User.query.filter_by(role='admin').filter(User.email.isnot(None)).filter(
        User.email != '').all()
    if admin_users_with_email:
        for admin_user in admin_users_with_email:
            send_new_request_notification(admin_user.email, new_req.nom_zayavki, current_user.name)
            # (Опционально) логировать каждую отправку
            # print(f"Notification sent to admin: {admin_user.username} at {admin_user.email}")
    else:
        import logging
        logging.warning(f"No admin users with email found. Cannot send notification for request {new_req.nom_zayavki}.")

    return redirect(url_for('index'))


@app.route('/assign_request/<int:request_id>', methods=['POST'])
@login_required
def assign_request(request_id):
    """Назначение программиста на заявку."""
    from email_sender import send_assignment_notification

    req = Request.query.get_or_404(request_id)

    can_assign = (
            current_user.role == 'admin' or
            (current_user.role == 'programmer' and req.programmer_id == current_user.id)
    )

    if not can_assign:
        flash('У вас нет прав для назначения программиста на эту заявку.')
        return redirect(url_for('index'))

    programmer_username = request.form.get('programmer_username')
    tip_zayavki_id = request.form.get('tip_zayavki_id')

    if req.status == 'Выполнено':
        flash('Нельзя изменить программиста у выполненной заявки.')
        return redirect(url_for('index'))

    if current_user.role == 'admin' and req.status == 'На рассмотрении':
        if not programmer_username:
            flash('Не выбран программист.')
            return redirect(url_for('index'))

        if not tip_zayavki_id:
            flash('Не выбран тип заявки.')
            return redirect(url_for('index'))

        programmer = User.query.filter_by(
            username=programmer_username,
            role='programmer'
        ).first()
        tip_obj = TipZayavki.query.get(tip_zayavki_id)

        if programmer and tip_obj:
            req.programmer_id = programmer.id
            req.tip_zayavki_id = tip_obj.id
            req.status = 'В работе'
            db.session.commit()

            flash(
                f'Заявка {req.nom_zayavki} назначена программисту {programmer.name} '
                f'и отмечена как "{tip_obj.nazvaniye}".'
            )

            if programmer.email:
                send_assignment_notification(
                    programmer.email,
                    req.nom_zayavki,
                    req.economist_user.name
                )
            else:
                logging.warning(
                    f"Email not set for programmer '{programmer.name}'. "
                    f"Cannot send assignment notification for request {req.nom_zayavki}."
                )
        elif not programmer:
            flash('Программист не найден или не является программистом.')
        elif not tip_obj:
            flash('Тип заявки не найден.')

        return redirect(url_for('index'))

    elif current_user.role == 'admin' or (
            current_user.role == 'programmer' and req.programmer_id == current_user.id
    ):
        if req.status in ['Отклонено', 'Выполнено']:
            flash('Нельзя изменить программиста у отклонённой или выполненной заявки.')
            return redirect(url_for('index'))

        if not programmer_username:
            flash('Не выбран программист.')
            return redirect(url_for('index'))

        new_programmer = User.query.filter_by(
            username=programmer_username,
            role='programmer'
        ).first()

        if new_programmer:
            old_programmer_name = req.programmer_user.name if req.programmer_user else 'None'
            req.programmer_id = new_programmer.id
            db.session.commit()

            flash(
                f'Программист для заявки {req.nom_zayavki} изменён '
                f'с {old_programmer_name} на {new_programmer.name}.'
            )
        else:
            flash('Программист не найден или не является программистом.')

        return redirect(url_for('index'))

    else:
        flash('Недостаточно прав для выполнения этого действия.')
        return redirect(url_for('index'))


@app.route('/complete_request/<int:request_id>', methods=['POST'])
@login_required
def complete_request_with_note(request_id):
    """Завершение заявки программистом."""
    from email_sender import send_completion_notification

    req = Request.query.get_or_404(request_id)

    if current_user.role != 'programmer' or req.programmer_id != current_user.id:
        flash('Только назначенный программист может завершить заявку.')
        return redirect(url_for('index'))

    note = request.form.get('completion_note', '').strip()
    req.status = 'Выполнено'
    req.date_ready = datetime.utcnow()

    if note:
        req.primechanie = note if not req.primechanie else req.primechanie + "\n" + note

    db.session.commit()
    flash(f'Заявка {req.nom_zayavki} отмечена как выполнена.')

    if req.economist_user.email:
        send_completion_notification(
            req.economist_user.email,
            req.nom_zayavki,
            req.programmer_user.name if req.programmer_user else "Неизвестный"
        )
    else:
        logging.warning(
            f"Email not set for requester '{req.economist_user.name}'. "
            f"Cannot send completion notification for request {req.nom_zayavki}."
        )

    return redirect(url_for('index'))


@app.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    """Отклонение заявки."""
    from email_sender import send_rejection_notification

    req = Request.query.get_or_404(request_id)

    if current_user.role != 'admin':
        if current_user.role != 'programmer' or req.programmer_id != current_user.id or req.status != 'В работе':
            flash('Недостаточно прав для отклонения заявки.')
            return redirect(url_for('index'))

    req.status = 'Отклонено'
    db.session.commit()
    flash(f'Заявка {req.nom_zayavki} отклонена.')

    if req.economist_user.email:
        send_rejection_notification(
            req.economist_user.email,
            req.nom_zayavki,
            current_user.name
        )
    else:
        logging.warning(
            f"Email not set for requester '{req.economist_user.name}'. "
            f"Cannot send rejection notification for request {req.nom_zayavki}."
        )

    return redirect(url_for('index'))


# --- Запуск приложения ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        initial_tips = [
            {"nazvaniye": "выборка из БД"},
            {"nazvaniye": "программирование"},
            {"nazvaniye": "DocMaker"}
        ]

        for tip_data in initial_tips:
            existing_tip = TipZayavki.query.filter_by(
                nazvaniye=tip_data["nazvaniye"]
            ).first()

            if not existing_tip:
                new_tip = TipZayavki(nazvaniye=tip_data["nazvaniye"])
                db.session.add(new_tip)

        db.session.commit()
        print("База данных инициализирована успешно.")

    app.run(host='0.0.0.0', port=1313, debug=True)