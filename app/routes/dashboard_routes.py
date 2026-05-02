from functools import wraps
from flask import Blueprint, jsonify, redirect, render_template, session, url_for
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction


dashboard_routes = Blueprint("dashboard_routes", __name__)


def login_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 401
        return handler(*args, **kwargs)

    return wrapper


@dashboard_routes.get("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("auth_routes.login_page"))
    return render_template("dashboard.html")


@dashboard_routes.get("/api/account")
@login_required
def account():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    account = Account.query.filter_by(user_id=user_id).first()

    if not user or not account:
        return jsonify({"error": "Account not found."}), 404

    return jsonify(
        {
            "full_name": user.full_name,
            "member_since": user.created_at.strftime("%Y-%m-%d"),
            "account_number": account.account_number,
            "account_type": account.account_type,
            "balance": float(account.balance),
        }
    )


@dashboard_routes.get("/api/transactions")
@login_required
def transactions():
    user_id = session.get("user_id")
    account = Account.query.filter_by(user_id=user_id).first()
    if not account:
        return jsonify({"error": "Account not found."}), 404

    items = (
        Transaction.query.filter_by(account_id=account.id)
        .order_by(Transaction.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify(
        {
            "transactions": [
                {
                    "type": item.type,
                    "amount": float(item.amount),
                    "description": item.description,
                    "balance_after": float(item.balance_after),
                    "created_at": item.created_at.strftime("%Y-%m-%d"),
                }
                for item in items
            ]
        }
    )
