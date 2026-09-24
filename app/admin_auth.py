from functools import wraps
from flask import session, redirect, url_for, flash
from app.auth import get_current_user


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        is_admin = session.get("is_admin") or (user.is_admin if user else False)
        if not is_admin:
            flash("Please log in with admin privileges to access the admin panel.")
            return redirect(url_for("admin.login"))
        return view_func(*args, **kwargs)
    return wrapper