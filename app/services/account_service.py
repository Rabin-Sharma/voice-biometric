import random
from app.models import db
from app.models.account import Account


class AccountService:
    def create_account(self, user_id):
        account_number = self._generate_account_number()
        account = Account(
            user_id=user_id, account_number=account_number, balance=0, account_type="checking"
        )
        db.session.add(account)
        db.session.commit()
        return account

    def _generate_account_number(self):
        return "".join([str(random.randint(0, 9)) for _ in range(10)])
