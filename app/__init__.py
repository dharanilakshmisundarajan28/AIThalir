from flask import Flask, render_template, request, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel, gettext
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = gettext('Please log in to access this page.')
babel = Babel()

def get_locale():
    """Determine the best match for supported languages"""
    if 'language' in session:
        return session['language']
    return request.accept_languages.best_match(Config.LANGUAGES.keys())

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.farmer import bp as farmer_bp
    app.register_blueprint(farmer_bp, url_prefix='/farmer')
    
    from app.consumer import bp as consumer_bp
    app.register_blueprint(consumer_bp, url_prefix='/consumer')
    
    from app.supplier import bp as supplier_bp
    app.register_blueprint(supplier_bp, url_prefix='/supplier')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.marketplace import bp as marketplace_bp
    app.register_blueprint(marketplace_bp, url_prefix='/marketplace')
    
    from app.schemes import bp as schemes_bp
    app.register_blueprint(schemes_bp, url_prefix='/schemes')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/change-language/<lang>')
    def change_language(lang):
        if lang in Config.LANGUAGES:
            session['language'] = lang
        return request.referrer or '/'
    
    return app

from app import models