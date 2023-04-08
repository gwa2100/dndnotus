from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from multiprocessing import cpu_count

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dnd_notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'some_secret_key'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    permissions = db.Column(db.Integer, default=1, nullable=False)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    dm_post = db.Column(db.Integer, default=False)


@app.before_first_request
def create_tables():
    db.create_all()


# Your routes and functions will go here
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def home():
    user = User.query.filter_by(username=session["username"]).first()
    if user.permissions >= 5:  #5+ is DM
        users_notes = []
        users = User.query.all()
        for user in users:
            user_notes = Note.query.filter_by(user_id=user.id).order_by(Note.date_posted.desc()).all()
            users_notes.append((user, user_notes))
    else:
        notes = Note.query.filter_by(user_id=user.id).order_by(Note.date_posted.desc()).all()
        users_notes = [(user, notes)]
    return render_template("home.html", users_notes=users_notes)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            session["user_id"] = user.id
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/note/new", methods=["GET", "POST"])
@login_required
def new_note():
    if request.method == "POST":
        content = request.form["content"]
        user = User.query.filter_by(username=session["username"]).first()
        note = Note(content=content, user_id=user.id)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("new_note.html")


@app.route("/dm_post", methods=["GET", "POST"])
@login_required
def dm_post():
    permissions = User.query.filter_by(username=session["username"]).first().permissions

    if permissions < 5:  # 5 and above are DM levels
        return redirect(url_for("home"))

    if request.method == "POST":
        content = request.form["content"]
        users = User.query.all()

        for user in users:
            note = Note(content=content, user_id=user.id, dm_post=True)
            db.session.add(note)

        db.session.commit()
        return redirect(url_for("home"))

    return render_template("dm_post.html")


@app.route("/delete_note/<int:note_id>", methods=["POST"])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)

    if note.user_id != session["user_id"] or note.dm_post:
        abort(403)  # Forbidden

    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("home"))

# @app.route("/dm_post", methods=["GET", "POST"])
# @login_required
# def dm_post():
#     if session["username"] != "dm_gwa2100":  # Replace "dm_user" with the actual DM's username
#         return redirect(url_for("home"))


if __name__ == '__main__':
    db.create_all()
    app.run(host="0.0.0.0", debug=True, processes=cpu_count())
