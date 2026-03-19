import uuid
from datetime import datetime
from app import db


def _generate_uuid():
    return str(uuid.uuid4())


class HumanaVoice(db.Model):
    __tablename__ = "humana_voices"

    id = db.Column(db.String(36), primary_key=True, default=_generate_uuid)
    user_id = db.Column(db.Integer, nullable=False)
    voice_id = db.Column(db.String(256), nullable=False)
    voice_name = db.Column(db.String(256), nullable=False)
    voice_type = db.Column(db.String(20), nullable=False, default="library")
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    preview_url = db.Column(db.String(512), nullable=True)
    style_speed = db.Column(db.Float, default=1.0)
    style_emotion = db.Column(db.String(50), default="neutral")

    def to_dict(self):
        return {
            "id": self.id,
            "voice_id": self.voice_id,
            "voice_name": self.voice_name,
            "voice_type": self.voice_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "preview_url": self.preview_url,
            "style_speed": self.style_speed,
            "style_emotion": self.style_emotion,
        }
