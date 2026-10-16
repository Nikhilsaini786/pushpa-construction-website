import base64
import os
import re
import sqlite3
import time
import uuid
from decimal import Decimal, InvalidOperation
from functools import wraps

import pymysql
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, redirect, render_template, request,
    session, url_for
)
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from openai import OpenAI
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "pushpa-construction-secret-2026")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def get_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="pushpa-pwd-reset")


def get_sqlite_path():
    if os.environ.get("VERCEL"):
        return "/tmp/construction_db.sqlite"
    return os.path.join(app.root_path, "construction_db.sqlite")


def init_sqlite(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            project_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed Admin accounts if missing
    cur.execute("SELECT id FROM users WHERE email='admin@example.com'")
    if not cur.fetchone():
        admin_pass = generate_password_hash("ChangeThisAdminPassword123!")
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Pushpa Admin", "admin@example.com", admin_pass)
        )
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            ("Nikhil Saini", "nikhilsaini@gmail.com", admin_pass)
        )

    # Seed default projects if empty
    cur.execute("SELECT COUNT(*) FROM projects")
    count = cur.fetchone()[0]
    if count == 0:
        seed = [
            ("Pushpa Heights - Luxury Residential Villa", "Residential", "3-storey premium residential project with high-grade RCC frame, designer elevation, and bespoke interior finishes in Vaishali Nagar, Jaipur.", "/static/image/project-1.jpg"),
            ("Shree Ram Commercial Complex", "Commercial", "Modern G+3 commercial building with glass facade, heavy-load floor plates, and automated basement parking in Mansarovar, Jaipur.", "/static/image/project-2.jpg"),
            ("Royal Palm Turnkey Villa", "Turnkey Construction", "End-to-end architectural planning, RCC structure, plumbing, electrical, and turnkey delivery completed within 9 months in Jagatpura, Jaipur.", "/static/image/project-3.jpg"),
            ("Modern Haveli Elevation & Renovation", "Renovation", "Heritage Rajasthani architectural fusion with modern minimalist interiors, Dholpur sandstone jali, and open courtyard design in C-Scheme, Jaipur.", "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"),
            ("Skyline Corporate Tower", "Commercial", "Reinforced concrete commercial office spaces with energy-efficient ventilation, firefighting systems, and high-speed elevators on Tonk Road, Jaipur.", "https://images.unsplash.com/photo-1541888946425-d0fbb18615f3?auto=format&fit=crop&w=1200&q=80"),
            ("Green Meadows Luxury Duplex", "Residential", "Sustainable duplex villa featuring rooftop solar pergola, rainwater harvesting, Vastu-compliant layout, and Italian marble flooring on Sirsi Road, Jaipur.", "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=80")
        ]
        for p in seed:
            cur.execute("INSERT INTO projects (title, category, description, image_url) VALUES (?, ?, ?, ?)", p)

    conn.commit()


def db_connection():
    if os.getenv("USE_SQLITE", "").lower() in ("true", "1") or (
        os.getenv("VERCEL") and not os.getenv("DB_HOST")
    ):
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row
        init_sqlite(conn)
        return conn, "sqlite"

    try:
        connect_kwargs = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "construction_db"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": False,
            "connect_timeout": 3,
        }
        if os.getenv("DB_SSL", "").lower() in ("true", "1"):
            connect_kwargs["ssl"] = {"ssl_disabled": False}

        conn = pymysql.connect(**connect_kwargs)
        return conn, "mysql"
    except Exception as e:
        app.logger.warning(f"MySQL connection unavailable ({e}). Using embedded SQLite storage.")
        conn = sqlite3.connect(get_sqlite_path())
        conn.row_factory = sqlite3.Row
        init_sqlite(conn)
        return conn, "sqlite"


