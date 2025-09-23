from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///pocketsage.db")
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    return app
