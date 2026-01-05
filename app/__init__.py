from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
@login_manager.user_loader
def load_user(user_id):
    from app.models import Usuario
    return Usuario.query.get(str(user_id))

from app import routes, models
