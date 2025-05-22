from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from whatsappclone.database.db import get_db_connection  # PostgreSQL bağlantısı

bcrypt = Bcrypt()
auth_blueprint: Blueprint = Blueprint("auth", __name__)
chat_blueprint = Blueprint("chat", __name__)

# ✅ Kullanıcı kayıt (Register)
@auth_blueprint.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Kullanıcı adı ve şifre gereklidir!"}), 400

    # Kullanıcı adı veritabanında var mı kontrol et
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM girisyap WHERE username = %s", (username,))  # Tablo adı 'giris'
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({"error": "❌ Bu kullanıcı adı zaten kullanılıyor!"}), 400

    # Şifreyi hashle
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Yeni kullanıcıyı veritabanına ekle
    try:
        cursor.execute("INSERT INTO girisyap (username, password) VALUES (%s, %s)", (username, hashed_password))  # Tablo adı 'giris'
        conn.commit()
        return jsonify({"message": "✅ Kullanıcı başarıyla kaydedildi!", "username": username}), 201
    except Exception as e:
        print("Hata oluştu: ", e)
        return jsonify({"error": "❌ Kayıt işlemi sırasında bir hata oluştu!"}), 500
    finally:
        cursor.close()
        conn.close()

# ✅ Kullanıcı giriş (Login)
@auth_blueprint.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Kullanıcı adı ve şifre gereklidir!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM girisyap WHERE username = %s", (username,))  # Tablo adı 'giris'
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and bcrypt.check_password_hash(user[2], password):
        access_token = create_access_token(identity=user[0])
        return jsonify({
            "message": "✅ Giriş başarılı!",
            "token": access_token,
            "user_id": user[0],  # <-- INT
            "username": user[1]  # <-- STRING
        }), 200

    return jsonify({"error": "❌ Hatalı kullanıcı adı veya şifre!"}),401