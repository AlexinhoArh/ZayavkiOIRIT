# models.py
from flask_login import UserMixin
from datetime import datetime

# Импортируем db из extensions.py, а не из app.py
from extensions import db


class TipZayavki(db.Model):
    __tablename__ = 'tip_zayavki'

    id = db.Column(db.Integer, primary_key=True)
    nazvaniye = db.Column(db.String(255), nullable=False, unique=True)

    requests = db.relationship('Request', backref='tip_obj', lazy=True)

    def __repr__(self):
        return f'<TipZayavki {self.nazvaniye}>'


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(200))
    email = db.Column(db.String(254))

    created_requests = db.relationship('Request', foreign_keys='Request.economist_id', backref='economist_user',
                                       lazy=True)
    assigned_requests = db.relationship('Request', foreign_keys='Request.programmer_id', backref='programmer_user',
                                        lazy=True)


class Request(db.Model):
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