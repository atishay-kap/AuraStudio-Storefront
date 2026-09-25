import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, abort
from werkzeug.security import check_password_hash
from app import db
from app.models import AdminUser, Order, Product, User, OrderItem
from app.admin_auth import admin_required
from app.auth import login_user, logout_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "avif"}

def save_uploaded_image(file_storage):
    """Saves an uploaded image file securely and returns its relative static URL."""
    if not file_storage or not file_storage.filename:
        return None
    
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    unique_filename = f"{uuid.uuid4().hex[:10]}_{filename}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    file_storage.save(file_path)
    return url_for("static", filename=f"uploads/products/{unique_filename}")


# -------------------------------------------------------------------------
# Admin Authentication
# -------------------------------------------------------------------------

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_admin"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("username") or request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if identifier and password:
            user = User.query.filter(
                (User.email == identifier.lower()) | (User.name == identifier)
            ).first()
            if user and user.is_admin and user.check_password(password):
                login_user(user)
                session["is_admin"] = True
                session["admin_username"] = user.name
                flash(f"Welcome to Atelier Portal, {user.name}!", "success")
                return redirect(url_for("admin.dashboard"))

            admin_legacy = AdminUser.query.filter_by(username=identifier).first()
            if admin_legacy and check_password_hash(admin_legacy.password_hash, password):
                session["is_admin"] = True
                session["admin_username"] = admin_legacy.username
                flash(f"Welcome to Atelier Portal, {admin_legacy.username}!", "success")
                return redirect(url_for("admin.dashboard"))

        flash("Invalid email or password. Please verify your credentials.", "danger")

    return redirect(url_for("storefront.login", next=url_for("admin.dashboard")))


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    session.pop("admin_username", None)
    logout_user()
    flash("Admin logged out successfully.", "info")
    return redirect(url_for("admin.login"))


# -------------------------------------------------------------------------
# Orders & Fulfillment Dashboard
# -------------------------------------------------------------------------

@admin_bp.route("/")
@admin_required
def dashboard():
    status_filter = request.args.get("status")
    search_query = request.args.get("q", "").strip()

    query = Order.query.filter(Order.status != "pending")

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.filter(
            db.or_(
                Order.customer_name.ilike(f"%{search_query}%"),
                Order.customer_email.ilike(f"%{search_query}%"),
                Order.tracking_number.ilike(f"%{search_query}%"),
                Order.razorpay_payment_id.ilike(f"%{search_query}%")
            )
        )

    orders = query.order_by(Order.created_at.desc()).all()

    # Metrics
    total_orders = Order.query.filter(Order.status != "pending").count()
    paid_count = Order.query.filter_by(status="paid").count()
    shipped_count = Order.query.filter_by(status="shipped").count()
    delivered_count = Order.query.filter_by(status="delivered").count()
    cancelled_count = Order.query.filter_by(status="cancelled").count()

    total_revenue = sum([float(o.total_amount) for o in Order.query.filter(Order.status.in_(["paid", "shipped", "delivered"])).all()])

    # Low stock alert count
    low_stock_count = Product.query.filter(Product.stock <= 5, Product.is_active == True).count()

    return render_template(
        "admin/dashboard.html",
        orders=orders,
        status_filter=status_filter,
        search_query=search_query,
        metrics={
            "total_orders": total_orders,
            "paid_count": paid_count,
            "shipped_count": shipped_count,
            "delivered_count": delivered_count,
            "cancelled_count": cancelled_count,
            "total_revenue": total_revenue,
            "low_stock_count": low_stock_count
        }
    )


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    return render_template("admin/order_detail.html", order=order)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    from app.refund_service import cancel_and_refund_order
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    new_status = request.form.get("status")

    if new_status == "cancelled":
        success, message = cancel_and_refund_order(order, reason="Cancelled by store administrator")
        flash(message, "success" if success else "danger")
    elif new_status in ["paid", "shipped", "delivered"]:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} status changed to '{new_status}'.", "success")
    else:
        flash("Invalid status specified.", "danger")

    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/orders/<int:order_id>/tracking", methods=["POST"])
