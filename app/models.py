from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    shipping_address = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")
    wishlist_items = db.relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    size = db.Column(db.String(100), nullable=False, default="S, M, L, XL")
    color = db.Column(db.String(40), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    rating = db.Column(db.Float, default=4.8, nullable=False)
    reviews_count = db.Column(db.Integer, default=12, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", back_populates="product")
    reviews = db.relationship("Review", back_populates="product", cascade="all, delete-orphan", order_by="desc(Review.created_at)")
    wishlist_entries = db.relationship("WishlistItem", back_populates="product", cascade="all, delete-orphan")

    @property
    def available_sizes(self):
        """Returns a list of stripped, uppercase size options."""
        if not self.size:
            return ["S", "M", "L", "XL"]
        raw = self.size.replace("/", ",").replace("|", ",")
        sizes = [s.strip().upper() for s in raw.split(",") if s.strip()]
        return sizes if sizes else ["S", "M", "L", "XL"]

    def in_stock(self, quantity=1):
        return self.is_active and self.stock >= quantity


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    customer_name = db.Column(db.String(150), nullable=False)
    customer_email = db.Column(db.String(150), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)

    razorpay_order_id = db.Column(db.String(100), nullable=True, unique=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    refund_id = db.Column(db.String(100), nullable=True)
    refund_status = db.Column(db.String(50), nullable=True)  # none, processed, failed
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, paid, shipped, delivered, cancelled

    # Tracking & Fulfillment metadata
    tracking_number = db.Column(db.String(100), nullable=True)
    courier_name = db.Column(db.String(100), nullable=True)
    estimated_delivery = db.Column(db.String(50), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    size = db.Column(db.String(30), nullable=True, default="M")
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="wishlist_items")
    product = db.relationship("Product", back_populates="wishlist_entries")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    reviewer_name = db.Column(db.String(150), nullable=True)
    rating = db.Column(db.Integer, nullable=False, default=5)
    title = db.Column(db.String(200), nullable=True)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")

    @property
    def author_name(self):
        if self.user and self.user.name:
            return self.user.name
        return self.reviewer_name or "Verified Customer"


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)