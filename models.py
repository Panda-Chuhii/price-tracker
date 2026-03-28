from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), default='')
    is_verified = db.Column(db.Boolean, default=False)
    items = db.relationship('TrackedItem', backref='user', lazy=True)

class TrackedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    product_name = db.Column(db.String(300), default='Unknown product')
    target_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    image_url = db.Column(db.Text)
    has_alert = db.Column(db.Boolean, default=False)
    price_history = db.relationship('PriceHistory', backref='item',
                                    lazy=True, cascade='all, delete-orphan')

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('tracked_item.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('tracked_item.id'), nullable=False)
    product_name = db.Column(db.String(300))
    old_price = db.Column(db.Float)
    new_price = db.Column(db.Float)
    target_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)