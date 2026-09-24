import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "storefront.db").replace("\\", "/")


def create_app(config=None):
    app = Flask(__name__)

    # Production vs Local Database Configuration
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Normalize postgres:// scheme for SQLAlchemy 2.0
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "aura-studio-luxury-secret-key-2026")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config:
        app.config.update(config)

    db.init_app(app)

    from app import models  # noqa: F401
    from app.auth import get_current_user
    from flask import session

    @app.before_request
    def load_logged_in_user():
        get_current_user()

    from app.models import WishlistItem

    @app.context_processor
    def inject_user_and_cart():
        user = get_current_user()
        cart = session.get("cart", {})
        cart_count = sum(cart.values()) if cart else 0
        wishlist_count = len(user.wishlist_items) if user else 0
        return {
            "current_user": user,
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
            "is_admin": session.get("is_admin", False) or (user.is_admin if user else False)
        }

    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500

    from app.routes import storefront_bp
    app.register_blueprint(storefront_bp)

    from app.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # Automatically ensure database tables, schema columns, and seed accounts are initialized
    if not app.config.get("TESTING", False):
        from app.db_init import auto_initialize_db
        auto_initialize_db(app)

    return app