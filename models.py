"""
models.py - Database models for Flask application with Flask-SQLAlchemy and Flask-Login.
Defines User, UserAppData, UserInstance, and ProvisionedNumber models for PostgreSQL database.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt
from datetime import datetime
import logging

from sqlalchemy import Numeric

db = SQLAlchemy()
logger = logging.getLogger("voicemail_app")


class User(UserMixin, db.Model):
    """User model with Flask-Login integration."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), nullable=True, unique=True)
    supabase_id = db.Column(db.String(255), nullable=True, unique=True)
    profile_name = db.Column(db.String(100), nullable=True)
    profile_image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    credit_balance = db.Column(Numeric(10, 2), default=5.00, nullable=False)
    
    app_data = db.relationship('UserAppData', backref='user', lazy=True, cascade='all, delete-orphan')
    instance = db.relationship('UserInstance', backref='user', uselist=False, lazy=True, cascade='all, delete-orphan')
    provisioned_numbers = db.relationship('ProvisionedNumber', backref='user', lazy=True, cascade='all, delete-orphan')
    
    @property
    def is_active(self):
        """Flask-Login required property - always True."""
        return True
    
    def set_password(self, password):
        """Hash and set password using bcrypt."""
        if password:
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against hash using bcrypt."""
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        """Return user data as dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'profile_name': self.profile_name,
            'profile_image_url': self.profile_image_url,
            'credit_balance': float(self.credit_balance or 0),
            'has_google': self.google_id is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserAppData(db.Model):
    """Model for storing per-user application data as JSON."""
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
    """Per-user Alex instance. Created on signup to isolate each user's data."""
    __tablename__ = 'user_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    status = db.Column(db.String(50), default='active', nullable=False)
    telnyx_connection_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProvisionedNumber(db.Model):
    """Phone numbers provisioned via Telnyx and assigned to a specific user."""
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
    """Create a UserInstance for the user if one doesn't exist yet."""
    instance = UserInstance.query.filter_by(user_id=user_id).first()
    if not instance:
        instance = UserInstance(user_id=user_id, status='active')
        db.session.add(instance)
        db.session.commit()
    return instance


def init_db(app):
    """Initialize database with Flask app and create all tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_schema()


def _ensure_schema():
    """
    Lightweight, idempotent schema fixups for deployments without migrations.
    Railway Postgres will NOT auto-add columns when models change; create_all()
    only creates missing tables. This ensures critical columns exist.
    """
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return

        existing_cols = {col["name"] for col in inspector.get_columns("users")}

        # Fix: older DBs may not have supabase_id yet (causes 500s on any User query)
        if "supabase_id" not in existing_cols:
            logger.warning("DB schema missing users.supabase_id; applying ALTER TABLE")
            print("DB schema missing users.supabase_id; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN supabase_id VARCHAR(255)"))
            db.session.commit()

        # Ensure a unique index exists (multiple NULLs allowed in Postgres)
        # IF NOT EXISTS keeps this safe across restarts.
        db.session.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_supabase_id_unique ON users (supabase_id)")
        )
        db.session.commit()

        if "credit_balance" not in existing_cols:
            logger.warning("DB schema missing users.credit_balance; applying ALTER TABLE")
            print("DB schema missing users.credit_balance; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN credit_balance NUMERIC(10,2) DEFAULT 5.00 NOT NULL"))
            db.session.execute(text("UPDATE users SET credit_balance = 5.00 WHERE credit_balance IS NULL"))
            db.session.commit()

    except Exception as e:
        # Don't crash the app on migration errors; log for Railway.
        logger.exception(f"Schema ensure failed: {e}")
        print(f"Schema ensure failed: {e}")
