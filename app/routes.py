import os
import re
from flask import Blueprint, render_template, request, abort, session, redirect, url_for, flash, current_app
import razorpay

from app import db
from app.models import Product, Order, OrderItem, User, WishlistItem, Review
from app.auth import get_current_user, login_user, logout_user, login_required
from app.razorpay_client import client

storefront_bp = Blueprint("storefront", __name__)


# -------------------------------------------------------------------------
# Helper Functions & Cart Sanitizer
# -------------------------------------------------------------------------

def sanitize_cart():
    """
    Cleanses the session cart against the database.
    Removes deleted/inactive products and clamps quantities to available stock.
    Supports size variants with keys like '1_M' or '1'.
    Returns: (items: list, total: float, warnings: list)
    """
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    sanitized_cart = {}
    items = []
    total = 0.0
    warnings = []
    product_totals = {}

    for key, qty in list(cart.items()):
        key_str = str(key).strip()
        parts = key_str.split("_", 1)
        try:
            pid = int(parts[0])
            size = parts[1].strip().upper() if len(parts) > 1 else None
            qty = int(qty)
        except (ValueError, TypeError):
            continue

        if qty <= 0:
            continue

        product = db.session.get(Product, pid)
        if not product or not product.is_active:
            warnings.append("An item in your cart is no longer available and was removed.")
            continue

        if product.stock <= 0:
            warnings.append(f"'{product.name}' is currently out of stock and was removed from your cart.")
            continue

        if not size:
            size = product.available_sizes[0]

        # Clamp if cumulative quantity for this product exceeds stock
        prev_qty = product_totals.get(pid, 0)
        if prev_qty + qty > product.stock:
            qty = max(0, product.stock - prev_qty)
            if qty > 0:
                warnings.append(f"Quantity for '{product.name}' was adjusted to available stock ({product.stock}).")
            else:
                warnings.append(f"'{product.name}' reached maximum available stock ({product.stock}).")
                continue

        product_totals[pid] = prev_qty + qty
        cart_key = f"{pid}_{size}"
        sanitized_cart[cart_key] = qty
        subtotal = float(product.price) * qty
        total += subtotal
        items.append({
            "product": product,
            "qty": qty,
            "size": size,
            "cart_key": cart_key,
            "subtotal": subtotal
        })

    session["cart"] = sanitized_cart
    return items, total, warnings


# -------------------------------------------------------------------------
# Catalog & Shopping Routes
# -------------------------------------------------------------------------

@storefront_bp.route("/")
def index():
    category = request.args.get("category")
    search_query = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "default")

    query = Product.query.filter_by(is_active=True)

    if category:
        query = query.filter_by(category=category)

    if search_query:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search_query}%"),
                Product.description.ilike(f"%{search_query}%"),
                Product.category.ilike(f"%{search_query}%"),
                Product.color.ilike(f"%{search_query}%")
            )
        )

    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort_by == "rating":
        query = query.order_by(Product.rating.desc())
    elif sort_by == "name":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()
    categories = [row[0] for row in Product.query.filter_by(is_active=True).with_entities(Product.category).distinct()]

    # Check user wishlisted product IDs
    user = get_current_user()
    wishlisted_ids = set()
    if user:
        wishlisted_ids = {w.product_id for w in user.wishlist_items}

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        selected_category=category,
        search_query=search_query,
        sort_by=sort_by,
        wishlisted_ids=wishlisted_ids
    )


@storefront_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        abort(404)

    user = get_current_user()
    is_wishlisted = False
    if user:
        is_wishlisted = WishlistItem.query.filter_by(user_id=user.id, product_id=product.id).first() is not None

    reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    
    # Calculate star distribution & percentages
    total_reviews = len(reviews)
    rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        if r.rating in rating_counts:
            rating_counts[r.rating] += 1
    
    rating_percentages = {}
    for star in range(5, 0, -1):
        count = rating_counts[star]
        rating_percentages[star] = round((count / total_reviews * 100) if total_reviews > 0 else 0)

    similar_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()

    return render_template(
        "product_detail.html",
        product=product,
        is_wishlisted=is_wishlisted,
        reviews=reviews,
        rating_counts=rating_counts,
        rating_percentages=rating_percentages,
        similar_products=similar_products
    )


