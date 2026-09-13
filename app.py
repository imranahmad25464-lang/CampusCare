from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

import sqlite3
import os
import uuid

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = "campuscare_secret_key_2026"

DATABASE = "database/campuscare.db"

UPLOAD_FOLDER = "static/uploads"

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "mp4",
    "mov",
    "webm",
    "pdf"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# Create required folders
os.makedirs("database", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# FILE EXTENSION CHECK
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# DATABASE INITIALIZATION + MIGRATION
# =========================================================

def init_db():

    conn = get_db_connection()

    cursor = conn.cursor()

    # -----------------------------------------------------
    # USERS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            student_id TEXT UNIQUE,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)

    # -----------------------------------------------------
    # COMPLAINTS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            category TEXT NOT NULL,

            subject TEXT,

            class_section TEXT,

            description TEXT NOT NULL,

            location TEXT,

            status TEXT DEFAULT 'Pending',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            attachment TEXT,

            FOREIGN KEY (user_id)
            REFERENCES users(id)

        )
    """)

    # -----------------------------------------------------
    # CHECK EXISTING COLUMNS
    # -----------------------------------------------------

    cursor.execute("PRAGMA table_info(users)")

    user_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]

    cursor.execute("PRAGMA table_info(complaints)")

    complaint_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]

    # -----------------------------------------------------
    # USERS MIGRATION
    # -----------------------------------------------------

    if "student_id" not in user_columns:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN student_id TEXT
        """)

    # -----------------------------------------------------
    # COMPLAINT SUBJECT MIGRATION
    # -----------------------------------------------------

    if "subject" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN subject TEXT
        """)

        if "title" in complaint_columns:

            cursor.execute("""
                UPDATE complaints
                SET subject = title
                WHERE subject IS NULL
            """)

        else:

            cursor.execute("""
                UPDATE complaints
                SET subject = 'General Complaint'
                WHERE subject IS NULL
            """)

    else:

        # Fill empty subjects in an older database
        cursor.execute("""
            UPDATE complaints
            SET subject = 'General Complaint'
            WHERE subject IS NULL
               OR TRIM(subject) = ''
        """)

    # -----------------------------------------------------
    # CLASS / SECTION MIGRATION
    # -----------------------------------------------------

    if "class_section" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN class_section TEXT
        """)

        if "class" in complaint_columns:

            cursor.execute("""
                UPDATE complaints
                SET class_section = "class"
                WHERE class_section IS NULL
            """)

        elif "class_name" in complaint_columns:

            cursor.execute("""
                UPDATE complaints
                SET class_section = class_name
                WHERE class_section IS NULL
            """)

    # -----------------------------------------------------
    # LOCATION MIGRATION
    # -----------------------------------------------------

    if "location" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN location TEXT
        """)

    # -----------------------------------------------------
    # STATUS MIGRATION
    # -----------------------------------------------------

    if "status" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN status TEXT DEFAULT 'Pending'
        """)

        cursor.execute("""
            UPDATE complaints
            SET status = 'Pending'
            WHERE status IS NULL
        """)

    # -----------------------------------------------------
    # CREATED AT MIGRATION
    # -----------------------------------------------------

    if "created_at" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN created_at TIMESTAMP
        """)

        cursor.execute("""
            UPDATE complaints
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL
        """)

    # -----------------------------------------------------
    # ATTACHMENT MIGRATION
    # -----------------------------------------------------

    if "attachment" not in complaint_columns:

        cursor.execute("""
            ALTER TABLE complaints
            ADD COLUMN attachment TEXT
        """)

    # -----------------------------------------------------
    # ADMIN TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)

    # -----------------------------------------------------
    # DEFAULT ADMIN
    # -----------------------------------------------------

    admin_email = "admin@campuscare.com"

    admin_password = "Admin@123"

    cursor.execute(
        """
        SELECT id
        FROM admins
        WHERE email = ?
        """,
        (admin_email,)
    )

    admin_exists = cursor.fetchone()

    if not admin_exists:

        cursor.execute(
            """
            INSERT INTO admins
            (
                email,
                password
            )
            VALUES (?, ?)
            """,
            (
                admin_email,
                generate_password_hash(admin_password)
            )
        )

    conn.commit()

    conn.close()


# Initialize database
init_db()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Validation
        if not name or not student_id or not email or not password:

            flash(
                "Please fill all required fields.",
                "error"
            )

            return redirect(url_for("register"))

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(url_for("register"))

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return redirect(url_for("register"))

        conn = get_db_connection()

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
               OR student_id = ?
            """,
            (
                email,
                student_id
            )
        ).fetchone()

        if existing_user:

            conn.close()

            flash(
                "Email or Student ID already registered.",
                "error"
            )

            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users
            (
                name,
                student_id,
                email,
                password
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                student_id,
                email,
                hashed_password
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Registration successful! Please login.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db_connection()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["student_id"] = user["student_id"]

            session["user_email"] = user["email"]

            flash(
                "Login successful!",
                "success"
            )

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "error"
        )

        return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(url_for("login"))

    conn = get_db_connection()

    # Get student information
    user = conn.execute(
        """
        SELECT
            id,
            name,
            student_id,
            email
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    if not user:

        conn.close()

        session.clear()

        flash(
            "User account not found.",
            "error"
        )

        return redirect(url_for("login"))

    # Get complaint statuses
    complaints = conn.execute(
        """
        SELECT status
        FROM complaints
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    total_complaints = len(complaints)

    pending_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "Pending"
    )

    in_progress_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "In Progress"
    )

    resolved_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "Resolved"
    )

    return render_template(
        "dashboard.html",
        user=user,
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints
    )


