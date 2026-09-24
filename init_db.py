from werkzeug.security import generate_password_hash
from app import create_app, db, DB_PATH
from app.models import Product, AdminUser, User, Review
from app.db_init import auto_initialize_db, PRODUCTS

app = create_app()


def run():
    print(f"Using database file: {DB_PATH}")
    auto_initialize_db(app)
    print("Database initialization, migrations, and seeding complete.")


if __name__ == "__main__":
    run()


if __name__ == "__main__":
    run()