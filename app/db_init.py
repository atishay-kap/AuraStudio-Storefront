import os
from werkzeug.security import generate_password_hash
from app import db
from app.models import Product, AdminUser, User, WishlistItem, Review, Order, OrderItem

PRODUCTS = [
    {"name": "Silk-Lined Minimalist Flight Bomber", "category": "Jackets", "price": 9499.00, "size": "S, M, L, XL", "color": "Obsidian Noir", "stock": 10,
     "image_url": "/static/images/products/jacket_bomber.jpg",
     "description": "Tailored satin-silk lined flight jacket with ribbed trims, dual-entry pockets, and burnished gold zipper hardware.", "rating": 4.9, "reviews_count": 28},
    {"name": "Selvedge Raw Denim Artisan Jacket", "category": "Jackets", "price": 7999.00, "size": "S, M, L, XL", "color": "Indigo Selvedge", "stock": 12,
     "image_url": "/static/images/products/jacket_denim.jpg",
     "description": "14oz Japanese selvedge raw denim jacket with custom antique brass shank buttons and bespoke tailoring.", "rating": 4.9, "reviews_count": 42},
    {"name": "Featherlight Quilted Down Puffer Vest", "category": "Jackets", "price": 5499.00, "size": "S, M, L, XL", "color": "Matte Obsidian", "stock": 14,
     "image_url": "/static/images/products/jacket_puffer.jpg",
     "description": "750-fill power responsibly sourced down vest with water-repellent matte microfiber shell.", "rating": 4.8, "reviews_count": 16},
    {"name": "Normandy Pure Linen Resort Shirt", "category": "Shirts", "price": 3999.00, "size": "S, M, L, XL", "color": "Sand Beige", "stock": 15,
     "image_url": "/static/images/products/shirt_linen.jpg",
     "description": "100% Normandy flax pure linen long-sleeve shirt with natural Australian mother-of-pearl buttons.", "rating": 4.8, "reviews_count": 14},
    {"name": "Mercerized Silk-Cotton Knit Polo", "category": "Shirts", "price": 3299.00, "size": "S, M, L, XL", "color": "Midnight Navy", "stock": 26,
     "image_url": "/static/images/products/shirt_polo.jpg",
     "description": "18-gauge fine knit polo crafted from long-staple mercerized cotton and mulberry silk blend.", "rating": 4.7, "reviews_count": 20},
    {"name": "Chunky Ribbed Cashmere-Merino Sweater", "category": "Sweaters", "price": 5999.00, "size": "S, M, L, XL", "color": "Warm Cream", "stock": 16,
     "image_url": "/static/images/products/sweater_knit.jpg",
     "description": "7-gauge chunky fisherman ribbed sweater woven from Italian merino wool and cashmere.", "rating": 4.9, "reviews_count": 38},
    {"name": "Pleated Italian Stretch Chinos", "category": "Pants", "price": 3999.00, "size": "30, 32, 34, 36", "color": "Sand Khaki", "stock": 25,
     "image_url": "/static/images/products/pants_chinos_khaki.jpg",
     "description": "Tailored double-pleated Italian stretch cotton trousers with crisp center press crease and tapered silhouette.", "rating": 4.8, "reviews_count": 27},
    {"name": "French Terry Drop-Shoulder Hoodie", "category": "Hoodies", "price": 4499.00, "size": "S, M, L, XL, XXL", "color": "Washed Charcoal", "stock": 20,
     "image_url": "/static/images/products/hoodie_charcoal.jpg",
     "description": "Heavyweight 450gsm loopback French terry hoodie featuring relaxed dropped shoulders and double-layered hood.", "rating": 5.0, "reviews_count": 31},
    {"name": "French Terry Drop-Shoulder Hoodie", "category": "Hoodies", "price": 4499.00, "size": "S, M, L, XL, XXL", "color": "Earth Olive", "stock": 18,
     "image_url": "/static/images/products/hoodie_olive.jpg",
     "description": "Heavyweight 450gsm loopback French terry hoodie in bespoke earth olive pigment dye.", "rating": 4.7, "reviews_count": 15},
    {"name": "Organic Heavyweight Crew Tee", "category": "T-Shirts", "price": 1899.00, "size": "XS, S, M, L, XL", "color": "Pure White", "stock": 40,
     "image_url": "/static/images/products/tee_white.jpg",
     "description": "280gsm organic combed cotton crewneck tee with reinforced ribbed binding. A foundational everyday luxury staple.", "rating": 4.9, "reviews_count": 24},
    {"name": "Organic Heavyweight Crew Tee", "category": "T-Shirts", "price": 1899.00, "size": "XS, S, M, L, XL", "color": "Obsidian Black", "stock": 35,
     "image_url": "/static/images/products/tee_black.jpg",
     "description": "280gsm organic combed cotton crewneck tee with reinforced ribbed binding in rich jet obsidian dye.", "rating": 4.8, "reviews_count": 18}
]