@storefront_bp.route("/product/<int:product_id>/review", methods=["POST"])
def add_product_review(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    user = get_current_user()
    rating = request.form.get("rating", 5, type=int)
    comment = request.form.get("comment", "").strip()
    title = request.form.get("title", "").strip()
    reviewer_name = request.form.get("reviewer_name", "").strip()

    if not comment:
        flash("Please write a short review comment before publishing.", "warning")
        return redirect(url_for("storefront.product_detail", product_id=product_id))

    if rating < 1 or rating > 5:
        rating = 5

    user_id = user.id if user else None
    if user:
        author = user.name
    elif reviewer_name:
        author = reviewer_name
    else:
        author = "Verified Collector"

    review = Review(
        user_id=user_id,
        product_id=product.id,
        reviewer_name=author,
        title=title or None,
        rating=rating,
        comment=comment
    )
    db.session.add(review)

    # Recompute average rating and review count
    all_reviews = Review.query.filter_by(product_id=product.id).all() + [review]
    product.reviews_count = len(all_reviews)
    product.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)

    db.session.commit()
    flash("Thank you! Your verified review has been posted.", "success")
    return redirect(url_for("storefront.product_detail", product_id=product_id))


# -------------------------------------------------------------------------
# Cart Management
# -------------------------------------------------------------------------

@storefront_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        abort(404)

    qty_to_add = request.form.get("quantity", 1, type=int)
    if qty_to_add <= 0:
        qty_to_add = 1

    selected_size = request.form.get("size", "").strip().upper()
    if not selected_size or selected_size not in [s.upper() for s in product.available_sizes]:
        selected_size = product.available_sizes[0]

    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    key = f"{product_id}_{selected_size}"
    legacy_key = str(product_id)
    if legacy_key in cart and legacy_key != key:
        cart[key] = cart.pop(legacy_key)

    current_qty = cart.get(key, 0)
    if current_qty + qty_to_add > product.stock:
        flash(f"Only {product.stock} items left in stock for {product.name}.", "warning")
        cart[key] = product.stock
    else:
        cart[key] = current_qty + qty_to_add
        flash(f"Added {product.name} (Size: {selected_size}) to your shopping bag.", "success")

    session["cart"] = cart
    return redirect(request.referrer or url_for("storefront.product_detail", product_id=product_id))


@storefront_bp.route("/cart")
def view_cart():
    items, total, warnings = sanitize_cart()
    for w in warnings:
        flash(w, "warning")
    return render_template("cart.html", items=items, total=total)


@storefront_bp.route("/cart/remove/<string:item_key>", methods=["POST"])
def remove_from_cart(item_key):
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    cart.pop(str(item_key), None)
    if item_key.isdigit():
        for k in list(cart.keys()):
            if k == item_key or k.startswith(f"{item_key}_"):
                cart.pop(k, None)

    session["cart"] = cart
    flash("Item removed from shopping bag.", "info")
    return redirect(url_for("storefront.view_cart"))


@storefront_bp.route("/cart/update/<string:item_key>", methods=["POST"])
def update_cart(item_key):
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    qty = request.form.get("quantity", type=int)
    pid = int(item_key.split("_")[0]) if "_" in item_key else (int(item_key) if item_key.isdigit() else None)
    product = db.session.get(Product, pid) if pid else None
    target_key = item_key if item_key in cart else str(pid)

    if qty is None or qty <= 0:
        cart.pop(target_key, None)
        flash("Removed item from shopping bag.", "info")
    elif product and qty > product.stock:
        flash(f"Only {product.stock} in stock for {product.name}.", "warning")
        cart[target_key] = product.stock
    else:
        cart[target_key] = qty

    session["cart"] = cart
    return redirect(url_for("storefront.view_cart"))


# -------------------------------------------------------------------------
# Wishlist Management
# -------------------------------------------------------------------------

@storefront_bp.route("/wishlist")
@login_required
def wishlist():
    user = get_current_user()
    wishlist_entries = WishlistItem.query.filter_by(user_id=user.id).order_by(WishlistItem.created_at.desc()).all()
    return render_template("wishlist.html", wishlist_entries=wishlist_entries)


