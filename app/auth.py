from functools import wraps
from flask import session, redirect, url_for, flash, g
from app.models import User


def get_current_user():
    """Retrieve the currently logged-in user or None."""
    from app import db

    if hasattr(g, "current_user"):
        return g.current_user

    user_id = session.get("user_id")
    if user_id:
        try:
            user = db.session.get(User, user_id)
            g.current_user = user
            return user
        except Exception:
            session.pop("user_id", None)
            session.pop("user_name", None)
            session.pop("user_email", None)
            session.pop("is_admin", None)
            session.pop("admin_username", None)
            g.current_user = None
            return None

    g.current_user = None
    return None


def login_user(user):
    """Set user info into session."""
    session["user_id"] = user.id
    session["user_name"] = user.name
    session["user_email"] = user.email
    if user.is_admin:
        session["is_admin"] = True
        session["admin_username"] = user.email
    g.current_user = user


def logout_user():
    """Clear user info from session."""
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    session.pop("is_admin", None)
    session.pop("admin_username", None)
    g.current_user = None


def login_required(view_func):
    """Decorator to require login for customer views."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to continue.")
            return redirect(url_for("storefront.login", next=url_for(view_func.__name__, **kwargs) if not kwargs else None))
        return view_func(*args, **kwargs)
    return wrapper