def auto_initialize_db(app):
    """Guarantees that all SQLite tables, columns, and default seed records exist automatically on startup."""
    with app.app_context():
        # Handle SQLite constraint migration for reviews table if user_id has NOT NULL
        try:
            with db.engine.connect() as conn:
                tables = [r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                if "reviews" in tables:
                    rev_info = conn.exec_driver_sql("PRAGMA table_info(reviews)").fetchall()
                    user_id_col = [r for r in rev_info if r[1] == "user_id"]
                    if user_id_col and user_id_col[0][3] == 1:  # notnull is set to 1
                        cnt = conn.exec_driver_sql("SELECT COUNT(*) FROM reviews").scalar()
                        if cnt == 0:
                            conn.exec_driver_sql("DROP TABLE reviews")
                            conn.commit()
        except Exception:
            pass

        db.create_all()

        # Check and migrate columns on orders and order_items table
        try:
            with db.engine.connect() as conn:
                # 1. Orders table migrations
                orders_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(orders)").fetchall()]
                if "user_id" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN user_id INTEGER REFERENCES users(id)")
                if "refund_id" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN refund_id VARCHAR(100)")
                if "refund_status" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN refund_status VARCHAR(50)")
                if "tracking_number" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN tracking_number VARCHAR(100)")
                if "courier_name" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN courier_name VARCHAR(100)")
                if "estimated_delivery" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN estimated_delivery VARCHAR(50)")
                if "admin_notes" not in orders_cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN admin_notes TEXT")

                # 2. Order Items table migrations
                order_items_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(order_items)").fetchall()]
                if "size" not in order_items_cols:
                    conn.exec_driver_sql("ALTER TABLE order_items ADD COLUMN size VARCHAR(30) DEFAULT 'M'")

                # 3. Products table migrations
                products_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(products)").fetchall()]
                if "is_active" not in products_cols:
                    conn.exec_driver_sql("ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT 1")
                if "rating" not in products_cols:
                    conn.exec_driver_sql("ALTER TABLE products ADD COLUMN rating FLOAT DEFAULT 4.8")
                if "reviews_count" not in products_cols:
                    conn.exec_driver_sql("ALTER TABLE products ADD COLUMN reviews_count INTEGER DEFAULT 12")

                # 4. Reviews table migrations
                reviews_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(reviews)").fetchall()]
                if "reviewer_name" not in reviews_cols:
                    conn.exec_driver_sql("ALTER TABLE reviews ADD COLUMN reviewer_name VARCHAR(150)")
                if "title" not in reviews_cols:
                    conn.exec_driver_sql("ALTER TABLE reviews ADD COLUMN title VARCHAR(200)")

                conn.commit()
        except Exception:
            pass

        # Seed products if empty
        if not Product.query.first():
            for p in PRODUCTS:
                db.session.add(Product(**p))
            db.session.commit()
        else:
            # Upgrade existing products: INR pricing & migrate remote Unsplash URLs to local static assets
            for product in Product.query.all():
                if product.price < 150.0:
                    for p in PRODUCTS:
                        if p["name"] == product.name:
                            product.price = p["price"]
                            break
                    else:
                        product.price = round(product.price * 80, 2)
                
                # Migrate remote Unsplash URLs to local static assets
                if product.image_url and ("unsplash.com" in product.image_url or not product.image_url.startswith(("/static/", "static/"))):
                    for p in PRODUCTS:
                        if p["name"] == product.name and p["color"] == product.color:
                            product.image_url = p["image_url"]
                            break
            db.session.commit()

        # Seed or refresh demo customer user
        demo_customer = User.query.filter_by(email="customer@example.com").first()
        if not demo_customer:
            demo_customer = User(
                name="Alex Morgan",
                email="customer@example.com",
                shipping_address="742 Evergreen Terrace, Springfield, OR 97477",
                is_admin=False
            )
            demo_customer.set_password("customer123")
            db.session.add(demo_customer)
            db.session.commit()
        else:
            # Guarantee password is valid
            if not demo_customer.check_password("customer123"):
                demo_customer.set_password("customer123")
                db.session.commit()

        # Seed or refresh demo admin user
        demo_admin = User.query.filter_by(email="admin@store.com").first()
        if not demo_admin:
            demo_admin = User(
                name="Store Administrator",
                email="admin@store.com",
                shipping_address="Storefront HQ, 100 Fashion Ave, New York, NY",
                is_admin=True
            )
            demo_admin.set_password("admin123")
            db.session.add(demo_admin)
            db.session.commit()
        else:
            demo_admin.is_admin = True
            if not demo_admin.check_password("admin123"):
                demo_admin.set_password("admin123")
                db.session.commit()

        # Seed or refresh secondary demo user
        demo_user2 = User.query.filter_by(email="demo@example.com").first()
        if not demo_user2:
            demo_user2 = User(
                name="Elena Vance",
                email="demo@example.com",
                shipping_address="123 Fashion Blvd, Beverly Hills, CA 90210",
                is_admin=False
            )
            demo_user2.set_password("demo123")
            db.session.add(demo_user2)
            db.session.commit()
        else:
            if not demo_user2.check_password("demo123"):
                demo_user2.set_password("demo123")
                db.session.commit()

        # Seed legacy AdminUser
        legacy_admin = AdminUser.query.filter_by(username="admin").first()
        if not legacy_admin:
            db.session.add(AdminUser(
                username="admin",
                password_hash=generate_password_hash("admin123")
            ))
            db.session.commit()
        else:
            legacy_admin.password_hash = generate_password_hash("admin123")
            db.session.commit()

        # Seed demo orders and wishlist for demo_customer if none exist
        if demo_customer and not Order.query.filter_by(user_id=demo_customer.id).first():
            p_hoodie = Product.query.filter(Product.name.like("%Hoodie%")).first() or Product.query.first()
            p_tee = Product.query.filter(Product.name.like("%Tee%")).first() or Product.query.first()
            if p_hoodie and p_tee:
                # Order 1: Shipped
                order1 = Order(
                    user_id=demo_customer.id,
                    customer_name=demo_customer.name,
                    customer_email=demo_customer.email,
                    shipping_address=demo_customer.shipping_address,
                    total_amount=float(p_hoodie.price),
                    status="shipped",
                    razorpay_payment_id="pay_demo_alex_101",
                    courier_name="BlueDart Express",
                    tracking_number="BD-IND-884920",
                    estimated_delivery="Within 2 business days"
                )
                db.session.add(order1)
                db.session.flush()
                db.session.add(OrderItem(
                    order_id=order1.id,
                    product_id=p_hoodie.id,
                    size="L",
                    quantity=1,
                    price_at_purchase=p_hoodie.price
                ))

                # Order 2: Delivered
                order2 = Order(
                    user_id=demo_customer.id,
                    customer_name=demo_customer.name,
                    customer_email=demo_customer.email,
                    shipping_address=demo_customer.shipping_address,
                    total_amount=float(p_tee.price) * 2,
                    status="delivered",
                    razorpay_payment_id="pay_demo_alex_100",
                    courier_name="Delhivery Courier",
                    tracking_number="DEL-IND-447219",
                    estimated_delivery="Delivered"
                )
                db.session.add(order2)
                db.session.flush()
                db.session.add(OrderItem(
                    order_id=order2.id,
                    product_id=p_tee.id,
                    size="M",
                    quantity=2,
                    price_at_purchase=p_tee.price
                ))

                # Seed wishlist item
                p_jacket = Product.query.filter(Product.name.like("%Jacket%")).first()
                if p_jacket and not WishlistItem.query.filter_by(user_id=demo_customer.id, product_id=p_jacket.id).first():
                    db.session.add(WishlistItem(user_id=demo_customer.id, product_id=p_jacket.id))

                db.session.commit()

        # Seed verified reviews across catalog if none exist
        if Review.query.count() == 0:
            SAMPLE_REVIEWS = [
                # T-Shirts
                {"product_match": "Classic Crew Tee", "reviewer": "Alex Morgan", "rating": 5, "title": "Exceptional Organic Cotton", "comment": "The organic cotton weight is sublime. Sits perfectly on the shoulders with clean minimal ribbing. An absolute wardrobe staple."},
                {"product_match": "Classic Crew Tee", "reviewer": "Devansh Mehta", "rating": 5, "title": "Zero Shrinkage, Perfect Fit", "comment": "Top tier fabric. Washed it multiple times and there is zero shrinkage or collar baconing. 10/10 quality."},
                {"product_match": "Classic Crew Tee", "reviewer": "Priya Sharma", "rating": 4, "title": "Great daily essential", "comment": "Extremely soft and breathable. The drape is flattering without feeling too tight."},
                
                # Hoodies
                {"product_match": "Oversized Hoodie", "reviewer": "Elena Vance", "rating": 5, "title": "Runway Level Drape", "comment": "The French terry fleece has that perfect heavyweight runway drape. The hood structure stands upright without flopping down."},
                {"product_match": "Oversized Hoodie", "reviewer": "Rohan Kapoor", "rating": 5, "title": "Substantial Weight & Cozy", "comment": "Incredible quality and warmth. The dropped shoulder cut feels so premium and modern."},
                {"product_match": "Oversized Hoodie", "reviewer": "Maya Sen", "rating": 4, "title": "Super comfortable silhouette", "comment": "Cozy, warm, and elevated. Rivals high-end designer pieces at a fraction of the cost."},

                # Jackets
                {"product_match": "Denim Jacket", "reviewer": "Vikram Patel", "rating": 5, "title": "Authentic Selvedge Feel", "comment": "Selvedge denim stiffness softens nicely with wear. The hand-distressed detailing looks authentic and bespoke."},
                {"product_match": "Denim Jacket", "reviewer": "Sarah Jenkins", "rating": 5, "title": "Stunning Craftsmanship", "comment": "Outstanding hardware and contrast stitching. Got compliments the first day wearing it out."},
                {"product_match": "Bomber Jacket", "reviewer": "Ananya Roy", "rating": 5, "title": "Buttery Silk Lining", "comment": "The silk lining is buttery smooth and the custom matte zippers glide with ease."},
                {"product_match": "Bomber Jacket", "reviewer": "Chris Evans", "rating": 4, "title": "Clean Minimalist Bomber", "comment": "Clean silhouette with just the right amount of insulation. Fits true to luxury sizing."},

                # Pants
                {"product_match": "Slim Fit Chinos", "reviewer": "Siddharth Verma", "rating": 5, "title": "Flawless Italian Stretch Weave", "comment": "Italian stretch fabric makes these so versatile for both studio work and evening gallery openings."},
                {"product_match": "Slim Fit Chinos", "reviewer": "Marcus Vance", "rating": 4, "title": "Sharp Tailored Silhouette", "comment": "Super sharp tailoring with slight stretch for mobility. Highly recommended."},
                {"product_match": "Relaxed Joggers", "reviewer": "Tanya Joshi", "rating": 5, "title": "Like Wearing Clouds", "comment": "Modal fleece feels unbelievable against the skin. The tapered ankle cuff stays crisp and doesn't stretch out."},
                {"product_match": "Relaxed Joggers", "reviewer": "Kevin Chen", "rating": 5, "title": "Luxury Loungewear Defined", "comment": "Best luxury loungewear purchase this season. Pairs easily with oversized tees."},

                # Shirts
                {"product_match": "Linen Shirt", "reviewer": "Arjun Singhania", "rating": 5, "title": "Pure Normandy Linen Excellence", "comment": "Normandy linen breathes exceptionally well in warm weather. The genuine mother-of-pearl buttons are gorgeous."},
                {"product_match": "Flannel Shirt", "reviewer": "Daniel Craig", "rating": 5, "title": "Rich Pigment Dyeing", "comment": "Double-brushed cotton has extraordinary depth. The plaid weave is aligned across seams perfectly."},
                {"product_match": "Polo Shirt", "reviewer": "Nikhil Nair", "rating": 5, "title": "Subtle Sheen & Tailored Collar", "comment": "Mercerized pique finish gives it a subtle luster. The structured collar holds shape after washing."},

                # Others
                {"product_match": "Graphic Tee", "reviewer": "Rhea Kapoor", "rating": 5, "title": "High Definition Screenprint", "comment": "Atelier screenprint has high definition texture. Boxy cut is contemporary and relaxed."},
                {"product_match": "Puffer Vest", "reviewer": "Sameer Malhotra", "rating": 5, "title": "Featherlight Down Insulation", "comment": "Recycled down is featherlight yet keeps you remarkably warm. Sleek matte weather-resistant shell."},
                {"product_match": "Cargo Pants", "reviewer": "Karan Oberoi", "rating": 5, "title": "Modular Streetwear Staple", "comment": "Modular zip pockets are well placed without looking bulky. Essential modern streetwear staple."},
                {"product_match": "Knit Sweater", "reviewer": "Zoe Kravitz", "rating": 5, "title": "Heirloom Grade Merino Wool", "comment": "Chunky merino rib knit is warm without being itchy. Truly heirloom grade craftsmanship."}
            ]

            for s in SAMPLE_REVIEWS:
                matching_products = Product.query.filter(Product.name.like(f"%{s['product_match']}%")).all()
                for prod in matching_products:
                    rev = Review(
                        product_id=prod.id,
                        user_id=demo_customer.id if s["reviewer"] == "Alex Morgan" else (demo_user2.id if s["reviewer"] == "Elena Vance" else None),
                        reviewer_name=s["reviewer"],
                        title=s["title"],
                        rating=s["rating"],
                        comment=s["comment"]
                    )
                    db.session.add(rev)

            db.session.commit()

            # Recalculate ratings & review counts for all products
            for prod in Product.query.all():
                prod_reviews = Review.query.filter_by(product_id=prod.id).all()
                if prod_reviews:
                    prod.reviews_count = len(prod_reviews)
                    prod.rating = round(sum(r.rating for r in prod_reviews) / len(prod_reviews), 1)
            db.session.commit()