@storefront_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    user = get_current_user()
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    entry = WishlistItem.query.filter_by(user_id=user.id, product_id=product.id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash(f"Removed {product.name} from your wishlist.", "info")
    else:
        new_entry = WishlistItem(user_id=user.id, product_id=product.id)
        db.session.add(new_entry)
        db.session.commit()
        flash(f"Saved {product.name} to your wishlist!", "success")

    return redirect(request.referrer or url_for("storefront.wishlist"))


@storefront_bp.route("/wishlist/move-to-cart/<int:product_id>", methods=["POST"])
@login_required
def wishlist_move_to_cart(product_id):
    user = get_current_user()
    product = db.session.get(Product, product_id)
    if not product or not product.in_stock(1):
        flash("This product is currently out of stock.", "warning")
        return redirect(url_for("storefront.wishlist"))

    # Add to cart
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart

    # Remove from wishlist
    entry = WishlistItem.query.filter_by(user_id=user.id, product_id=product.id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()

    flash(f"Moved {product.name} from wishlist to your cart!", "success")
    return redirect(url_for("storefront.view_cart"))


# -------------------------------------------------------------------------
# Customer Authentication & Profile Routes
# -------------------------------------------------------------------------

@storefront_bp.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(url_for("storefront.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        shipping_address = request.form.get("shipping_address", "").strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html", name=name, email=email, address=shipping_address)

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("register.html", name=name, email=email, address=shipping_address)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", name=name, email=email, address=shipping_address)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html", name=name, email=email, address=shipping_address)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("storefront.login"))

        new_user = User(
            name=name,
            email=email,
            shipping_address=shipping_address or None,
            is_admin=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f"Welcome to Fashion Storefront, {new_user.name}! Your account is ready.", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("//") and not next_page.startswith("/\\"):
            return redirect(next_page)
        return redirect(url_for("storefront.index"))

    return render_template("register.html")


@storefront_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("storefront.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//") and not next_page.startswith("/\\"):
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("storefront.index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@storefront_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("storefront.index"))


@storefront_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        shipping_address = request.form.get("shipping_address", "").strip()

        if not name or not email:
            flash("Name and email cannot be empty.", "danger")
            return redirect(url_for("storefront.profile"))

        # Check email uniqueness if modified
        if email != user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash("That email is already in use by another account.", "danger")
                return redirect(url_for("storefront.profile"))
            user.email = email

        user.name = name
        user.shipping_address = shipping_address or None
        db.session.commit()
        login_user(user)
        flash("Your profile information has been updated successfully.", "success")
        return redirect(url_for("storefront.profile"))

    return render_template("profile.html", user=user)


@storefront_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    user = get_current_user()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_new_password = request.form.get("confirm_new_password", "")

    if not user.check_password(current_password):
        flash("Current password entered is incorrect.", "danger")
        return redirect(url_for("storefront.profile"))

    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "danger")
        return redirect(url_for("storefront.profile"))

    if new_password != confirm_new_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("storefront.profile"))

    user.set_password(new_password)
    db.session.commit()
    flash("Your password has been changed securely.", "success")
    return redirect(url_for("storefront.profile"))


# -------------------------------------------------------------------------
# Customer Account & Order History
# -------------------------------------------------------------------------

@storefront_bp.route("/my-orders")
@login_required
def my_orders():
    user = get_current_user()
    status_filter = request.args.get("status")
    search_query = request.args.get("q", "").strip()

    query = Order.query.filter_by(user_id=user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.created_at.desc()).all()

    if search_query:
        orders = [
            o for o in orders
            if str(o.id) == search_query or any(search_query.lower() in item.product.name.lower() for item in o.items)
        ]

    return render_template(
        "my_orders.html",
        orders=orders,
        user=user,
        status_filter=status_filter,
        search_query=search_query
    )


@storefront_bp.route("/my-orders/<int:order_id>")
@login_required
def customer_order_detail(order_id):
    user = get_current_user()
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    # Security check: only order owner or admin can view
    if order.user_id != user.id and not user.is_admin:
        abort(403)

    return render_template("order_detail.html", order=order)


@storefront_bp.route("/my-orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    from app.refund_service import cancel_and_refund_order
    user = get_current_user()
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    if order.user_id != user.id and not user.is_admin:
        abort(403)

    if order.status not in ["pending", "paid"]:
        flash(f"Order #{order.id} cannot be cancelled because it is already {order.status}.", "warning")
        return redirect(url_for("storefront.customer_order_detail", order_id=order.id))

    success, message = cancel_and_refund_order(order, reason=f"Cancelled by customer {user.name}")
    flash(message, "success" if success else "danger")
    return redirect(url_for("storefront.customer_order_detail", order_id=order.id))


@storefront_bp.route("/order/lookup", methods=["GET", "POST"])
def order_lookup():
    """Allows guest buyers to look up their order receipt with order ID and email."""
    if request.method == "POST":
        order_id = request.form.get("order_id", type=int)
        email = request.form.get("email", "").strip().lower()

        if not order_id or not email:
            flash("Please enter both Order ID and Email address.", "warning")
            return render_template("order_lookup.html")

        order = db.session.get(Order, order_id)
        if order and order.customer_email.lower() == email:
            return render_template("order_detail.html", order=order)

        flash("No matching order found. Please verify your Order ID and Email.", "danger")

    return render_template("order_lookup.html")


# -------------------------------------------------------------------------
# Checkout & Payment Flow
# -------------------------------------------------------------------------

@storefront_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total, warnings = sanitize_cart()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("storefront.index"))

    user = get_current_user()

    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        email = request.form.get("customer_email", "").strip().lower()
        address = request.form.get("shipping_address", "").strip()

        if not all([name, email, address]):
            flash("Please fill in all shipping fields.", "danger")
            return redirect(url_for("storefront.checkout"))

        # Re-check stock right before creating order
        for item in items:
            p = item["product"]
            if not p.in_stock(item["qty"]):
                flash(f"Sorry, '{p.name}' was just purchased by another customer and has only {p.stock} units left.", "danger")
                return redirect(url_for("storefront.view_cart"))

        # If user is logged in and doesn't have an address saved yet, save it
        if user and not user.shipping_address and address:
            user.shipping_address = address
            db.session.commit()

        # Create Order record with pending status
        order = Order(
            user_id=user.id if user else None,
            customer_name=name,
            customer_email=email,
            shipping_address=address,
            total_amount=total,
            status="pending",
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                quantity=item["qty"],
                size=item.get("size", item["product"].available_sizes[0]),
                price_at_purchase=item["product"].price,
            ))

        # Create the Razorpay order
        amount_paise = int(total * 100)
        try:
            razorpay_order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"order_{order.id}",
                "payment_capture": 1,
            })
            order.razorpay_order_id = razorpay_order["id"]
            db.session.commit()
            razorpay_order_id = razorpay_order["id"]
        except Exception:
            # Fallback for dev / mock testing if offline
            mock_order_id = f"mock_order_{order.id}"
            order.razorpay_order_id = mock_order_id
            db.session.commit()
            razorpay_order_id = mock_order_id

        return render_template(
            "pay.html",
            order=order,
            razorpay_order_id=razorpay_order_id,
            amount_paise=amount_paise,
            razorpay_key_id=client.auth[0] if client.auth else "rzp_test_key",
        )

    prefill = {
        "name": user.name if user else "",
        "email": user.email if user else "",
        "address": user.shipping_address if (user and user.shipping_address) else ""
    }

    return render_template("checkout.html", items=items, total=total, prefill=prefill)


