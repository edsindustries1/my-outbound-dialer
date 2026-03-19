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
    navigator_persona = db.Column(db.Text, nullable=True)
    navigator_knowledge_base = db.Column(db.Text, nullable=True)
    
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
    expires_at = db.Column(db.DateTime, nullable=True)

    inviter = db.relationship('User', foreign_keys=[invited_by])

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


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
    last_used_at = db.Column(db.DateTime, nullable=True)

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


class AppConfig(db.Model):
    __tablename__ = 'app_config'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        try:
            row = cls.query.filter_by(key=key).first()
            return row.value if row and row.value else default
        except Exception:
            return default

    @classmethod
    def set(cls, key, value):
        try:
            row = cls.query.filter_by(key=key).first()
            if row:
                row.value = value
                row.updated_at = datetime.utcnow()
            else:
                row = cls(key=key, value=value)
                db.session.add(row)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


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

        if "navigator_persona" not in existing_cols:
            logger.warning("DB schema missing users.navigator_persona; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN navigator_persona TEXT"))
            db.session.commit()

        if "navigator_knowledge_base" not in existing_cols:
            logger.warning("DB schema missing users.navigator_knowledge_base; applying ALTER TABLE")
            db.session.execute(text("ALTER TABLE users ADD COLUMN navigator_knowledge_base TEXT"))
            db.session.commit()

        if "invitations" in inspector.get_table_names():
            inv_cols = {col["name"] for col in inspector.get_columns("invitations")}
            if "expires_at" not in inv_cols:
                db.session.execute(text("ALTER TABLE invitations ADD COLUMN expires_at TIMESTAMP"))
                db.session.commit()

        if "provisioned_numbers" in inspector.get_table_names():
            pn_cols = {col["name"] for col in inspector.get_columns("provisioned_numbers")}
            if "last_used_at" not in pn_cols:
                logger.warning("DB schema missing provisioned_numbers.last_used_at; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE provisioned_numbers ADD COLUMN last_used_at TIMESTAMP"))
                db.session.commit()

        if "app_config" not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS app_config (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            db.session.commit()

        _seed_max_concurrent_lines()

        pass

    except Exception as e:
        logger.exception(f"Schema ensure failed: {e}")
        print(f"Schema ensure failed: {e}")


def _seed_max_concurrent_lines():
    """Ensure every user has a max_concurrent_lines record in UserAppData.
    
    Defaults to 5 for free/starter users, 15 for business users.
    Does not overwrite existing records.
    """
    import json as _json
    try:
        users = User.query.all()
        for user in users:
            existing = UserAppData.query.filter_by(user_id=user.id, data_key="max_concurrent_lines").first()
            if existing:
                continue
            plan_limit = 5
            try:
                plan_rec = UserAppData.query.filter_by(user_id=user.id, data_key="active_plan").first()
                if plan_rec:
                    plan_val = _json.loads(plan_rec.data_value)
                    plan_name = (plan_val.get("plan") or "").lower()
                    if plan_name == "business":
                        plan_limit = 15
                    elif plan_name == "starter":
                        plan_limit = 5
            except Exception:
                pass
            payload = _json.dumps({"limit": plan_limit})
            rec = UserAppData(user_id=user.id, data_key="max_concurrent_lines", data_value=payload)
            db.session.add(rec)
        db.session.commit()
        logger.info("Seeded max_concurrent_lines for existing users")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Could not seed max_concurrent_lines: {e}")
