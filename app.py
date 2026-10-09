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

class HealthCenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ward = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    services = db.Column(db.String(250), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    hours = db.Column(db.String(100), default="24/7 Service")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Database Initialization & Default Admin / Center Seeding ---
default_admin_username = os.environ.get('ADMIN_USERNAME', 'BHCAPSI')
default_admin_password = os.environ.get('ADMIN_PASSWORD', 'Bichi@123')

with app.app_context():
    db.create_all()
    
    # Seed default admin if missing
    if not User.query.filter_by(username=default_admin_username).first():
        admin = User(username=default_admin_username)
        admin.set_password(default_admin_password)
        db.session.add(admin)
        db.session.commit()

    # Seed initial health centers if empty
    if not HealthCenter.query.first():
        initial_centers = [
            HealthCenter(
                name="Bichi General Hospital",
                ward="Bichi Ward",
                address="Kano-Katsina Road, Bichi Town",
                services="Comprehensive ART, HTS, PMTCT, Viral Load Testing, STI Treatment",
                phone="+234 800 000 0001",
                hours="24/7 Emergency & Clinic"
            ),
            HealthCenter(
                name="Badume Primary Health Care Center",
                ward="Badume Ward",
                address="Badume Central Road, near Market Square",
                services="HIV Testing & Counseling (HTS), PMTCT, Counseling, First Aid",
                phone="+234 800 000 0002",
                hours="8:00 AM - 4:00 PM (Daily)"
            ),
            HealthCenter(
                name="Danzabuwa Comprehensive Health Center",
                ward="Danzabuwa Ward",
                address="Danzabuwa Main Expressway",
                services="HTS, ART Refill Station, Maternal & Child Health, PMTCT",
                phone="+234 800 000 0003",
                hours="24/7 Service"
            ),
            HealthCenter(
                name="Fagwalawa Primary Health Post",
                ward="Fagwalawa Ward",
                address="Fagwalawa Central",
                services="Confidential HIV Counseling, Screening, TB/HIV Co-infection Clinic",
                phone="+234 800 000 0004",
                hours="8:00 AM - 4:00 PM (Mon-Fri)"
            ),
            HealthCenter(
                name="Saye Model Primary Health Care",
                ward="Saye Ward",
                address="Saye Town Center",
                services="HTS, PMTCT, Family Planning, Community Referral",
                phone="+234 800 000 0005",
                hours="24/7 Service"
            ),
        ]
        db.session.add_all(initial_centers)
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
        is_anonymous = request.form.get("is_anonymous") == "on"
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message_body = request.form.get("message", "").strip()

        # Handle anonymous option
        if is_anonymous:
            name = "Anonymous Community Member"
            email = "Not Provided (Anonymous)"
        else:
            if not name or not email:
                flash("Please provide your name and email, or check 'Submit Anonymously'.", "danger")
                return redirect(url_for("contact"))

        # Subject and message are always required
        if not subject or not message_body:
            flash("Please fill in the subject and message fields.", "danger")
            return redirect(url_for("contact"))

        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message_body
        )
        db.session.add(new_message)
        db.session.commit()
        
        flash("Thank you! Your confidential message has been received.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/resources")
def resources():
    faqs = [
        {
            "question": "What HIV services are available in Bichi LGA?",
            "answer": "BHCAPSI supports free HIV Testing & Counseling (HTS), Prevention of Mother-to-Child Transmission (PMTCT), ART medication refills, STI screening, and confidential counseling across supported primary health facilities in Bichi LGA."
        },
        {
            "question": "Are HIV testing and counseling really free and confidential?",
            "answer": "Yes. All testing and counseling services at supported centers are 100% free of charge. Patient records and test results are kept strictly confidential under national medical privacy guidelines."
        },
        {
            "question": "What does PMTCT mean for pregnant women?",
            "answer": "PMTCT (Prevention of Mother-to-Child Transmission) ensures that pregnant mothers living with HIV receive anti-retroviral treatment (ART). When taken consistently, treatment reduces the risk of transmitting HIV to the baby to less than 1% during pregnancy, delivery, and breastfeeding."
        },
        {
            "question": "What does Undetectable = Untransmittable (U=U) mean?",
            "answer": "When a person living with HIV takes prescribed ART daily, the amount of virus in their blood drops to undetectable levels. Research shows that individuals with an undetectable viral load cannot transmit HIV through sexual contact."
        },
        {
            "question": "Where can I receive counseling or ART refills in Bichi?",
            "answer": "You can visit any of our listed facilities in the Health Center Directory, such as Bichi General Hospital, Badume PHC, Danzabuwa Comprehensive Health Center, or Saye Model PHC."
        }
    ]
    return render_template("resources.html", faqs=faqs)