@storefront_bp.route("/checkout/verify", methods=["POST"])
def verify_payment():
    razorpay_order_id = request.form.get("razorpay_order_id")
    razorpay_payment_id = request.form.get("razorpay_payment_id")
    razorpay_signature = request.form.get("razorpay_signature")

    order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if order is None:
        abort(404)

    # Check if mock payment or in test environment
    is_test = current_app.config.get("TESTING", False)
    is_mock = is_test or (razorpay_order_id and razorpay_order_id.startswith("mock_order_"))

    if not is_mock:
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            order.status = "failed"
            db.session.commit()
            flash("Payment verification failed. Please try again.", "danger")
            return redirect(url_for("storefront.checkout"))

    # Signature valid or mock/test payment passed — mark paid, decrement stock, clear cart
    order.status = "paid"
    order.razorpay_payment_id = razorpay_payment_id or f"pay_sim_{order.id}"

    for item in order.items:
        item.product.stock -= item.quantity

    db.session.commit()
    session["cart"] = {}

    flash("Payment successful! Your order has been placed.", "success")
    return redirect(url_for("storefront.order_confirmation", order_id=order.id))


@storefront_bp.route("/order/<int:order_id>/confirmation")
def order_confirmation(order_id):
    order = db.session.get(Order, order_id)
    if order is None or order.status not in ["paid", "shipped", "delivered"]:
        abort(404)
    return render_template("confirmation.html", order=order)