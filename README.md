# AURA STUDIO — Haute Couture E-Commerce Platform

A production-ready luxury fashion storefront and back-office management system built with **Python (Flask)**, **SQLAlchemy**, and **Razorpay India Payment Gateway**. Crafted with a dark-mode editorial aesthetic, typography hierarchy (*Playfair Display*, *Cormorant Garamond*, *Plus Jakarta Sans*), multi-size garment selections, live order tracking, and role-separated admin dashboards.

---

## ✨ Features

### 🛍️ Luxury Customer Storefront
- **INR (₹) Native Currency**: Tailored for the Indian market with UPI (GPay, PhonePe, Paytm, BHIM), RuPay, Visa, Mastercard, and NetBanking badges.
- **Dynamic Size Selection**: Interactive sizing chips (`XS`, `S`, `M`, `L`, `XL`, `30`, `32`, `34`, `36`) tracked cleanly from product detail to cart, checkout, and order history.
- **Runway Lookbook & Collections**: Filter by categories (*Jackets*, *Hoodies*, *T-Shirts*, *Pants*, *Shirts*, *Sweaters*), search by keywords, and sort by price, novelty, and verified reviews.
- **Shopping Bag & Smart Clamping**: Real-time stock clamping, item size differentiation, and unified luxury quantity steppers.
- **Verified Product Reviews**: 5-star customer ratings and verified purchase feedback.
- **Member Accounts & Wishlist**: Personal order history, wishlist persistence, address book management, and 1-click order cancellation with instant inventory restock and refund tracking.
- **Guest Order Lookup**: Direct receipt and tracking lookup using Order ID and Email address.

### ⚡ Back-Office Admin Portal (`/admin/login`)
- **Executive Analytics**: Real-time Gross Revenue (INR), Total Orders, Paid vs. Shipped fulfillment metrics, Low Stock alerts, and Customer counts.
- **Order Dispatch & Courier Tracking**: Assign courier partners (*Blue Dart*, *Delhivery*, *FedEx*, *DHL*), tracking waybill numbers, and estimated delivery dates.
- **Catalog Management**: Add, edit, toggle drafts, upload high-res imagery, and manage size runs with archival protection for past orders.
- **Customer Directory & Access Control**: View customer lifetime value (LTV), promote administrators, and manage permissions.

---

## 🔐 Default Demo Accounts

Both customer and admin demo accounts are automatically seeded into the database upon startup with guaranteed 1-click login helpers.

| Role | Portal URL | Email / Username | Password | Access Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Demo Customer** | [`/login`](http://127.0.0.1:5000/login) | `customer@example.com` | `customer123` | Storefront, Wishlist, Order History, Checkout |
| **Secondary Customer** | [`/login`](http://127.0.0.1:5000/login) | `demo@example.com` | `demo123` | Storefront, Cart, Profile |
| **Store Administrator** | [`/admin/login`](http://127.0.0.1:5000/admin/login) | `admin@store.com` | `admin123` | Full Back-Office Admin Operations |
| **Legacy Admin** | [`/admin/login`](http://127.0.0.1:5000/admin/login) | `admin` | `admin123` | Full Back-Office Admin Operations |

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/fashion-storefront.git
cd fashion-storefront
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy the template file to `.env`:
```bash
cp .env.example .env
```
*(Optional: Add your Razorpay API test keys and custom `SECRET_KEY`)*

### 5. Seed the database (Optional, runs automatically)
```bash
python init_db.py
```

### 6. Run the application
```bash
python run.py
```
Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🌐 Production Hosting & Deployment

The application includes `Procfile`, flexible environment handling, and automatic database auto-migration for zero-downtime hosting on platforms like **Render**, **Railway**, **Fly.io**, or **Heroku**.

### Deploy to Render
1. Create a **New Web Service** linked to your GitHub repository.
2. Select **Python 3** environment.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn run:app`
5. Add Environment Variables:
   - `SECRET_KEY`: A secure random string
   - `RAZORPAY_KEY_ID`: Your Razorpay Key ID
   - `RAZORPAY_KEY_SECRET`: Your Razorpay Key Secret
   - `DATABASE_URL`: *(Optional)* Link a Render PostgreSQL database (defaults to SQLite if omitted)

### Deploy with Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
```

---

## ⚙️ Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask session cryptographic key | `aura-studio-luxury-secret-key-2026` |
| `DATABASE_URL` | PostgreSQL or custom database connection string | `sqlite:///storefront.db` |
| `RAZORPAY_KEY_ID` | Razorpay Merchant Key ID | Test Key |
| `RAZORPAY_KEY_SECRET` | Razorpay Merchant Key Secret | Test Secret |
| `PORT` | Web server listening port | `5000` |
| `FLASK_DEBUG` | Enable/disable Flask debug mode (`1` or `0`) | `1` |

---

## 🧪 Running Automated Tests

Run the comprehensive unit and integration test suite:
```bash
python test_auth_and_orders.py
```
Verifies customer registration, authentication, inventory stock deductions, order cancellations, refund automation, size validations, wishlist lifecycle, reviews, and courier tracking.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
