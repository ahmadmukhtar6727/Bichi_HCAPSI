import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- App Configurations ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-goes-here')

# Dynamic Database Configuration (Render PostgreSQL in production vs local SQLite fallback)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

# Fix SQLAlchemy 1.4+ compatibility with Render's postgres:// prefix
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database Extension
db = SQLAlchemy(app)

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Database Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Database Initialization & Default Admin Seeding ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# --- Public Routes ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message_body = request.form.get("message")

        if not name or not email or not message_body:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("contact"))

        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message_body
        )
        db.session.add(new_message)
        db.session.commit()
        
        flash("Thank you! Your message has been received.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

# --- Authentication Routes ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("view_messages"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for("view_messages"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Please pick a different one.", "danger")
            return redirect(url_for("register"))

        new_admin = User(username=username)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()

        flash(f"Account for '{username}' created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# --- Protected Admin Routes ---

@app.route("/admin/messages")
@login_required
def view_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin_messages.html", messages=messages)

@app.route("/admin/messages/delete/<int:id>", methods=["POST"])
@login_required
def delete_message(id):
    msg = ContactMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted successfully.", "success")
    return redirect(url_for("view_messages"))

if __name__ == "__main__":
    app.run(debug=True)