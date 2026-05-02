import os
from flask import Flask
from app.config import Config
from app.models import db
def create_app(register_routes=True):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    os.makedirs(app.config["AUDIO_DIR"], exist_ok=True)
    os.makedirs(app.config["VOICEPRINT_DIR"], exist_ok=True)

    db.init_app(app)

    if register_routes:
        from app.routes.auth_routes import auth_routes
        from app.routes.dashboard_routes import dashboard_routes

        app.register_blueprint(auth_routes)
        app.register_blueprint(dashboard_routes)

    return app
