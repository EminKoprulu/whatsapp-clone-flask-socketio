import logging
from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room
from whatsappclone.database.db import get_db_connection # type: ignore

chat_blueprint = Blueprint("chat", __name__)


def _username_to_id(username: str, cur):
    cur.execute("SELECT id FROM girisyap WHERE username=%s", (username,))
    row = cur.fetchone()
    return row[0] if row else None


def _resolve_id(value, cur):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return _username_to_id(value, cur)


def init_socketio_handlers(socketio):

    @socketio.on("join_private_room")
    def _join_private(data):
        uid = data.get("user_id")
        if uid:
            join_room(str(uid))
            print(f"👤 User {uid} odaya katıldı (SID={request.sid})")

    @socketio.on("private_message")
    def _private(data):
        sender_raw = data.get("sender_id")
        receiver_raw = data.get("receiver_id")
        message = data.get("message")

        conn = cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            sender_id = _resolve_id(sender_raw, cur)
            receiver_id = _resolve_id(receiver_raw, cur)

            if sender_id is None or receiver_id is None:
                emit("error_msg", {"text": "Gönderici/alıcı bulunamadı"}, room=request.sid)
                return

            cur.execute("""
                INSERT INTO messages (sender_id, receiver_id, message, status)
                VALUES (%s, %s, %s, 'gönderildi')
                RETURNING id
            """, (sender_id, receiver_id, message))
            msg_id = cur.fetchone()[0]
            conn.commit()
            print("✅ mesaj kaydedildi | id", msg_id)

        except Exception as e:
            if conn: conn.rollback()
            logging.exception("DB hatası (private_message): %s", e)
            emit("error_msg", {"text": "Veritabanı hatası"}, room=request.sid)
            return
        finally:
            if cur: cur.close()
            if conn: conn.close()

        payload = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message,
            "message_id": msg_id
        }
        emit("new_private_message", payload, room=str(receiver_id))
        emit("new_private_message", payload, room=str(sender_id))
        emit("message_status", {"message_id": msg_id, "status": "gönderildi"}, room=str(sender_id))

    @socketio.on("mark_as_read")
    def _mark_as_read(data):
        message_id = data.get("message_id")
        original_sender_id = data.get("sender_id")

        if not message_id or not original_sender_id:
            logging.warning(f"mark_as_read için eksik veri: message_id={message_id}, original_sender_id={original_sender_id}")
            return

        conn = cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE messages SET status = 'okundu' WHERE id = %s", (message_id,))
            conn.commit()
            print(f"👁‍🗨 okundu olarak güncellendi | id: {message_id}")
        except Exception as e:
            if conn: conn.rollback()
            logging.exception("DB hatası (mark_as_read): %s", e)
        finally:
            if cur: cur.close()
            if conn: conn.close()

        emit("message_status", {"message_id": message_id, "status": "okundu"}, room=str(original_sender_id))

    @socketio.on("join_group")
    def _join_group(data):
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        if group_id:
            room_name = f"group_{group_id}"
            join_room(room_name)
            print(f"👥 Kullanıcı {user_id if user_id else 'Bilinmeyen'} group_{group_id} odasına katıldı (SID={request.sid})")

    @socketio.on("group_message")
    def _group_message(data):
        group_id = data.get("group_id")
        sender_id = data.get("sender_id")
        message = data.get("message")

        if not all([group_id, sender_id, message]):
            emit("error_msg", {"text": "Grup mesajı için eksik veri."}, room=request.sid)
            return

        conn = cur = None
        msg_db_id = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO group_messages (group_id, sender_id, message)
                VALUES (%s, %s, %s) RETURNING id
            """, (group_id, sender_id, message))
            msg_db_id = cur.fetchone()[0]
            conn.commit()
            print(f"📨 Grup mesajı kaydedildi | grup: {group_id}, mesaj_id: {msg_db_id}")
        except Exception as e:
            if conn: conn.rollback()
            logging.exception("Grup mesajı DB hatası: %s", e)
            emit("error_msg", {"text": "Grup mesajı kaydedilemedi."}, room=request.sid)
            return
        finally:
            if cur: cur.close()
            if conn: conn.close()

        emit("new_group_message", {
            "group_id": group_id,
            "sender_id": sender_id,
            "message": message,
            "message_id": msg_db_id
        }, room=f"group_{group_id}")

    @socketio.on("offer")
    def _offer(data):
        to_user_id = data.get("to")
        sdp = data.get("sdp")
        from_user_id = data.get("from_user_id")

        if to_user_id and sdp and from_user_id:
            payload_to_send = {"from_user_id": from_user_id, "sdp": sdp}
            target_room = str(to_user_id)
            print(f"DEBUG: Sending 'offer' to room {target_room} with payload: {payload_to_send}")
            socketio.emit("offer", payload_to_send, room=target_room)
            print(f"📞 Offer sent from User {from_user_id} to User {to_user_id}")
        else:
            print("⚠️ Offer received with missing data:", data)
            emit("error_msg", {"text": "Offer için eksik veri."}, room=request.sid)

    @socketio.on("answer")
    def _answer(data):
        to_user_id = data.get("to")
        sdp = data.get("sdp")
        from_user_id = data.get("from_user_id")

        if to_user_id and sdp and from_user_id:
            emit("answer", {"from_user_id": from_user_id, "sdp": sdp}, room=str(to_user_id))
            print(f"📢 Answer from User {from_user_id} sent to User {to_user_id}")
        else:
            print("⚠️ Answer received with missing data:", data)
            emit("error_msg", {"text": "Answer için eksik veri."}, room=request.sid)

    @socketio.on("ice-candidate")
    def _ice(data):
        to_user_id = data.get("to")
        candidate = data.get("candidate")
        from_user_id = data.get("from_user_id")

        if to_user_id and candidate and from_user_id:
            emit("ice-candidate", {"from_user_id": from_user_id, "candidate": candidate}, room=str(to_user_id))
        else:
            if not (to_user_id and from_user_id and candidate is None):
                print(f"🧊 ICE candidate from User {from_user_id} to User {to_user_id} (candidate is null - normal end).")
            elif not (to_user_id and from_user_id):
                print("⚠️ ICE candidate received with missing to_user_id or from_user_id:", data)
                emit("error_msg", {"text": "ICE candidate için eksik veri."}, room=request.sid)

    @socketio.on("hangup")
    def _hangup(data):
        to_user_id = data.get("to")
        from_user_id = data.get("from")

        if to_user_id and from_user_id:
            emit("hangup_received", {"from": from_user_id}, room=str(to_user_id))
            print(f"🚫 Call hangup by User {from_user_id}, notified User {to_user_id}")
        else:
            print("⚠️ Hangup received with missing data:", data)

# ✅ MESAJ GEÇMİŞİ GETİREN API (yeni)
@chat_blueprint.route("/messages/<int:user1_id>/<int:user2_id>", methods=["GET"])
def get_private_messages(user1_id, user2_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_id, receiver_id, message, status, created_at, id
        FROM messages
        WHERE (sender_id = %s AND receiver_id = %s)
           OR (sender_id = %s AND receiver_id = %s)
        ORDER BY created_at ASC
    """, (user1_id, user2_id, user2_id, user1_id))

    messages = cursor.fetchall()
    result = []
    for msg in messages:
        result.append({
            "message_id": msg[5],
            "sender_id": msg[0],
            "receiver_id": msg[1],
            "message": msg[2],
            "status": msg[3],
            "created_at": msg[4].isoformat()
        })

    cursor.close()
    conn.close()
    return jsonify(result), 200

# Grup oluşturma HTTP endpoint'i
@chat_blueprint.route("/create_group", methods=["POST"])
def create_group_route():
    data = request.get_json()
    group_name = data.get("name")
    creating_user_id = data.get("user_id_creating")

    if not group_name or not creating_user_id:
        return jsonify({"error": "Grup adı ve oluşturan kullanıcı ID'si gereklidir."}), 400

    conn = cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO groups (name, created_by_user_id)
            VALUES (%s, %s) RETURNING id
        """, (group_name, creating_user_id))
        group_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Grup oluşturuldu: Adı='{group_name}', ID={group_id}, Oluşturan={creating_user_id}")
        return jsonify({"message": "Grup başarıyla oluşturuldu.", "group_id": group_id, "group_name": group_name}), 201
    except Exception as e:
        if conn: conn.rollback()
        logging.exception("DB hatası (create_group): %s", e)
        return jsonify({"error": "Grup oluşturulurken bir veritabanı hatası oluştu."}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()
