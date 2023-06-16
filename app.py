from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

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
        transactions = db.transactions.find().sort('date', -1).limit(4)
        # Prepare the data for the template
        dates = []
        types = []
        descriptions = []
        amounts = []
        for transaction in transactions:
            dates.append(transaction['date'])
            types.append(transaction['type'])
            descriptions.append(transaction['description'])
            amounts.append(transaction['amount'])
        return render_template('index.html', dates=dates, types=types, descriptions=descriptions, amounts=amounts)
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
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["username_give"]
        password_receive = request.form["password_give"]
        password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        print(f"Username received: {name_receive}")
        print(f"Password received: {password_receive}")
        new_doc = {
            "password": password_hash,
            "profile_name": name_receive,
            }

        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path

        db.users.update_one(
            {"username": payload["id"]},
            {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profile updated!"})
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

        # Retrieve data from form
        category_receive = request.form["category"]
        amount_receive = request.form["amount"]
        description_receive = request.form["description"]

        # Get current date
        current_date = datetime.now()

        # Construct transaction object
        transaction = {
            "username": payload["id"],
            "category": category_receive,
            "amount": float(amount_receive), # make sure amount is stored as a float/integer
            "description": description_receive,
            "date": current_date
        }

        # Insert the transaction into the database
        db.transactions.insert_one(transaction)

        return jsonify({"result": "success", "msg": "Transaction added successfully!"})
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
        return render_template("history.html", user_info=user_info)
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
        return jsonify({'message': 'Form submitted successfully'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
