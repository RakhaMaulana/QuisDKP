import datetime
import uuid
import os
from flask import Flask, request, render_template, make_response, redirect

from peewee import *

db = SqliteDatabase("b.db")


class User(Model):
    id = AutoField()
    username = CharField(unique=True)
    password = CharField()
    token = CharField()
    balance = IntegerField()

    class Meta:
        database = db


class PurchaseLog(Model):
    id = AutoField()
    user_id = IntegerField()
    product_id = IntegerField()
    paid_amount = IntegerField()
    v_date = DateField(default=datetime.datetime.now)

    class Meta:
        database = db


class Product(Model):
    id = AutoField()
    name = CharField(unique=True)
    price = IntegerField()

    class Meta:
        database = db


@db.connection_context()
def initialize():
    db.create_tables([User, PurchaseLog, Product])
    for i in [
        {
            "name": "Galois Salad", "price": 5,
        },
        {
            "name": "Alpaca Salad", "price": 20,
        },
        {
            "name": "Flag", "price": 21,
        }
    ]:
        try:
            Product.create(name=i["name"], price=i["price"])
        except:
            pass


initialize()


class API:
    @staticmethod
    @db.connection_context()
    def login(username, password) -> str:
        user_objs = User \
            .select() \
            .where(User.username == username)
        if len(user_objs) == 0:
            token = str(uuid.uuid4())
            try:
                User.create(
                    username=username,
                    password=password,
                    token=token,
                    balance=20,
                )
            except IntegrityError as e:
                print(e)
                return ""
            return token
        user_obj = user_objs[0]
        if user_obj.password != password:
            return ""
        return user_obj.token

    @staticmethod
    @db.connection_context()
    def get_user_detail_by_token(token: str) -> (bool, int, [PurchaseLog]):
        user_objs = User \
            .select() \
            .where(User.token == token)
        if len(user_objs) == 0:
            return False, 0, None
        user_obj = user_objs[0]
        purchase_log = PurchaseLog \
            .select() \
            .where(PurchaseLog.user_id == user_obj.id)
        return True, user_obj.balance, [x for x in purchase_log]

    @staticmethod
    @db.connection_context()
    def buy(product_id: int) -> (bool, str):
        try:
            with db.atomic():
                product_obj = Product.get_or_none(Product.id == product_id)
                if not product_obj:
                    return False, "No such product"

                # Mendapatkan id pengguna dari token
                token = request.cookies.get("token")
                user_objs = User.select().where(User.token == token)
                if len(user_objs) == 0:
                    return False, "User not found"
                user_id = user_objs[0].id

                # Mendapatkan saldo pengguna dan mengunci baris pengguna
                user_obj = User.select().where(User.id == user_id).for_update().get()
                if product_obj.price > user_obj.balance:
                    return False, "Not enough balance"

                # Check user balance before purchasing
                initial_balance = user_obj.balance

                PurchaseLog.create(
                    user_id=user_obj.id,
                    product_id=product_obj.id,
                    paid_amount=product_obj.price
                )

                # Check user balance after purchasing
                final_balance = User.get(User.id == user_obj.id).balance

                if initial_balance - product_obj.price != final_balance:
                    return False, "Balance changed unexpectedly"

                # Update user balance
                user_obj.balance -= product_obj.price
                user_obj.save()
        except IntegrityError as e:
            db.rollback()
            print(e)
            return False, "Transaction failed, database rolled back"

        return True, ""


    @staticmethod
    @db.connection_context()
    def sell(purchase_id: int) -> (bool, str):
        try:
            with db.atomic():
                purchase_history_obj = PurchaseLog.get_or_none(PurchaseLog.id == purchase_id)
                if not purchase_history_obj:
                    return False, "No such purchase"

                user_obj = User.select_for_update().get()  # Locking user row for update
                if purchase_history_obj.user_id != user_obj.id:
                    return False, "Not the purchase you made"

                PurchaseLog.delete().where(PurchaseLog.id == purchase_history_obj.id).execute()

                # Update user balance
                user_obj.balance += purchase_history_obj.paid_amount
                user_obj.save()

                if purchase_history_obj.paid_amount == 21:
                    return False, f"Well, flag is {os.getenv('FLAG')}"
        except IntegrityError as e:
            db.rollback()
            print(e)
            return False, "Transaction failed, database rolled back"

        return True, ""


app = Flask(__name__)


@app.route('/', methods=["GET", "POST"])
def default():
    if request.method == 'POST':
        token = API.login(request.form["username"], request.form["password"])
        if token:
            resp = make_response(redirect("/"))
            resp.set_cookie("token", token)
            return resp
        else:
            return render_template('login.html',
                                   error_msg="Wrong credential")
        pass
    else:
        token = request.cookies.get("token")

        def go_login():
            return render_template('login.html')

        if token and len(token) > 5:
            is_login, balance, purchase_log = API.get_user_detail_by_token(token)
            if not is_login:
                resp = make_response(redirect("/"))
                resp.set_cookie("token", "")
                return resp
            return render_template('home.html', balance=balance, purchase_log=purchase_log)
        return go_login()


@app.route('/buy/<product_id>', methods=["GET"])
def buy(product_id):
    is_success, err_message = API.buy(int(product_id))
    if is_success:
        return make_response(redirect("/"))
    else:
        return err_message


@app.route('/sell/<purchase_id>', methods=["GET"])
def sell(purchase_id):
    is_success, err_message = API.sell(int(purchase_id))
    if is_success:
        return make_response(redirect("/"))
    else:
        return err_message
