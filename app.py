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
        return render_template("index.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)

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
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),#ini 24 jam
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
        "profile_name": username_receive,                           # user's name is set to their id by default
        "profile_pic": "",                                          # profile image file name
        "profile_pic_real": "profile_pics/profile_placeholder.png", # a default profile image
        "profile_info": ""                                          # a profile description
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route("/sign_up/check_dup", methods=['POST'])
def check_dup():
    username_recieve = request.form.get('username_give')
    exists = bool(db.users.find_one({'username': username_recieve}))
    return jsonify({'result': 'success', 'exists': exists})

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
