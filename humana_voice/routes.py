from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
from app import db
from humana_voice.models import HumanaVoice
from humana_voice import fish_client

humana_voice_bp = Blueprint("humana_voice", __name__, url_prefix="/humana-voice")


@humana_voice_bp.record_once
def _create_tables(state):
    with state.app.app_context():
        db.create_all()


def _active_voice(user_id):
    return HumanaVoice.query.filter_by(user_id=user_id, is_active=True).first()


@humana_voice_bp.route("/")
@login_required
def index():
    voices = HumanaVoice.query.filter_by(user_id=current_user.id).order_by(HumanaVoice.created_at.desc()).all()
    active = _active_voice(current_user.id)
    api_key_set = fish_client.is_configured()
    return render_template(
        "humana_voice/index.html",
        voices=voices,
        active_voice=active,
        api_key_set=api_key_set,
    )


@humana_voice_bp.route("/api/library")
@login_required
def api_library():
    query = request.args.get("query", "")
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        data = fish_client.list_voices(query=query, page=page)
        items = data.get("items", [])
        normalized = []
        for v in items:
            normalized.append({
                "id": v.get("_id") or v.get("id", ""),
                "title": v.get("title", "Unnamed Voice"),
                "description": v.get("description", ""),
                "cover_image": fish_client.resolve_cover_image(v.get("cover_image") or v.get("cover_image_url", "")),
                "languages": v.get("languages", []),
                "sample_url": (
                    (v.get("samples") or [{}])[0].get("audio", "")
                    if v.get("samples") else v.get("sample_url", "")
                ),
            })
        return jsonify({"items": normalized, "total": data.get("total", len(normalized))})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@humana_voice_bp.route("/api/clone/upload", methods=["POST"])
@login_required
def api_clone_upload():
    audio = request.files.get("audio")
    voice_name = request.form.get("voice_name", "My Voice").strip() or "My Voice"
    if not audio:
        return jsonify({"error": "No audio file provided"}), 400
    try:
        result = fish_client.create_voice_model(audio.read(), audio.filename or "recording.mp3", voice_name)
        voice_id = result.get("_id") or result.get("id", "")
        rec = HumanaVoice(
            user_id=current_user.id,
            voice_id=voice_id,
            voice_name=voice_name,
            voice_type="cloned",
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({"voice_id": voice_id, "voice_name": voice_name, "status": "created", "id": rec.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@humana_voice_bp.route("/api/clone/record", methods=["POST"])
@login_required
def api_clone_record():
    audio = request.files.get("audio")
    voice_name = request.form.get("voice_name", "My Recording").strip() or "My Recording"
    if not audio:
        return jsonify({"error": "No recorded audio provided"}), 400
    try:
        result = fish_client.create_voice_model(audio.read(), "recording.mp3", voice_name)
        voice_id = result.get("_id") or result.get("id", "")
        rec = HumanaVoice(
            user_id=current_user.id,
            voice_id=voice_id,
            voice_name=voice_name,
            voice_type="cloned",
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({"voice_id": voice_id, "voice_name": voice_name, "status": "created", "id": rec.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@humana_voice_bp.route("/api/select", methods=["POST"])
@login_required
def api_select():
    data = request.get_json(silent=True) or {}
    voice_id = data.get("voice_id", "").strip()
    voice_name = data.get("voice_name", "Library Voice").strip() or "Library Voice"
    if not voice_id:
        return jsonify({"error": "voice_id required"}), 400
    existing = HumanaVoice.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
    if not existing:
        rec = HumanaVoice(
            user_id=current_user.id,
            voice_id=voice_id,
            voice_name=voice_name,
            voice_type="library",
        )
        db.session.add(rec)
        db.session.commit()
    return jsonify({"success": True})


@humana_voice_bp.route("/api/set-active", methods=["POST"])
@login_required
def api_set_active():
    data = request.get_json(silent=True) or {}
    voice_id = data.get("voice_id", "").strip()
    if not voice_id:
        return jsonify({"error": "voice_id required"}), 400
    HumanaVoice.query.filter_by(user_id=current_user.id).update({"is_active": False})
    target = HumanaVoice.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
    if not target:
        return jsonify({"error": "Voice not found in your library"}), 404
    target.is_active = True
    db.session.commit()
    return jsonify({"success": True})


@humana_voice_bp.route("/api/preview", methods=["POST"])
@login_required
def api_preview():
    data = request.get_json(silent=True) or {}
    voice_id = data.get("voice_id", "").strip()
    text = data.get("text", "Hello! This is a preview of your selected Humana Voice.").strip()
    if not voice_id:
        return jsonify({"error": "voice_id required"}), 400
    try:
        rec = HumanaVoice.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
        speed = rec.style_speed if rec else 1.0
        emotion = rec.style_emotion if rec else "neutral"
        resp = fish_client.text_to_speech(voice_id, text, speed=speed, emotion=emotion)

        def generate():
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        return Response(stream_with_context(generate()), mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@humana_voice_bp.route("/api/style", methods=["POST"])
@login_required
def api_style():
    data = request.get_json(silent=True) or {}
    voice_id = data.get("voice_id", "").strip()
    try:
        speed = float(data.get("speed", 1.0))
    except (ValueError, TypeError):
        return jsonify({"error": "speed must be a number"}), 400
    emotion = data.get("emotion", "neutral").strip()
    allowed_emotions = {"neutral", "excited", "calm", "serious", "friendly"}
    if emotion not in allowed_emotions:
        emotion = "neutral"
    if not voice_id:
        return jsonify({"error": "voice_id required"}), 400
    rec = HumanaVoice.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
    if not rec:
        return jsonify({"error": "Voice not found"}), 404
    rec.style_speed = max(0.5, min(2.0, speed))
    rec.style_emotion = emotion
    db.session.commit()
    return jsonify({"success": True})


@humana_voice_bp.route("/api/my-voices")
@login_required
def api_my_voices():
    voices = HumanaVoice.query.filter_by(user_id=current_user.id).order_by(HumanaVoice.created_at.desc()).all()
    return jsonify([v.to_dict() for v in voices])


@humana_voice_bp.route("/api/voice/<voice_id>", methods=["DELETE"])
@login_required
def api_delete_voice(voice_id):
    rec = HumanaVoice.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
    if not rec:
        return jsonify({"error": "Voice not found"}), 404
    if rec.voice_type == "cloned":
        try:
            fish_client.delete_voice_model(voice_id)
        except Exception:
            pass
    db.session.delete(rec)
    db.session.commit()
    return jsonify({"success": True})
