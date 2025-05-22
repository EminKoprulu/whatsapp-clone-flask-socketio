from flask import Flask, render_template, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
import sys

# Ortam değişkenlerini yükle
load_dotenv()

# Flask uygulamasını başlat
app = Flask(__name__, template_folder=os.path.abspath("../templates"))
CORS(app)

# SocketIO başlat
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# JWT yapılandırması
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
jwt = JWTManager(app)

# Blueprint içe aktar
from whatsappclone.routes.auth_routes import auth_blueprint
from whatsappclone.routes.chat_routes import chat_blueprint, init_socketio_handlers

app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(chat_blueprint, url_prefix="/chat_api")

# SocketIO handler'ları başlat
init_socketio_handlers(socketio)

# Sayfa yönlendirmeleri
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/call")
def call_page():
    me = request.args.get("me")
    to = request.args.get("to")
    if not me or not to:
        return "Eksik parametre", 400
    return render_template("call.html")

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
