import os
import unittest
from app import create_app, db
from app.models import User, Product, Order, OrderItem, WishlistItem, Review

class ComprehensiveStorefrontTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Seed products
            product1 = Product(
                name="Minimalist Crewneck",
                description="Organic cotton crewneck sweatshirt.",
                price=45.00,
                category="Sweatshirts",
                size="M",
                color="Heather Grey",
                stock=5,
                image_url="https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800&q=80",
                is_active=True
            )
            product2 = Product(
                name="Draft Jacket",
                description="Upcoming winter jacket.",
                price=120.00,
                category="Jackets",
                size="L",
                color="Black",
                stock=2,
                image_url="https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&q=80",
                is_active=False
            )
            db.session.add_all([product1, product2])

            # Seed an admin user
            admin = User(
                name="Admin Master",
                email="admin@test.com",
                is_admin=True
            )
            admin.set_password("adminpass123")
            db.session.add(admin)

            # Seed a regular customer
            customer = User(
                name="Alice Walker",
                email="alice@test.com",
                shipping_address="123 Main St, New York, NY",
                is_admin=False
            )
            customer.set_password("customerpass123")
            db.session.add(customer)

            db.session.commit()
            self.p1_id = product1.id
            self.p2_id = product2.id
            self.admin_id = admin.id
            self.customer_id = customer.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_customer_registration_and_login_validation(self):
        # 1. Reject duplicate email registration
        res = self.client.post("/register", data={
            "name": "Alice Duplicate",
            "email": "alice@test.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertIn(b"An account with this email already exists", res.data)

        # 2. Reject mismatched passwords
        res = self.client.post("/register", data={
            "name": "New User",
            "email": "new@test.com",
            "password": "password123",
            "confirm_password": "mismatchpassword"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", res.data)

        # 3. Successful customer registration (auto-logs in)
        res = self.client.post("/register", data={
            "name": "David Bowie",
            "email": "david@test.com",
            "password": "davidpassword",
            "confirm_password": "davidpassword",
            "shipping_address": "77 Sunset Strip"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"David Bowie", res.data)

        # Log out David
        self.client.get("/logout", follow_redirects=True)

        # 4. Login with invalid password
        res = self.client.post("/login", data={
            "email": "david@test.com",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res.data)

        # 5. Login with valid password
        res = self.client.post("/login", data={
            "email": "david@test.com",
            "password": "davidpassword"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"David Bowie", res.data)

    def test_cart_sanitization_and_stock_clamping(self):
        # Add 3 units of product 1 (stock is 5)
        self.client.post(f"/cart/add/{self.p1_id}", data={"quantity": 3}, follow_redirects=True)
        cart_page = self.client.get("/cart")
        self.assertIn(b"Minimalist Crewneck", cart_page.data)
        self.assertIn(b"3", cart_page.data)

        # Attempt to add inactive product (product 2) -> returns 404
        res_inactive = self.client.post(f"/cart/add/{self.p2_id}", data={"quantity": 1}, follow_redirects=True)
        self.assertEqual(res_inactive.status_code, 404)
        self.assertIn(b"Page Not Found", res_inactive.data)

        # Simulate another buyer reducing product 1 stock to 1
        with self.app.app_context():
            p1 = db.session.get(Product, self.p1_id)
            p1.stock = 1
            db.session.commit()

        # Viewing cart should auto-sanitize and clamp quantity from 3 to 1
        sanitized_cart = self.client.get("/cart")
        self.assertIn(b"was adjusted to available stock", sanitized_cart.data)

    def test_authenticated_checkout_and_payment_flow(self):
        # Login Alice
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)

        # Add 2 items to cart
        self.client.post(f"/cart/add/{self.p1_id}", data={"quantity": 2}, follow_redirects=True)

        # Checkout page should prefill Alice's address
        checkout_get = self.client.get("/checkout")
        self.assertIn(b"123 Main St, New York, NY", checkout_get.data)

        # Submit checkout
        checkout_post = self.client.post("/checkout", data={
            "customer_name": "Alice Walker",
            "customer_email": "alice@test.com",
            "shipping_address": "123 Main St, New York, NY"
        }, follow_redirects=True)
        self.assertEqual(checkout_post.status_code, 200)

        # Get the pending order
        with self.app.app_context():
            order = Order.query.filter_by(user_id=self.customer_id).first()
            self.assertIsNotNone(order)
            self.assertEqual(order.status, "pending")
            self.assertEqual(float(order.total_amount), 90.00)  # 2 * 45.00
            order_id = order.id
            razorpay_order_id = order.razorpay_order_id

        # Verify payment simulation
        pay_res = self.client.post("/checkout/verify", data={
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": "pay_test_alice_999",
            "razorpay_signature": "mock_signature"
        }, follow_redirects=True)
        self.assertEqual(pay_res.status_code, 200)
        self.assertIn(b"Order Confirmed", pay_res.data)

        # Check stock is deducted from 5 to 3
        with self.app.app_context():
            updated_p1 = db.session.get(Product, self.p1_id)
            self.assertEqual(updated_p1.stock, 3)

            paid_order = db.session.get(Order, order_id)
            self.assertEqual(paid_order.status, "paid")

        # Alice checks My Orders
        my_orders = self.client.get("/my-orders")
        self.assertIn(f"Order #{order_id}".encode(), my_orders.data)

    def test_order_cancellation_and_inventory_refund(self):
        # Setup an existing paid order for Alice
        with self.app.app_context():
            order = Order(
                user_id=self.customer_id,
                customer_name="Alice Walker",
                customer_email="alice@test.com",
                shipping_address="123 Main St, New York, NY",
                total_amount=45.00,
                status="paid",
                razorpay_payment_id="pay_sim_refund_target"
            )
            db.session.add(order)
            db.session.flush()

            p1 = db.session.get(Product, self.p1_id)
            p1.stock = 4  # 1 was purchased

            db.session.add(OrderItem(
                order_id=order.id,
                product_id=p1.id,
                quantity=1,
                price_at_purchase=45.00
            ))
            db.session.commit()
            order_id = order.id

        # Login Alice
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)

        # Cancel order
        cancel_res = self.client.post(f"/my-orders/{order_id}/cancel", follow_redirects=True)
        self.assertEqual(cancel_res.status_code, 200)
        self.assertIn(b"refund was processed", cancel_res.data)

        # Verify DB state: order is cancelled, stock restored to 5
        with self.app.app_context():
            refunded_order = db.session.get(Order, order_id)
            self.assertEqual(refunded_order.status, "cancelled")
            self.assertEqual(refunded_order.refund_status, "processed")
            self.assertTrue(refunded_order.refund_id.startswith("rfnd_sim_"))

            p1 = db.session.get(Product, self.p1_id)
            self.assertEqual(p1.stock, 5)

    def test_wishlist_lifecycle(self):
        # Login Alice
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)

        # 1. Toggle product 1 into wishlist
        toggle_res = self.client.post(f"/wishlist/toggle/{self.p1_id}", follow_redirects=True)
        self.assertIn(b"Saved Minimalist Crewneck to your wishlist", toggle_res.data)

        # 2. View wishlist
        wishlist_page = self.client.get("/wishlist")
        self.assertIn(b"Minimalist Crewneck", wishlist_page.data)

        # 3. Move from wishlist to cart
        move_res = self.client.post(f"/wishlist/move-to-cart/{self.p1_id}", follow_redirects=True)
        self.assertIn(b"Moved Minimalist Crewneck from wishlist to your cart", move_res.data)

        # Verify it's in cart and out of wishlist
        with self.app.app_context():
            wish_entry = WishlistItem.query.filter_by(user_id=self.customer_id, product_id=self.p1_id).first()
            self.assertIsNone(wish_entry)

    def test_product_reviews_and_rating_aggregation(self):
        # Login Alice
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)

        # Submit a 5-star review
        rev_res = self.client.post(f"/product/{self.p1_id}/review", data={
            "rating": "5",
            "comment": "Absolutely love the fabric and texture!"
        }, follow_redirects=True)
        self.assertEqual(rev_res.status_code, 200)
        self.assertIn(b"Thank you! Your verified review has been posted", rev_res.data)

        # Verify rating in DB and product page
        with self.app.app_context():
            p1 = db.session.get(Product, self.p1_id)
            self.assertGreaterEqual(p1.reviews_count, 1)

        # View product detail page
        detail_res = self.client.get(f"/product/{self.p1_id}")
        self.assertIn(b"Alice Walker", detail_res.data)
        self.assertIn(b"fabric and texture", detail_res.data)

    def test_user_profile_and_password_update(self):
        # Login Alice
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)

        # Update profile shipping address and name
        prof_res = self.client.post("/profile", data={
            "name": "Alice W. Cooper",
            "email": "alice@test.com",
            "shipping_address": "888 Broadway, New York, NY"
        }, follow_redirects=True)
        self.assertIn(b"Your profile information has been updated successfully", prof_res.data)

        # Change password with wrong current password (should fail)
        fail_pass = self.client.post("/profile/password", data={
            "current_password": "incorrectpassword",
            "new_password": "brandnewpassword123",
            "confirm_new_password": "brandnewpassword123"
        }, follow_redirects=True)
        self.assertIn(b"Current password entered is incorrect", fail_pass.data)

        # Change password correctly
        success_pass = self.client.post("/profile/password", data={
            "current_password": "customerpass123",
            "new_password": "brandnewpassword123",
            "confirm_new_password": "brandnewpassword123"
        }, follow_redirects=True)
        self.assertIn(b"Your password has been changed securely", success_pass.data)

        # Verify login with new password
        self.client.get("/logout", follow_redirects=True)
        new_login = self.client.post("/login", data={
            "email": "alice@test.com",
            "password": "brandnewpassword123"
        }, follow_redirects=True)
        self.assertEqual(new_login.status_code, 200)
        self.assertIn(b"Alice W. Cooper", new_login.data)

    def test_admin_product_management_and_courier_tracking(self):
        # Login as Admin
        self.client.post("/admin/login", data={"username": "admin@test.com", "password": "adminpass123"}, follow_redirects=True)

        # 1. Admin adds a product
        add_res = self.client.post("/admin/products/add", data={
            "name": "Silk Camp Shirt",
            "category": "Shirts",
            "price": "68.00",
            "size": "M",
            "color": "Sage Green",
            "stock": 12,
            "description": "Luxurious breathable silk camp collar shirt."
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        with self.app.app_context():
            silk_shirt = Product.query.filter_by(name="Silk Camp Shirt").first()
            self.assertIsNotNone(silk_shirt)
            shirt_id = silk_shirt.id

        # 2. Admin edits the product
        edit_res = self.client.post(f"/admin/products/{shirt_id}/edit", data={
            "name": "Silk Camp Shirt - Relaxed",
            "category": "Shirts",
            "price": "72.00",
            "size": "L",
            "color": "Sage Green",
            "stock": 15,
            "image_url": "https://example.com/shirt.jpg",
            "description": "Updated silk shirt description.",
            "is_active": "y"
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        with self.app.app_context():
            updated_shirt = db.session.get(Product, shirt_id)
            self.assertEqual(updated_shirt.name, "Silk Camp Shirt - Relaxed")
            self.assertEqual(float(updated_shirt.price), 72.00)

        # 3. Admin toggles active status to draft
        toggle_res = self.client.post(f"/admin/products/{shirt_id}/toggle", follow_redirects=True)
        self.assertEqual(toggle_res.status_code, 200)

        with self.app.app_context():
            draft_shirt = db.session.get(Product, shirt_id)
            self.assertFalse(draft_shirt.is_active)

        # 4. Admin assigns courier tracking to an order
        with self.app.app_context():
            order = Order(
                customer_name="George",
                customer_email="george@test.com",
                shipping_address="505 Maple Ave",
                total_amount=72.00,
                status="paid"
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id

        tracking_res = self.client.post(f"/admin/orders/{order_id}/tracking", data={
            "courier_name": "FedEx Express",
            "tracking_number": "FEDEX-9988776655",
            "estimated_delivery": "2026-10-01",
            "admin_notes": "Priority express parcel"
        }, follow_redirects=True)
        self.assertEqual(tracking_res.status_code, 200)

        with self.app.app_context():
            tracked_order = db.session.get(Order, order_id)
            self.assertEqual(tracked_order.courier_name, "FedEx Express")
            self.assertEqual(tracked_order.tracking_number, "FEDEX-9988776655")
            self.assertEqual(tracked_order.status, "shipped")

        # 5. Check customer directory and LTV
        users_res = self.client.get("/admin/users")
        self.assertEqual(users_res.status_code, 200)
        self.assertIn(b"Customer Directory", users_res.data)

    def test_guest_order_lookup(self):
        # Create an unauthenticated guest order
        with self.app.app_context():
            guest_order = Order(
                customer_name="Guest Buyer",
                customer_email="guest@fashion.com",
                shipping_address="321 Oak St, Austin, TX",
                total_amount=45.00,
                status="shipped",
                courier_name="DHL Express",
                tracking_number="DHL-123456"
            )
            db.session.add(guest_order)
            db.session.commit()
            guest_order_id = guest_order.id

        # Lookup with correct Order ID and Email
        res = self.client.post("/order/lookup", data={
            "order_id": str(guest_order_id),
            "email": "guest@fashion.com"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"DHL-123456", res.data)
        self.assertIn(b"DHL Express", res.data)

        # Lookup with wrong email should fail gracefully
        fail_res = self.client.post("/order/lookup", data={
            "order_id": str(guest_order_id),
            "email": "wrongemail@fashion.com"
        }, follow_redirects=True)
        self.assertIn(b"No matching order found", fail_res.data)

    def test_demo_customer_and_admin_logins(self):
        # 1. Customer Demo Login (auto-initialized by db_init)
        cust_res = self.client.post("/login", data={
            "email": "customer@example.com",
            "password": "customer123"
        }, follow_redirects=True)
        self.assertEqual(cust_res.status_code, 200)
        self.assertIn(b"Alex Morgan", cust_res.data)

        self.client.get("/logout", follow_redirects=True)

        # 2. Admin Demo Login via /admin/login (auto-initialized by db_init)
        admin_res = self.client.post("/admin/login", data={
            "username": "admin@store.com",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b"Store Administrator", admin_res.data)
        self.assertIn(b"Admin Dashboard", admin_res.data)

    def test_order_confirmation_security_and_idor_protection(self):
        # Create a paid order for Alice
        with self.app.app_context():
            secret_order = Order(
                user_id=self.customer_id,
                customer_name="Alice Walker",
                customer_email="alice@test.com",
                shipping_address="123 Main St, New York, NY",
                total_amount=150.00,
                status="paid"
            )
            db.session.add(secret_order)
            db.session.commit()
            secret_order_id = secret_order.id

        # 1. An unauthenticated / stranger client trying to view Alice's order confirmation directly
        stranger_client = self.app.test_client()
        res = stranger_client.get(f"/order/{secret_order_id}/confirmation", follow_redirects=True)
        # Should be redirected to /order/lookup and prevented from seeing private details
        self.assertIn(b"order receipts are protected", res.data)
        self.assertNotIn(b"123 Main St, New York, NY", res.data)

        # 2. Alice logged in CAN view her own order confirmation
        self.client.post("/login", data={"email": "alice@test.com", "password": "customerpass123"}, follow_redirects=True)
        auth_res = self.client.get(f"/order/{secret_order_id}/confirmation", follow_redirects=True)
        self.assertEqual(auth_res.status_code, 200)
        self.assertIn(b"Order Confirmed", auth_res.data)
        self.assertIn(b"123 Main St, New York, NY", auth_res.data)

if __name__ == "__main__":
    unittest.main()