# =========================================================
# SUBMIT COMPLAINT
# =========================================================

@app.route(
    "/submit-complaint",
    methods=["GET", "POST"]
)
def submit_complaint():

    if "user_id" not in session:

        return redirect(url_for("login"))

    if request.method == "POST":

        category = request.form.get(
            "category",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        class_section = request.form.get(
            "student_class",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not category:

            flash(
                "Please select a complaint category.",
                "error"
            )

            return redirect(url_for("submit_complaint"))

        if not subject:

            flash(
                "Please enter complaint subject.",
                "error"
            )

            return redirect(url_for("submit_complaint"))

        if not class_section:

            flash(
                "Please enter your Class / Section.",
                "error"
            )

            return redirect(url_for("submit_complaint"))

        if not description:

            flash(
                "Please describe your complaint.",
                "error"
            )

            return redirect(url_for("submit_complaint"))

        # -------------------------------------------------
        # FILE UPLOAD
        # -------------------------------------------------

        attachment_filename = None

        if "attachment" in request.files:

            file = request.files["attachment"]

            if file and file.filename:

                if not allowed_file(file.filename):

                    flash(
                        "This file type is not allowed.",
                        "error"
                    )

                    return redirect(
                        url_for("submit_complaint")
                    )

                original_filename = secure_filename(
                    file.filename
                )

                extension = ""

                if "." in original_filename:

                    extension = (
                        "."
                        + original_filename.rsplit(
                            ".",
                            1
                        )[1].lower()
                    )

                unique_filename = (
                    str(uuid.uuid4())
                    + extension
                )

                file.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        unique_filename
                    )
                )

                attachment_filename = unique_filename

        # -------------------------------------------------
        # SAVE COMPLAINT
        # -------------------------------------------------

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO complaints
            (
                user_id,
                category,
                subject,
                class_section,
                description,
                location,
                status,
                attachment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                category,
                subject,
                class_section,
                description,
                location,
                "Pending",
                attachment_filename
            )
        )

        conn.commit()

        conn.close()

        flash(
            "Complaint submitted successfully!",
            "success"
        )

        return redirect(
            url_for("my_complaints")
        )

    return render_template(
        "submit_complaint.html"
    )


# =========================================================
# MY COMPLAINTS
# =========================================================

@app.route("/my-complaints")
def my_complaints():

    if "user_id" not in session:

        return redirect(url_for("login"))

    conn = get_db_connection()

    complaints = conn.execute(
        """
        SELECT
            id,
            category,
            subject,
            class_section,
            description,
            location,
            status,
            created_at,
            attachment
        FROM complaints
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "my_complaints.html",
        complaints=complaints
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db_connection()

        admin = conn.execute(
            """
            SELECT *
            FROM admins
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):

            session.clear()

            session["admin_logged_in"] = True

            session["admin_email"] = admin["email"]

            flash(
                "Admin login successful!",
                "success"
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid admin email or password.",
            "error"
        )

        return redirect(
            url_for("admin_login")
        )

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):

        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    complaints = conn.execute(
        """
        SELECT
            complaints.id,
            complaints.category,
            complaints.subject,
            complaints.class_section,
            complaints.description,
            complaints.location,
            complaints.status,
            complaints.created_at,
            complaints.attachment,

            users.name AS student_name,
            users.student_id AS student_id,
            users.email AS student_email

        FROM complaints

        JOIN users
        ON complaints.user_id = users.id

        ORDER BY complaints.id DESC
        """
    ).fetchall()

    conn.close()

    total_complaints = len(complaints)

    pending_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "Pending"
    )

    in_progress_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "In Progress"
    )

    resolved_complaints = sum(
        1
        for complaint in complaints
        if complaint["status"] == "Resolved"
    )

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints
    )


# =========================================================
# UPDATE COMPLAINT STATUS
# =========================================================

@app.route(
    "/update-status/<int:complaint_id>",
    methods=["POST"]
)
def update_status(complaint_id):

    if not session.get("admin_logged_in"):

        return redirect(url_for("admin_login"))

    status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = {
        "Pending",
        "In Progress",
        "Resolved"
    }

    if status not in allowed_statuses:

        flash(
            "Invalid complaint status.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    conn = get_db_connection()

    conn.execute(
        """
        UPDATE complaints
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            complaint_id
        )
    )

    conn.commit()

    conn.close()

    flash(
        "Complaint status updated successfully.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# SERVE UPLOADED FILES
# =========================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "File is too large. Maximum allowed size is 100 MB.",
        "error"
    )

    return redirect(
        url_for("submit_complaint")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )

