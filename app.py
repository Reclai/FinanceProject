from pymongo import MongoClient
import jwt
import calendar
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, time

client = MongoClient("mongodb+srv://test:sparta@pymongolx.npweo5y.mongodb.net/?retryWrites=true&w=majority")
db = client["FinanceProject"]
SECRET_KEY = "SECRET_KEY"

app = Flask(__name__)

@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        # Fetch the latest 4 transactions sorted by date
        transactions = db.transactions.find({"username": payload["id"]}).sort([('date', -1), ('username', 1)]).limit(4)

        # Prepare the data for the template
        dates = []
        category = []
        descriptions = []
        amounts = []

        current_datetime = datetime.now()

        first_day_of_month = current_datetime.replace(day=1)

        # Print the modified datetime
        # print(first_day_of_month)
        # print(first_day_of_month.year)

        first_day_of_next_month = current_datetime.replace(day=1) + timedelta(days=32)

        # Set the month to the next month
        next_month = first_day_of_next_month.replace(day=1)

        # Print the modified datetime
        # print(next_month)


        start_date = datetime(first_day_of_month.year, first_day_of_month.month, first_day_of_month.day)
        end_date = datetime(first_day_of_next_month.year, first_day_of_next_month.month, first_day_of_next_month.day)

        # Buat permintaan pencarian
        query = {
            'date': {
            '$gte': start_date,
            '$lt': end_date
            }
        }

        # Lakukan pencarian
        results = db.transactions.find(query)

        # print(results)
        total_month = 0
        for month in results:
            if month["username"] == payload['id']:
                total_month += month['amount']

        times = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        today_db = db.transactions.find({"date": times})
        total_day = 0
        if today_db:
            for today in today_db:
                if today["username"] == payload["id"]:
                    total_day += today['amount']

        total_all = 0
        for transaction in transactions:
            dates.append(transaction['date'])
            category.append(transaction['category'])
            descriptions.append(transaction['description'])
            amounts.append(transaction['amount'])
            total_all += transaction['amount']

        return render_template('index.html', user_info=user_info,month=total_month,today=total_day,total_all=total_all, dates=dates, category=category, descriptions=descriptions, amounts=amounts)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)

@app.route("/user/<username>")
def user(username):
    # an endpoint for retrieving a user's profile information
    # and all of their posts
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # if this is my own profile, True
        # if this is somebody else's profile, False
        status = username == payload["id"]

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]

    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),  # ini 24 jam
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )

@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    doc = {
        "username": username_receive,                               # id
        "password": password_hash,                                  # password
        # user's name is set to their id by default
        "profile_name": username_receive,
        # profile image file name
        "profile_pic": "",
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # a default profile image
        # a profile description
        "profile_info": ""
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route("/sign_up/check_dup", methods=['POST'])
def check_dup():
    username_recieve = request.form.get('username_give')
    exists = bool(db.users.find_one({'username': username_recieve}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route("/update_profile", methods=["POST"])
def update_profile():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        display_name_receive = request.form["displayname"]
        old_password_receive = request.form["inputPassword"]
        new_password_receive = request.form["newPassword"]
        confirm_new_password_receive = request.form["confirmNewPassword"]

        if display_name_receive.strip() == "":
            return jsonify({"result": "fail", "msg": "Please enter a valid display name"})

        if old_password_receive.strip() != "":
            # Check if the old password is correct
            user = db.users.find_one({"username": username})
            old_password_hash = hashlib.sha256(old_password_receive.encode("utf-8")).hexdigest()
            if user["password"] != old_password_hash:
                return jsonify({"result": "fail", "msg": "Incorrect old password"})

        if old_password_receive.strip() == "" and new_password_receive.strip() == "" and confirm_new_password_receive.strip() == "":
            # Only updating the display name
            db.users.update_one(
                {"username": username},
                {"$set": {"profile_name": display_name_receive}}
            )
            return jsonify({"result": "success", "msg": "Display name updated successfully"})

        if old_password_receive.strip() != "" or new_password_receive.strip() != "" or confirm_new_password_receive.strip() != "":
            # Updating password and display name
            if new_password_receive != confirm_new_password_receive:
                return jsonify({"result": "fail", "msg": "New passwords do not match"})

            # Update the password in the database
            password_hash = hashlib.sha256(new_password_receive.encode("utf-8")).hexdigest()
            db.users.update_one(
                {"username": username},
                {"$set": {"password": password_hash, "profile_name": display_name_receive}}
            )
            return jsonify({"result": "success", "msg": "Display name and password updated successfully"})

        return jsonify({"result": "fail", "msg": "Please fill in all password fields"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/transaction")
def transaction():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template("transaction.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/addTransaction", methods=["POST"])
def addTransaction():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # Retrieve JSON data from the request
        data = request.get_json()
        date_receive = data["date"]
        category_receive = data["category"]
        description_receive = data["description"]
        amount_receive = data["amount"]
        date_datetime = datetime.strptime(date_receive, '%Y-%m-%d')

        # Get current date
        current_date = datetime.now()

        # Construct transaction object
        transaction = {
            "username": payload["id"],
            "date": date_datetime,
            "category": category_receive,
            "description": description_receive,
            "amount": float(amount_receive),  # make sure amount is stored as a float/integer
            "transaction_id": str(current_date)
        }

        # Insert the transaction into the database
        db.transactions.insert_one(transaction)

        return jsonify({"result": "success", "msg": "Transaction added successfully!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/deleteTransaction", methods=["POST"])
def deleteTransaction():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        transaction_id = request.form.get('transactionId')

        # Delete the transaction
        result = db.transactions.delete_one({"username": payload["id"], "transaction_id": transaction_id})
        if result.deleted_count == 1:
            return jsonify({"result": "success", "msg": "Transaction has been deleted!"})
        else:
            return jsonify({"result": "fail", "msg": "Transaction not found or unable to delete."})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/contact")
def contact():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template("contact.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/history")
def history():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        transactions = list(db.transactions.find({"username": payload["id"]},{'_id':False}))
        return render_template("history.html", user_info=user_info, transactions=transactions)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))


@app.route("/addContact", methods=['POST'])
def addContact():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])

        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        message = request.form.get('message')

        # Process the form data (e.g., send emails, store in a database, etc.)
        # Here, we'll simply print the data to the console
        contact = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'mobile': mobile,
            'message': message
        }
        db.contact.insert_one(contact)

        # Return a JSON response
        return jsonify({'result': 'success', 'msg': 'Form submitted successfully'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