def query_all(sql, params=()):
    conn, engine = db_connection()
    try:
        if engine == "mysql":
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(sql.replace("%s", "?"), params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    conn, engine = db_connection()
    try:
        if engine == "mysql":
            with conn.cursor() as cur:
                cur.execute(sql, params)
                result = cur.lastrowid
            conn.commit()
            return result
        else:
            cur = conn.cursor()
            cur.execute(sql.replace("%s", "?"), params)
            result = cur.lastrowid
            conn.commit()
            return result
    except (pymysql.err.IntegrityError, sqlite3.IntegrityError):
        conn.rollback()
        raise pymysql.err.IntegrityError(1062, "Duplicate entry")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def current_user():
    if not session.get("user_id"):
        return None
    return query_one(
        "SELECT id, name, email, role FROM users WHERE id=%s",
        (session["user_id"],)
    )


def is_admin():
    if not session.get("user_id"):
        return False
    if session.get("role") == "admin":
        return True
    raw_admins = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_emails = {e.strip().lower() for e in raw_admins.split(",") if e.strip()}
    return session.get("email", "").lower() in admin_emails


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to the Admin Portal to continue.", "info")
            return redirect(url_for("admin_login", next=request.path))
        if not is_admin():
            flash("Access denied. Administrator privileges required.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"nav_user": current_user(), "nav_is_admin": is_admin()}


@app.route("/")
def home():
    projects = query_all(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT 3"
    )
    return render_template("index.html", projects=projects)


@app.route("/projects")
def projects():
    rows = query_all("SELECT * FROM projects ORDER BY created_at DESC")
    return render_template("projects.html", projects=rows)


@app.route("/calculator", methods=["GET", "POST"])
def calculator():
    result = None
    if request.method == "POST":
        try:
            area = Decimal(request.form.get("area", "0"))
            floors = int(request.form.get("floors", "1"))
            rate = Decimal(request.form.get("rate", "0"))
            if area <= 0 or rate <= 0 or floors < 1 or floors > 10:
                raise ValueError
            total_area = area * floors
            estimated_cost = total_area * rate

            # AI Jaipur Construction Material & Resource Estimations
            cement_bags = int(total_area * Decimal("0.42"))
            steel_tons = round(float(total_area * Decimal("3.8") / Decimal("1000")), 2)
            bricks_count = int(total_area * Decimal("8.5"))
            sand_cuft = int(total_area * Decimal("1.8"))
            aggregate_cuft = int(total_area * Decimal("1.35"))
            duration_months = max(4, min(24, int(total_area / Decimal("450")) + (floors * 2)))

            result = {
                "area_per_floor": area,
                "floors": floors,
                "area": total_area,
                "rate": rate,
                "cost": estimated_cost,
                "cement_bags": cement_bags,
                "steel_tons": steel_tons,
                "bricks_count": bricks_count,
                "sand_cuft": sand_cuft,
                "aggregate_cuft": aggregate_cuft,
                "duration_months": duration_months,
            }
        except (InvalidOperation, ValueError, TypeError):
            flash("Enter a valid area, rate, and floor count.", "error")
    return render_template("calculator.html", result=result)



@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        project_type = request.form.get("project_type", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, phone, project_type, message]):
            flash("Please fill in every field.", "error")
        elif len(name) > 120 or len(email) > 190 or len(message) > 5000:
            flash("Some fields are too long. Please shorten them.", "error")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address.", "error")
        else:
            execute(
                """INSERT INTO enquiries
                   (name, email, phone, project_type, message)
                   VALUES (%s, %s, %s, %s, %s)""",
                (name, email, phone[:30], project_type, message)
            )
            flash("Thanks! Your enquiry has been submitted.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        raw_admins = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_emails = {e.strip().lower() for e in raw_admins.split(",") if e.strip()}

        if not name or not email or not password:
            flash("Please complete all fields.", "error")
        elif len(name) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid name and email address.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif email in admin_emails:
            flash("That email address is reserved for system administrators.", "error")
        else:
            try:
                user_id = execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'customer')",
                    (name, email, generate_password_hash(password))
                )
                session.clear()
                session["user_id"] = user_id
                session["email"] = email
                session["role"] = "customer"
                flash("Your customer account has been created successfully!", "success")
                return redirect(url_for("home"))
            except pymysql.err.IntegrityError:
                flash("An account with that email already exists.", "error")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