@app.route("/centers")
def centers():
    all_centers = HealthCenter.query.order_by(HealthCenter.ward, HealthCenter.name).all()
    return render_template("centers.html", centers=all_centers)

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

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            flash("All password fields are required.", "danger")
            return redirect(url_for("change_password"))

        if not current_user.check_password(current_password):
            flash("Incorrect current password. Please try again.", "danger")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        current_user.set_password(new_password)
        db.session.commit()

        flash("Your password has been updated successfully!", "success")
        return redirect(url_for("view_messages"))

    return render_template("change_password.html")

@app.route("/register", methods=["GET", "POST"])
@login_required
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

        flash(f"Account for '{username}' created successfully!", "success")
        return redirect(url_for("view_messages"))

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

# --- Protected Admin Health Center CRUD Routes ---

@app.route("/admin/centers", methods=["GET"])
@login_required
def admin_centers():
    centers = HealthCenter.query.order_by(HealthCenter.ward, HealthCenter.name).all()
    edit_id = request.args.get('edit', type=int)
    center_to_edit = HealthCenter.query.get(edit_id) if edit_id else None
    return render_template("admin_centers.html", centers=centers, center_to_edit=center_to_edit)

@app.route("/admin/centers/add", methods=["POST"])
@login_required
def add_center():
    name = request.form.get("name", "").strip()
    ward = request.form.get("ward", "").strip()
    address = request.form.get("address", "").strip()
    services = request.form.get("services", "").strip()
    phone = request.form.get("phone", "").strip()
    hours = request.form.get("hours", "").strip() or "24/7 Service"

    if not name or not ward or not address or not services:
        flash("Facility Name, Ward, Address, and Services are required.", "danger")
        return redirect(url_for("admin_centers"))

    new_center = HealthCenter(
        name=name,
        ward=ward,
        address=address,
        services=services,
        phone=phone,
        hours=hours
    )
    db.session.add(new_center)
    db.session.commit()
    flash(f"Health center '{name}' added successfully!", "success")
    return redirect(url_for("admin_centers"))

@app.route("/admin/centers/edit/<int:id>", methods=["POST"])
@login_required
def edit_center(id):
    center = HealthCenter.query.get_or_404(id)
    center.name = request.form.get("name", "").strip()
    center.ward = request.form.get("ward", "").strip()
    center.address = request.form.get("address", "").strip()
    center.services = request.form.get("services", "").strip()
    center.phone = request.form.get("phone", "").strip()
    center.hours = request.form.get("hours", "").strip() or "24/7 Service"

    if not center.name or not center.ward or not center.address or not center.services:
        flash("Facility Name, Ward, Address, and Services are required.", "danger")
        return redirect(url_for("admin_centers", edit=id))

    db.session.commit()
    flash(f"Health center '{center.name}' updated successfully!", "success")
    return redirect(url_for("admin_centers"))

@app.route("/admin/centers/delete/<int:id>", methods=["POST"])
@login_required
def delete_center(id):
    center = HealthCenter.query.get_or_404(id)
    db.session.delete(center)
    db.session.commit()
    flash(f"Health center '{center.name}' deleted successfully.", "success")
    return redirect(url_for("admin_centers"))

if __name__ == "__main__":
    app.run(debug=True)