@admin_required
def update_order_tracking(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    courier_name = request.form.get("courier_name", "").strip()
    tracking_number = request.form.get("tracking_number", "").strip()
    estimated_delivery = request.form.get("estimated_delivery", "").strip()
    admin_notes = request.form.get("admin_notes", "").strip()

    order.courier_name = courier_name or None
    order.tracking_number = tracking_number or None
    order.estimated_delivery = estimated_delivery or None
    order.admin_notes = admin_notes or None

    # Auto-advance status to shipped if tracking added and still in paid state
    if tracking_number and order.status == "paid":
        order.status = "shipped"

    db.session.commit()
    flash(f"Tracking and fulfillment details updated for Order #{order.id}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@admin_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@admin_required
def cancel_order_admin(order_id):
    from app.refund_service import cancel_and_refund_order
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    success, message = cancel_and_refund_order(order, reason="Cancelled by store administrator")
    flash(message, "success" if success else "danger")
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/orders/<int:order_id>/ship", methods=["POST"])
@admin_required
def ship_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    order.status = "shipped"
    db.session.commit()
    flash(f"Order #{order.id} marked as shipped.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


# -------------------------------------------------------------------------
# Product & Inventory Management (Full CRUD)
# -------------------------------------------------------------------------

@admin_bp.route("/products")
@admin_required
def products():
    category_filter = request.args.get("category")
    stock_filter = request.args.get("stock")  # 'low' or 'out'

    query = Product.query

    if category_filter:
        query = query.filter_by(category=category_filter)

    if stock_filter == "low":
        query = query.filter(Product.stock <= 5, Product.stock > 0)
    elif stock_filter == "out":
        query = query.filter(Product.stock <= 0)

    all_products = query.order_by(Product.category, Product.name).all()
    categories = [row[0] for row in Product.query.with_entities(Product.category).distinct()]

    return render_template(
        "admin/products.html",
        products=all_products,
        categories=categories,
        selected_category=category_filter,
        stock_filter=stock_filter
    )


@admin_bp.route("/products/add", methods=["POST"])
@admin_required
def add_product():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    price = request.form.get("price", type=float)
    size = request.form.get("size", "").strip()
    color = request.form.get("color", "").strip()
    stock = request.form.get("stock", 0, type=int)
    image_url = request.form.get("image_url", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not category or price is None:
        flash("Please provide product name, category, and a valid price.", "danger")
        return redirect(url_for("admin.products"))

    # Handle file upload if provided
    if "image_file" in request.files and request.files["image_file"].filename != "":
        uploaded_url = save_uploaded_image(request.files["image_file"])
        if uploaded_url:
            image_url = uploaded_url

    product = Product(
        name=name,
        category=category,
        price=price,
        size=size or "M",
        color=color or "Standard",
        stock=max(0, stock if stock is not None else 0),
        image_url=image_url or "/static/images/products/tee_white.jpg",
        description=description,
        is_active=True
    )
    db.session.add(product)
    db.session.commit()
    flash(f"Successfully added '{product.name}' to the inventory catalog.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.category = request.form.get("category", "").strip()
        product.price = request.form.get("price", type=float)
        product.size = request.form.get("size", "").strip()
        product.color = request.form.get("color", "").strip()
        product.stock = max(0, request.form.get("stock", 0, type=int))
        product.description = request.form.get("description", "").strip()
        product.is_active = bool(request.form.get("is_active"))

        # Check if new photo file uploaded
        if "image_file" in request.files and request.files["image_file"].filename != "":
            uploaded_url = save_uploaded_image(request.files["image_file"])
            if uploaded_url:
                product.image_url = uploaded_url
        else:
            raw_url = request.form.get("image_url", "").strip()
            if raw_url:
                product.image_url = raw_url

        db.session.commit()
        flash(f"Product '{product.name}' has been updated successfully.", "success")
        return redirect(url_for("admin.products"))

    categories = [row[0] for row in Product.query.with_entities(Product.category).distinct()]
    return render_template("admin/product_edit.html", product=product, categories=categories)


@admin_bp.route("/products/<int:product_id>/toggle", methods=["POST"])
@admin_required
def toggle_product_active(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    product.is_active = not product.is_active
    db.session.commit()
    status_str = "Active (Published)" if product.is_active else "Inactive (Draft/Hidden)"
    flash(f"Product '{product.name}' is now {status_str}.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    name = product.name
    # If product is linked to customer orders, archive it to protect purchase history
    if product.order_items:
        product.is_active = False
        db.session.commit()
        flash(f"Product '{name}' is linked to historical customer orders, so it was archived and hidden from the storefront.", "info")
        return redirect(url_for("admin.products"))

    db.session.delete(product)
    db.session.commit()
    flash(f"Product '{name}' has been permanently deleted.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/update", methods=["POST"])
@admin_required
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    stock = request.form.get("stock", type=int)
    price = request.form.get("price", type=float)

    if stock is not None:
        product.stock = max(0, stock)
    if price is not None and price >= 0:
        product.price = price

    db.session.commit()
    flash(f"Updated {product.name} (Price: ₹{product.price:.2f}, Stock: {product.stock}).", "success")
    return redirect(url_for("admin.products"))


# -------------------------------------------------------------------------
# Customer Directory & LTV Insights
# -------------------------------------------------------------------------

@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()

    # Calculate LTV and completed orders per user
    user_data = []
    for u in all_users:
        valid_orders = [o for o in u.orders if o.status in ["paid", "shipped", "delivered"]]
        ltv = sum(float(o.total_amount) for o in valid_orders)
        user_data.append({
            "user": u,
            "total_orders": len(u.orders),
            "completed_orders": len(valid_orders),
            "ltv": ltv
        })
    return render_template("admin/users.html", user_data=user_data)


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_user_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    db.session.commit()
    
    role = "Administrator" if user.is_admin else "Standard Customer"
    flash(f"User {user.name} ({user.email}) updated to {role}.", "success")
    return redirect(url_for("admin.users"))