@app.route("/customer/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        if is_admin():
            return redirect(url_for("admin"))
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one(
            "SELECT id, name, email, role, password_hash FROM users WHERE email=%s",
            (email,)
        )
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["role"] = user.get("role", "customer")
            flash(f"Welcome back, {user['name']}!", "success")
            if is_admin():
                return redirect(url_for("admin"))
            return redirect(url_for("home"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_id") and is_admin():
        return redirect(url_for("admin"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one(
            "SELECT id, name, email, role, password_hash FROM users WHERE email=%s",
            (email,)
        )
        if user and check_password_hash(user["password_hash"], password):
            raw_admins = os.getenv("ADMIN_EMAIL", "admin@example.com")
            admin_emails = {e.strip().lower() for e in raw_admins.split(",") if e.strip()}
            user_role = user.get("role", "customer")

            if user_role == "admin" or email in admin_emails:
                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["role"] = "admin"
                flash("Administrator authenticated successfully. Welcome to the Control Panel!", "success")
                next_url = request.args.get("next")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect(url_for("admin"))
            else:
                flash("Access denied: This account is not an administrator. Please use the Customer Login.", "error")
                return redirect(url_for("login"))
        flash("Invalid administrator email or password.", "error")
    return render_template("admin_login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_link = None
    target_email = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your registered email address.", "error")
        else:
            user = query_one("SELECT id, name, email, role FROM users WHERE email=%s", (email,))
            if user:
                s = get_serializer()
                token = s.dumps(user["email"])
                reset_link = url_for("reset_password", token=token, _external=True)
                target_email = user["email"]
                flash("Password reset link generated successfully! Click the link below to set your new password.", "success")
            else:
                flash("No account registered with that email address. Please check and try again.", "error")
    return render_template("forgot_password.html", reset_link=reset_link, target_email=target_email)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = get_serializer()
    try:
        email = s.loads(token, max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        flash("The password reset link has expired or is invalid. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))

    user = query_one("SELECT id, name, email, role FROM users WHERE email=%s", (email,))
    if not user:
        flash("User account not found.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not password or len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (generate_password_hash(password), user["id"])
            )
            flash("Your password has been successfully reset! Please log in now.", "success")
            raw_admins = os.getenv("ADMIN_EMAIL", "admin@example.com")
            admin_emails = {e.strip().lower() for e in raw_admins.split(",") if e.strip()}
            if user.get("role") == "admin" or user["email"] in admin_emails:
                return redirect(url_for("admin_login"))
            return redirect(url_for("login"))

    return render_template("reset_password.html", email=email, token=token)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin():
    projects = query_all("SELECT * FROM projects ORDER BY created_at DESC")
    enquiries = query_all("SELECT * FROM enquiries ORDER BY created_at DESC")
    users = query_all(
        "SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC"
    )
    return render_template(
        "admin.html", projects=projects, enquiries=enquiries, users=users
    )


@app.route("/admin/projects/add", methods=["POST"])
@admin_required
def add_project():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    image_url = request.form.get("image_url", "").strip()

    if not title or not category or not description:
        flash("Title, category, and description are required.", "error")
        return redirect(url_for("admin"))

    if len(title) > 160 or len(category) > 80:
        flash("Title or category is too long.", "error")
        return redirect(url_for("admin"))

    # Direct image upload handling
    file = request.files.get("image_file")
    if file and file.filename:
        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            flash("Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP, GIF.", "error")
            return redirect(url_for("admin"))

        unique_name = f"project_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
        try:
            upload_folder = os.path.join(app.root_path, "static", "image", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, unique_name))
            image_url = f"/static/image/uploads/{unique_name}"
        except OSError:
            flash("Local file uploads are disabled on serverless hosting. Please provide an Image URL instead.", "error")
            return redirect(url_for("admin"))
    elif image_url:
        if not (image_url.startswith(("http://", "https://", "/static/"))):
            flash("Image URL must start with http://, https://, or /static/.", "error")
            return redirect(url_for("admin"))
    else:
        image_url = ""

    execute(
        """INSERT INTO projects (title, category, description, image_url)
           VALUES (%s, %s, %s, %s)""",
        (title, category, description, image_url)
    )
    flash(f"Project '{title}' has been successfully added to the website!", "success")
    return redirect(url_for("admin"))


@app.route("/admin/projects/<int:project_id>/delete", methods=["POST"])
@admin_required
def delete_project(project_id):
    proj = query_one("SELECT * FROM projects WHERE id=%s", (project_id,))
    if proj:
        # If it was an uploaded file in static/image/uploads/, clean it up
        if proj.get("image_url", "").startswith("/static/image/uploads/"):
            filepath = os.path.join(app.root_path, proj["image_url"].lstrip("/"))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        execute("DELETE FROM projects WHERE id=%s", (project_id,))
        flash(f"Project '{proj['title']}' deleted successfully.", "success")
    else:
        flash("Project not found.", "error")
    return redirect(url_for("admin"))


@app.route("/admin/enquiries/<int:enquiry_id>/delete", methods=["POST"])
@admin_required
def delete_enquiry(enquiry_id):
    execute("DELETE FROM enquiries WHERE id=%s", (enquiry_id,))
    flash("Customer enquiry deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/ai-design", methods=["GET", "POST"])
def ai_design():
    image_data = None
    prompt_used = ""
    if request.method == "POST":
        prompt_used = request.form.get("prompt", "").strip()
        if not prompt_used:
            flash("Describe the house design first.", "error")
        elif len(prompt_used) > 1000:
            flash("Please keep the prompt under 1000 characters.", "error")
        elif not os.getenv("OPENAI_API_KEY"):
            flash("AI design is not configured yet. Add OPENAI_API_KEY to your .env file.", "error")
        else:
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response = client.images.generate(
                    model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
                    prompt=(
                        "Create a high-quality architectural concept visualization "
                        "of a house. This is an inspirational concept, not a construction "
                        "blueprint. Include no text or watermark. User brief: " + prompt_used
                    ),
                    size="1024x1024",
                )
                image_data = response.data[0].b64_json
                if not image_data:
                    flash("The image service returned no image. Please try again.", "error")
            except Exception:
                app.logger.exception("AI image generation failed")
                flash("Image generation failed. Check your API key, account access, and API billing, then try again.", "error")
    return render_template("ai_design.html", image_data=image_data, prompt_used=prompt_used)


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403,
                           message="This page is for the administrator only."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404,
                           message="The page you requested could not be found."), 404



if __name__ == "__main__":
    app.run(debug=True, port=9002)
