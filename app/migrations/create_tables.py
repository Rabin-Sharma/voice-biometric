from app import create_app
from app.models import db
from app.models.account import Account
from app.models.login_attempt import LoginAttempt
from app.models.transaction import Transaction
from app.models.user import User


app = create_app(register_routes=False)


def main():
    with app.app_context():
        db.create_all()
        print("Database tables created.")


if __name__ == "__main__":
    main()
