"""
models.py - Database models for Flask application with Flask-SQLAlchemy and Flask-Login.
Defines User, UserAppData, UserInstance, ProvisionedNumber, and Invitation models for PostgreSQL database.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt
from datetime import datetime
import logging
import uuid

from sqlalchemy import Numeric

db = SQLAlchemy()
logger = logging.getLogger("voicemail_app")


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), nullable=True, unique=True)
    supabase_id = db.Column(db.String(255), nullable=True, unique=True)
    profile_name = db.Column(db.String(100), nullable=True)
    profile_image_url = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    credit_balance = db.Column(Numeric(10, 2), default=5.00, nullable=False)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    app_data = db.relationship('UserAppData', backref='user', lazy=True, cascade='all, delete-orphan')
    instance = db.relationship('UserInstance', backref='user', uselist=False, lazy=True, cascade='all, delete-orphan')
    provisioned_numbers = db.relationship('ProvisionedNumber', backref='user', lazy=True, cascade='all, delete-orphan')
    
    @property
    def is_active(self):
        return self.is_active_account
    
    def set_password(self, password):
        if password:
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'profile_name': self.profile_name,
            'profile_image_url': self.profile_image_url,
            'credit_balance': float(self.credit_balance or 0),
            'has_google': self.google_id is not None,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Invitation(db.Model):
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    grant_free_access = db.Column(db.Boolean, default=False, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    inviter = db.relationship('User', foreign_keys=[invited_by])


class UserAppData(db.Model):
    __tablename__ = 'user_app_data'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_key = db.Column(db.String(100), nullable=False)
    data_value = db.Column(db.Text, default='{}', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'data_key', name='uq_user_data_key'),
    )


class UserInstance(db.Model):
    __tablename__ = 'user_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    status = db.Column(db.String(50), default='active', nullable=False)
    telnyx_connection_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProvisionedNumber(db.Model):
    __tablename__ = 'provisioned_numbers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone_number = db.Column(db.String(30), nullable=False)
    telnyx_number_id = db.Column(db.String(255), nullable=True)
    telnyx_order_id = db.Column(db.String(255), nullable=True)
    telnyx_connection_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='provisioning', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('phone_number', name='uq_provisioned_phone'),
    )


def ensure_user_instance(user_id):
    instance = UserInstance.query.filter_by(user_id=user_id).first()
    if not instance:
        instance = UserInstance(user_id=user_id, status='active')
        db.session.add(instance)
        db.session.commit()
    return instance


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_schema()


def _ensure_schema():
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return

        existing_cols = {col["name"] for col in inspector.get_columns("users")}

        if "supabase_id" not in existing_cols:
            logger.warning("DB schema missing users.supabase_id; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN supabase_id VARCHAR(255)"))
            db.session.commit()

        db.session.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_supabase_id_unique ON users (supabase_id)")
        )
        db.session.commit()

        if "credit_balance" not in existing_cols:
            logger.warning("DB schema missing users.credit_balance; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN credit_balance NUMERIC(10,2) DEFAULT 5.00 NOT NULL"))
            db.session.execute(text("UPDATE users SET credit_balance = 5.00 WHERE credit_balance IS NULL"))
            db.session.commit()

        if "role" not in existing_cols:
            logger.warning("DB schema missing users.role; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
            db.session.commit()

        if "is_active_account" not in existing_cols:
            logger.warning("DB schema missing users.is_active_account; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active_account BOOLEAN DEFAULT TRUE NOT NULL"))
            db.session.commit()

        if "reset_token" not in existing_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP"))
            db.session.commit()

        admin_email = __import__('os').environ.get("ADMIN_EMAIL", "")
        if admin_email:
            admin_user = User.query.filter_by(email=admin_email.lower()).first()
            if admin_user and admin_user.role != 'admin':
                admin_user.role = 'admin'
                db.session.commit()

    except Exception as e:
        logger.exception(f"Schema ensure failed: {e}")
        print(f"Schema ensure failed: {e}")
