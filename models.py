"""
models.py - Database models for Flask application with Flask-SQLAlchemy and Flask-Login.
Defines User, UserAppData, UserInstance, ProvisionedNumber, Invitation, Campaign, and CallRecord models for PostgreSQL database.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt
from datetime import datetime
import logging
import uuid

from sqlalchemy import Numeric, Text

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
    daily_dial_count = db.Column(db.Integer, default=0, nullable=False)
    last_dial_date = db.Column(db.Date, nullable=True)
    is_included = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('phone_number', name='uq_provisioned_phone'),
    )


class NumberSwapLog(db.Model):
    __tablename__ = 'number_swap_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    old_number = db.Column(db.String(30), nullable=False)
    new_number = db.Column(db.String(30), nullable=False)
    swap_cost = db.Column(db.Numeric(10, 4), default=0, nullable=False)
    was_free = db.Column(db.Boolean, default=False, nullable=False)
    swap_reason = db.Column(db.String(50), default='manual', nullable=True)
    swapped_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class UserFeature(db.Model):
    """Per-user feature access flags.

    Each row represents one feature for one user.
    enabled=True means the user has access; enabled=False means explicitly revoked.
    Rows are upserted by (user_id, feature_key).
    """
    __tablename__ = 'user_features'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    feature_key = db.Column(db.String(60), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    granted_by = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(255), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'feature_key', name='uq_user_feature_key'),
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


class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(30), default='active', nullable=False, index=True)
    numbers = db.Column(Text, default='[]', nullable=False)
    dialed_count = db.Column(db.Integer, default=0, nullable=False)
    total_count = db.Column(db.Integer, default=0, nullable=False)
    dial_mode = db.Column(db.String(30), default='sequential', nullable=False)
    batch_size = db.Column(db.Integer, default=5, nullable=False)
    dial_delay = db.Column(db.Integer, default=2, nullable=False)
    audio_url = db.Column(Text, nullable=True)
    transfer_number = db.Column(db.String(50), nullable=True)
    from_number = db.Column(db.String(50), nullable=True)
    is_test = db.Column(db.Boolean, default=False, nullable=False)
    gatekeeper_navigator_enabled = db.Column(db.Boolean, default=False, nullable=False)
    prospect_name = db.Column(db.String(255), default='', nullable=False)
    prospect_company = db.Column(db.String(255), default='', nullable=False)
    navigator_voice_id = db.Column(db.String(255), nullable=True)
    navigator_knowledge_base = db.Column(Text, default='', nullable=False)
    campaign_type = db.Column(db.String(30), default='telnyx', nullable=False)
    sf_model_id = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    call_records = db.relationship('CallRecord', backref='campaign', lazy=True)

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'dialed_count': self.dialed_count,
            'total_count': self.total_count,
            'dial_mode': self.dial_mode,
            'batch_size': self.batch_size,
            'dial_delay': self.dial_delay,
            'audio_url': self.audio_url,
            'transfer_number': self.transfer_number,
            'from_number': self.from_number,
            'is_test': self.is_test,
            'gatekeeper_navigator_enabled': self.gatekeeper_navigator_enabled,
            'prospect_name': self.prospect_name,
            'prospect_company': self.prospect_company,
            'navigator_voice_id': self.navigator_voice_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CallRecord(db.Model):
    __tablename__ = 'call_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    call_control_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    phone_number = db.Column(db.String(50), nullable=False)
    from_number = db.Column(db.String(50), default='', nullable=False)
    status = db.Column(db.String(50), default='initiated', nullable=False)
    amd_result = db.Column(db.String(100), nullable=True)
    machine_detected = db.Column(db.Boolean, nullable=True)
    transferred = db.Column(db.Boolean, default=False, nullable=False)
    voicemail_dropped = db.Column(db.Boolean, default=False, nullable=False)
    hangup_cause = db.Column(db.String(100), nullable=True)
    transcript = db.Column(Text, default='[]', nullable=False)
    recording_url = db.Column(Text, nullable=True)
    ring_duration = db.Column(db.Integer, nullable=True)
    status_description = db.Column(db.String(255), default='', nullable=False)
    status_color = db.Column(db.String(20), default='blue', nullable=False)
    vm_duration = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(50), default='telnyx', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


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
            if "daily_dial_count" not in pn_cols:
                logger.warning("DB schema missing provisioned_numbers.daily_dial_count; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE provisioned_numbers ADD COLUMN daily_dial_count INTEGER DEFAULT 0 NOT NULL"))
                db.session.commit()
            if "last_dial_date" not in pn_cols:
                logger.warning("DB schema missing provisioned_numbers.last_dial_date; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE provisioned_numbers ADD COLUMN last_dial_date DATE"))
                db.session.commit()
            if "is_included" not in pn_cols:
                logger.warning("DB schema missing provisioned_numbers.is_included; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE provisioned_numbers ADD COLUMN is_included BOOLEAN DEFAULT FALSE NOT NULL"))
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

        if "campaigns" in inspector.get_table_names():
            camp_cols = {col["name"] for col in inspector.get_columns("campaigns")}
            if "campaign_type" not in camp_cols:
                logger.warning("DB schema missing campaigns.campaign_type; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE campaigns ADD COLUMN campaign_type VARCHAR(30) DEFAULT 'telnyx' NOT NULL"))
                db.session.commit()
            if "sf_model_id" not in camp_cols:
                logger.warning("DB schema missing campaigns.sf_model_id; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE campaigns ADD COLUMN sf_model_id TEXT"))
                db.session.commit()

        if "call_records" in inspector.get_table_names():
            cr_cols = {col["name"] for col in inspector.get_columns("call_records")}
            if "source" not in cr_cols:
                logger.warning("DB schema missing call_records.source; applying ALTER TABLE")
                db.session.execute(text("ALTER TABLE call_records ADD COLUMN source VARCHAR(50) DEFAULT 'telnyx' NOT NULL"))
                db.session.commit()

        _seed_max_concurrent_lines()
        _recover_interrupted_campaigns()

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


def _recover_interrupted_campaigns():
    try:
        # Only recover telnyx campaigns; synthflow campaigns are external and
        # cannot be resumed from in-memory state after a restart.
        # campaign_type column may not exist yet on first run (migration adds it).
        try:
            active_campaigns = Campaign.query.filter(
                Campaign.status.in_(['active', 'paused']),
                Campaign.campaign_type != 'synthflow',
            ).all()
        except Exception:
            active_campaigns = Campaign.query.filter(
                Campaign.status.in_(['active', 'paused'])
            ).all()
        if not active_campaigns:
            return
        for camp in active_campaigns:
            old_status = camp.status
            camp.status = 'interrupted'
            camp.updated_at = datetime.utcnow()
            logger.warning(
                f"Campaign {camp.id} for user {camp.user_id} was '{old_status}' at shutdown — "
                f"marked as 'interrupted' (dialed {camp.dialed_count}/{camp.total_count})"
            )
        db.session.commit()
        logger.info(f"Recovered {len(active_campaigns)} interrupted campaign(s) on startup")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Could not recover interrupted campaigns: {e}")


class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscribers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
