import os
import json
import hmac
import ssl
import smtplib
import logging
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

import mysql.connector
from mysql.connector import Error as MySQLError

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort, g
)
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv


# =============================================================
# 1. CONFIGURATION
# =============================================================

load_dotenv()

app = Flask(__name__)

ENVIRONMENT = os.getenv("DAIRYMITR_ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY", "")

if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("change-me"):
    raise RuntimeError(
        "Set a strong SECRET_KEY (at least 32 characters) in your .env file."
    )

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=(
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "0" if ENVIRONMENT == "development" else "1"
        ) == "1"
    ),
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    WTF_CSRF_TIME_LIMIT=3600,
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)

proxy_hops = int(os.getenv(
    "TRUST_PROXY_HOPS",
    "1" if ENVIRONMENT == "production" else "0"
))

if proxy_hops > 0:
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=proxy_hops,
        x_proto=proxy_hops,
        x_host=proxy_hops,
    )


# =============================================================
# 2. LOGGING
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("dairymitra_superadmin")


# =============================================================
# PLATFORM MONITORING CORE
# =============================================================
# Creates its own tables in the existing DairyMitr MySQL database.
# The main DairyMitr app sends events to /api/monitoring/event.
# Never include passwords, OTP values, tokens or secrets in event details.

MONITORING_INGEST_TOKEN = os.getenv("MONITORING_INGEST_TOKEN", "").strip()
MONITORING_ALERT_EMAIL = os.getenv("MONITORING_ALERT_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME).strip()
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "0") == "1"
_monitoring_ready = False

EVENT_RULES = {
    "dairy_registered": ("WARNING", "New Dairy Owner Registration"),
    "dairy_first_login": ("INFO", "New Dairy Owner First Login"),
    "login_new_device": ("WARNING", "Dairy Owner Login from New Device"),
    "login_new_ip": ("WARNING", "Dairy Owner Login from New IP"),
    "dairy_verified": ("INFO", "Dairy Owner Account Verified"),
    "dairy_deleted": ("CRITICAL", "Dairy Owner Account Deleted"),
    "multiple_accounts_same_ip": ("WARNING", "Multiple Accounts from Same IP"),
    "wrong_password": ("WARNING", "Wrong Password Attempt"),
    "otp_request": ("INFO", "OTP Requested"),
    "wrong_otp": ("WARNING", "Wrong OTP Attempt"),
    "password_reset_request": ("INFO", "Password Reset Requested"),
    "superadmin_failed_login": ("CRITICAL", "Failed Super Admin Login"),
    "superadmin_login": ("INFO", "Super Admin Login"),
    "vendor_added": ("INFO", "New Vendor Added"),
    "staff_added": ("INFO", "New Staff Added"),
    "vendor_deleted": ("WARNING", "Vendor Deleted"),
    "staff_deleted": ("WARNING", "Staff Deleted"),
    "milk_collection_stopped": ("WARNING", "Milk Collection Stopped"),
    "unusual_milk_volume": ("WARNING", "Unusual Milk Collection Volume"),
    "milk_rate_changed": ("WARNING", "Milk Rate Changed"),
    "large_advance_entry": ("INFO", "Large Advance Entry"),
    "bulk_data_deleted": ("CRITICAL", "Bulk Data Deletion"),
    "account_settings_changed": ("WARNING", "Account Settings Changed"),
    "application_down": ("CRITICAL", "Application Down"),
    "application_restarted": ("WARNING", "Application Restarted"),
    "database_connection_failed": ("CRITICAL", "Database Connection Failed"),
    "database_connection_restored": ("INFO", "Database Connection Restored"),
    "database_query_errors": ("WARNING", "Database Query Errors Increased"),
    "server_resource_critical": ("WARNING", "Server CPU / RAM Critical"),
    "disk_storage_critical": ("WARNING", "Disk Storage Almost Full"),
    "backup_failed": ("CRITICAL", "Database Backup Failed"),
    "backup_succeeded": ("INFO", "Database Backup Successful"),
    "database_restore": ("CRITICAL", "Database Restore Performed"),
    "database_tables_missing": ("CRITICAL", "Database Tables Missing"),
    "unexpected_data_deletion": ("CRITICAL", "Unexpected Data Deletion"),
    "tenant_isolation_violation": ("CRITICAL", "Tenant Data Isolation Violation"),
    "csrf_suspicious": ("WARNING", "Repeated CSRF / Unauthorized Attempts"),
    "superadmin_password_changed": ("CRITICAL", "Super Admin Password Changed"),
    "superadmin_settings_changed": ("WARNING", "Super Admin Settings Changed"),
    "notification_settings_changed": ("WARNING", "Notification Settings Changed"),
    "security_config_changed": ("CRITICAL", "Security Configuration Changed"),
}

def ensure_monitoring_tables():
    global _monitoring_ready
    if _monitoring_ready:
        return
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_monitoring_events (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(80) NOT NULL,
                event_title VARCHAR(190) NOT NULL,
                severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
                source VARCHAR(40) NOT NULL DEFAULT 'dairymitra',
                actor_email VARCHAR(190) NULL,
                dairy_id BIGINT NULL,
                dairy_name VARCHAR(190) NULL,
                ip_address VARCHAR(64) NULL,
                user_agent VARCHAR(500) NULL,
                details LONGTEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_monitor_created (created_at),
                INDEX idx_monitor_type_created (event_type, created_at),
                INDEX idx_monitor_severity (severity)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_monitoring_email_log (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                event_id BIGINT UNSIGNED NULL,
                recipient VARCHAR(190) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL,
                error_message TEXT NULL,
                sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_monitor_email_sent (sent_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_monitoring_settings (
                setting_key VARCHAR(100) NOT NULL PRIMARY KEY,
                setting_value TEXT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            INSERT IGNORE INTO platform_monitoring_settings
                (setting_key, setting_value)
            VALUES
                ('alert_email', %s),
                ('critical_email_enabled', '1'),
                ('warning_email_enabled', '1'),
                ('info_email_enabled', '0'),
                ('daily_summary_enabled', '1')
        """, (MONITORING_ALERT_EMAIL,))
        _monitoring_ready = True
    finally:
        cur.close()


def monitoring_setting(key, default=""):
    ensure_monitoring_tables()
    row = fetch_one(
        "SELECT setting_value FROM platform_monitoring_settings WHERE setting_key=%s",
        (key,)
    )
    return row["setting_value"] if row and row.get("setting_value") is not None else default


def _save_monitor_email(event_id, recipient, subject, status, error=None):
    try:
        ensure_monitoring_tables()
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("""
                INSERT INTO platform_monitoring_email_log
                    (event_id, recipient, subject, status, error_message)
                VALUES (%s,%s,%s,%s,%s)
            """, (event_id, recipient, subject, status, error))
        finally:
            cur.close()
    except Exception:
        logger.exception("Could not save monitoring email history")


def send_monitoring_email(subject, body, event_id=None):
    recipient = monitoring_setting("alert_email", MONITORING_ALERT_EMAIL).strip()
    if not recipient:
        logger.warning("Monitoring alert email recipient is not configured")
        return False
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL)):
        _save_monitor_email(event_id, recipient, subject, "SKIPPED",
                            "SMTP configuration is incomplete")
        logger.warning("Monitoring SMTP configuration is incomplete")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = recipient
    msg.set_content(body)
    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=15
            ) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        _save_monitor_email(event_id, recipient, subject, "SENT")
        return True
    except Exception as exc:
        logger.exception("Monitoring email delivery failed")
        _save_monitor_email(event_id, recipient, subject, "FAILED", str(exc)[:1000])
        return False


def record_monitoring_event(event_type, source="dairymitra", actor_email=None,
                            dairy_id=None, dairy_name=None, ip_address=None,
                            user_agent=None, details=None, severity=None):
    ensure_monitoring_tables()
    rule = EVENT_RULES.get(event_type, ("INFO", event_type.replace("_", " ").title()))
    severity = (severity or rule[0]).upper()
    if severity not in ("CRITICAL", "WARNING", "INFO"):
        severity = "INFO"
    details = details if isinstance(details, dict) else {}
    # Sensitive values are never persisted.
    safe_details = {
        str(k): v for k, v in details.items()
        if str(k).lower() not in {
            "password", "otp", "token", "secret", "authorization",
            "access_token", "refresh_token"
        }
    }
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO platform_monitoring_events
                (event_type,event_title,severity,source,actor_email,dairy_id,
                 dairy_name,ip_address,user_agent,details)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            event_type[:80], rule[1][:190], severity, source[:40],
            actor_email[:190] if actor_email else None, dairy_id,
            dairy_name[:190] if dairy_name else None,
            ip_address[:64] if ip_address else None,
            user_agent[:500] if user_agent else None,
            json.dumps(safe_details, ensure_ascii=False, default=str)[:12000]
        ))
        event_id = cur.lastrowid
    finally:
        cur.close()

    # Security events alert only when a 10-minute threshold is crossed.
    thresholds = {
        "wrong_password": 5, "otp_request": 5, "wrong_otp": 5,
        "password_reset_request": 5, "superadmin_failed_login": 5
    }
    threshold = thresholds.get(event_type)
    send_alert = True
    if threshold:
        if actor_email:
            count = fetch_one("""
                SELECT COUNT(*) AS n FROM platform_monitoring_events
                WHERE event_type=%s AND actor_email=%s
                  AND created_at >= NOW() - INTERVAL 10 MINUTE
            """, (event_type, actor_email))
        elif ip_address:
            count = fetch_one("""
                SELECT COUNT(*) AS n FROM platform_monitoring_events
                WHERE event_type=%s AND ip_address=%s
                  AND created_at >= NOW() - INTERVAL 10 MINUTE
            """, (event_type, ip_address))
        else:
            count = {"n": 0}
        send_alert = int((count or {}).get("n") or 0) == threshold

    email_key = {
        "CRITICAL": "critical_email_enabled",
        "WARNING": "warning_email_enabled",
        "INFO": "info_email_enabled"
    }[severity]
    enabled = monitoring_setting(email_key, "1" if severity != "INFO" else "0") == "1"
    if send_alert and enabled:
        subject = f"[DairyMitr {severity}] {rule[1]}"
        body = (
            f"DairyMitr Monitoring Alert\n\nEvent: {rule[1]}\n"
            f"Severity: {severity}\nSource: {source}\n"
            f"Time: {datetime.now().astimezone().strftime('%d %b %Y, %I:%M:%S %p %Z')}\n"
            f"Owner: {actor_email or 'Not available'}\n"
            f"Dairy: {dairy_name or 'Not available'}\n"
            f"Dairy ID: {dairy_id or 'Not available'}\n"
            f"IP: {ip_address or 'Not available'}\n"
            f"User Agent: {user_agent or 'Not available'}\n"
            f"Details: {json.dumps(safe_details, ensure_ascii=False, default=str)}\n\n"
            "Never include passwords, OTP values or authentication tokens in monitoring events."
        )
        send_monitoring_email(subject, body, event_id)
    return event_id


def monitoring_client_ip():
    return request.remote_addr or ""


def monitoring_stats_data():
    ensure_monitoring_tables()
    return fetch_one("""
        SELECT
            COUNT(*) AS total_events,
            COALESCE(SUM(severity='CRITICAL' AND created_at >= CURDATE()),0) AS critical_today,
            COALESCE(SUM(severity='WARNING' AND created_at >= CURDATE()),0) AS warnings_today,
            COALESCE(SUM(event_type IN ('wrong_password','wrong_otp','otp_request',
                'superadmin_failed_login','login_new_ip','login_new_device')
                AND created_at >= CURDATE()),0) AS login_security_today
        FROM platform_monitoring_events
        WHERE created_at >= NOW() - INTERVAL 30 DAY
    """) or {}




# =============================================================
# 3. SECURITY
# =============================================================

csrf = CSRFProtect(app)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)
limiter.init_app(app)


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    response.headers["Cache-Control"] = "no-store"

    if ENVIRONMENT == "production" and request.is_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# =============================================================
# 4. DATABASE CONFIGURATION
# =============================================================

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "dairymitra"),
    "charset": "utf8mb4",
    "connection_timeout": 10,
    "autocommit": True,
}


def get_db():
    if "db_connection" not in g:
        try:
            g.db_connection = mysql.connector.connect(**DB_CONFIG)
        except MySQLError:
            logger.exception("Database connection failed")
            abort(503, description="Database temporarily unavailable.")

    if not g.db_connection.is_connected():
        try:
            g.db_connection.reconnect(attempts=2, delay=1)
        except MySQLError:
            logger.exception("Database reconnection failed")
            abort(503, description="Database temporarily unavailable.")

    return g.db_connection


@app.teardown_appcontext
def close_db(exception=None):
    connection = g.pop("db_connection", None)
    if connection is not None:
        try:
            connection.close()
        except MySQLError:
            logger.exception("Database connection closing failed")


# =============================================================
# 5. DATABASE HELPERS
# =============================================================

def fetch_all(query, params=()):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()


def fetch_one(query, params=()):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()


# =============================================================
# 6. SUPER ADMIN AUTHENTICATION
# =============================================================

SUPERADMIN_EMAIL = os.getenv("SUPERADMIN_EMAIL", "").strip().lower()
SUPERADMIN_PASSWORD_HASH = os.getenv("SUPERADMIN_PASSWORD_HASH", "")


def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if not session.get("super_admin_logged_in"):
            return redirect(url_for("login"))

        if session.get("super_admin_email") != SUPERADMIN_EMAIL:
            session.clear()
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# Keep the decorator name used by earlier route versions.
super_admin_required = login_required


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if session.get("super_admin_logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not SUPERADMIN_EMAIL or not SUPERADMIN_PASSWORD_HASH:
            flash("Super Admin credentials are not configured.", "danger")
            return render_template("login.html")

        valid_email = email == SUPERADMIN_EMAIL
        valid_password = False

        if valid_email and password:
            try:
                valid_password = check_password_hash(
                    SUPERADMIN_PASSWORD_HASH, password
                )
            except (ValueError, TypeError):
                logger.error("Invalid Super Admin password hash configuration")

        if valid_email and valid_password:
            session.clear()
            session["super_admin_logged_in"] = True
            session["super_admin_email"] = SUPERADMIN_EMAIL
            session.permanent = True

            logger.info("Super Admin login successful")
            try:
                record_monitoring_event(
                    "superadmin_login", source="superadmin",
                    actor_email=SUPERADMIN_EMAIL, ip_address=monitoring_client_ip(),
                    user_agent=request.user_agent.string
                )
            except Exception:
                logger.exception("Could not record Super Admin login")
            flash("Welcome to DairyMitr Super Admin!", "success")
            return redirect(url_for("dashboard"))

        logger.warning("Failed Super Admin login attempt")
        try:
            record_monitoring_event(
                "superadmin_failed_login", source="superadmin",
                actor_email=email or None, ip_address=monitoring_client_ip(),
                user_agent=request.user_agent.string
            )
        except Exception:
            logger.exception("Could not record failed Super Admin login")
        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logger.info("Super Admin logged out")
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# =============================================================
# 7. DASHBOARD
# =============================================================

@app.route("/")
@login_required
def dashboard():
    stats = fetch_one("""
        SELECT
            COUNT(*) AS total_dairies,
            COALESCE(SUM(is_verified = 1), 0) AS verified_dairies,
            COALESCE(SUM(is_verified = 0), 0) AS unverified_dairies
        FROM users
    """) or {}

    vendor_stats = fetch_one("""
        SELECT COUNT(*) AS total_vendors
        FROM vendors
    """) or {"total_vendors": 0}

    staff_stats = fetch_one("""
        SELECT
            COUNT(*) AS total_staff,
            COALESCE(SUM(is_active = 1), 0) AS active_staff
        FROM staff
    """) or {"total_staff": 0, "active_staff": 0}

    # NOTE: These two collection tables may contain overlapping records
    # if a dairy migrated from the old litre-rate system to FAT/SNF.
    # Confirm the dairy's active calculation mode before treating this
    # combined figure as a unique platform-wide total.
    milk_stats = fetch_one("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0) FROM milk_collection)
            +
            (SELECT COALESCE(SUM(quantity), 0)
             FROM fat_snf_milk_collection) AS total_milk
    """) or {"total_milk": 0}

    today_stats = fetch_one("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0)
             FROM milk_collection
             WHERE date = CURDATE())
            +
            (SELECT COALESCE(SUM(quantity), 0)
             FROM fat_snf_milk_collection
             WHERE collection_date = CURDATE()) AS today_milk
    """) or {"today_milk": 0}

    recent_dairies = fetch_all("""
        SELECT id, dairy_name, email, phone, dairy_code, is_verified
        FROM users
        ORDER BY id DESC
        LIMIT 5
    """)

    return render_template(
        "dashboard.html",
        stats=stats,
        vendor_stats=vendor_stats,
        staff_stats=staff_stats,
        milk_stats=milk_stats,
        today_stats=today_stats,
        recent_dairies=recent_dairies,
    )


# =============================================================
# 8. DAIRY MANAGEMENT
# =============================================================

@app.route("/dairies")
@login_required
def dairies():
    search = request.args.get("q", "").strip()
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 20
    offset = (page - 1) * per_page

    where_clause = ""
    params = []

    if search:
        where_clause = """
            WHERE (
                u.dairy_name LIKE %s
                OR u.email LIKE %s
                OR u.phone LIKE %s
                OR u.dairy_code LIKE %s
            )
        """
        value = f"%{search}%"
        params = [value] * 4

    total_result = fetch_one(
        f"SELECT COUNT(*) AS total FROM users u {where_clause}",
        tuple(params),
    ) or {"total": 0}

    total = total_result["total"] or 0

    dairy_list = fetch_all(
        f"""
        SELECT
            u.id, u.dairy_name, u.email, u.phone, u.dairy_code,
            u.is_verified,
            (SELECT COUNT(*) FROM vendors v
             WHERE v.user_id = u.id) AS total_vendors,
            (SELECT COUNT(*) FROM staff s
             WHERE s.owner_id = u.id) AS total_staff
        FROM users u
        {where_clause}
        ORDER BY u.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, offset]),
    )

    total_pages = (total + per_page - 1) // per_page

    # These counts are global, not limited to the current page.
    verification_counts = fetch_one("""
        SELECT
            COALESCE(SUM(is_verified = 1), 0) AS verified_total,
            COALESCE(SUM(is_verified = 0), 0) AS unverified_total
        FROM users
    """) or {"verified_total": 0, "unverified_total": 0}

    return render_template(
        "dairies.html",
        dairies=dairy_list,
        search=search,
        page=page,
        total_pages=total_pages,
        total=total,
        verified_total=verification_counts["verified_total"],
        unverified_total=verification_counts["unverified_total"],
    )


# =============================================================
# 9. DAIRY DETAILS
# =============================================================

@app.route("/dairy/<int:dairy_id>")
@login_required
def dairy_details(dairy_id):
    dairy = fetch_one("""
        SELECT id, dairy_name, email, phone, dairy_code, is_verified
        FROM users
        WHERE id = %s
    """, (dairy_id,))

    if not dairy:
        abort(404)

    vendor_stats = fetch_one("""
        SELECT COUNT(*) AS total_vendors
        FROM vendors
        WHERE user_id = %s
    """, (dairy_id,)) or {"total_vendors": 0}

    staff_stats = fetch_one("""
        SELECT
            COUNT(*) AS total_staff,
            COALESCE(SUM(is_active = 1), 0) AS active_staff
        FROM staff
        WHERE owner_id = %s
    """, (dairy_id,)) or {"total_staff": 0, "active_staff": 0}

    milk_stats = fetch_one("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0)
             FROM milk_collection WHERE user_id = %s)
            +
            (SELECT COALESCE(SUM(quantity), 0)
             FROM fat_snf_milk_collection WHERE user_id = %s)
            AS total_milk
    """, (dairy_id, dairy_id)) or {"total_milk": 0}

    recent_vendors = fetch_all("""
        SELECT id, vendor_id, name, name_en, phone, milk_type
        FROM vendors
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 10
    """, (dairy_id,))

    return render_template(
        "dairy_details.html",
        dairy=dairy,
        vendor_stats=vendor_stats,
        staff_stats=staff_stats,
        milk_stats=milk_stats,
        recent_vendors=recent_vendors,
    )


# =============================================================
# 10. USER MANAGEMENT
# =============================================================

@app.route("/users")
@login_required
def users():
    search = request.args.get("q", "").strip()
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = 20
    offset = (page - 1) * per_page

    users_query = """
        SELECT
            'Owner' AS role,
            u.id AS id,
            u.dairy_name AS name,
            u.email AS email,
            u.phone AS phone,
            u.id AS dairy_id,
            u.dairy_name AS dairy_name,
            u.is_verified AS status
        FROM users u

        UNION ALL

        SELECT
            'Staff' AS role,
            s.id AS id,
            s.name AS name,
            s.email AS email,
            NULL AS phone,
            s.owner_id AS dairy_id,
            u.dairy_name AS dairy_name,
            s.is_active AS status
        FROM staff s
        LEFT JOIN users u ON u.id = s.owner_id

        UNION ALL

        SELECT
            'Customer' AS role,
            v.id AS id,
            v.name AS name,
            NULL AS email,
            v.phone AS phone,
            v.user_id AS dairy_id,
            u.dairy_name AS dairy_name,
            1 AS status
        FROM vendors v
        LEFT JOIN users u ON u.id = v.user_id
    """

    where_clause = ""
    params = []

    if search:
        where_clause = """
            WHERE (
                name LIKE %s OR email LIKE %s OR phone LIKE %s
                OR role LIKE %s OR dairy_name LIKE %s
            )
        """
        value = f"%{search}%"
        params = [value] * 5

    count_result = fetch_one(
        f"SELECT COUNT(*) AS total FROM ({users_query}) AS all_users {where_clause}",
        tuple(params),
    ) or {"total": 0}

    total = count_result["total"] or 0

    user_list = fetch_all(
        f"""
        SELECT *
        FROM ({users_query}) AS all_users
        {where_clause}
        ORDER BY name ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, offset]),
    )

    total_pages = (total + per_page - 1) // per_page

    role_counts = fetch_one(f"""
        SELECT
            SUM(role = 'Owner') AS owner_count,
            SUM(role = 'Staff') AS staff_count,
            SUM(role = 'Customer') AS customer_count
        FROM ({users_query}) AS all_users
    """) or {}

    return render_template(
        "users.html",
        users=user_list,
        search=search,
        page=page,
        total_pages=total_pages,
        total=total,
        owner_count=role_counts.get("owner_count") or 0,
        staff_count=role_counts.get("staff_count") or 0,
        customer_count=role_counts.get("customer_count") or 0,
    )


# =============================================================
# 11. USER DETAILS
# =============================================================

@app.route("/user/<string:role>/<int:user_id>")
@login_required
def user_details(role, user_id):
    if role == "Owner":
        user = fetch_one("""
            SELECT
                id, dairy_name AS name, email, phone,
                id AS dairy_id, dairy_name, dairy_code,
                is_verified AS status
            FROM users
            WHERE id = %s
        """, (user_id,))

    elif role == "Staff":
        user = fetch_one("""
            SELECT
                s.id, s.name, s.email, s.vehicle_number,
                s.role AS staff_role, s.owner_id AS dairy_id,
                s.is_active AS status, u.dairy_name
            FROM staff s
            LEFT JOIN users u ON u.id = s.owner_id
            WHERE s.id = %s
        """, (user_id,))

    elif role == "Customer":
        user = fetch_one("""
            SELECT
                v.id, v.name, v.name_en, v.phone, v.address,
                v.milk_type, v.user_id AS dairy_id,
                u.dairy_name
            FROM vendors v
            LEFT JOIN users u ON u.id = v.user_id
            WHERE v.id = %s
        """, (user_id,))

    else:
        abort(404)

    if not user:
        abort(404)

    return render_template("user_details.html", user=user, role=role)



# =============================================================
# 12. PLATFORM ANALYTICS
# =============================================================

@app.route("/analytics")
@login_required
def analytics():
    from decimal import Decimal

    dairy_counts = fetch_one("""
        SELECT
            COUNT(*) AS total_dairies,
            COALESCE(SUM(is_verified = 1), 0) AS verified_dairies,
            COALESCE(SUM(is_verified = 0), 0) AS unverified_dairies
        FROM users
    """) or {}

    vendor_stats = fetch_one("""
        SELECT COUNT(*) AS total_vendors
        FROM vendors
    """) or {"total_vendors": 0}

    staff_stats = fetch_one("""
        SELECT COUNT(*) AS total_staff
        FROM staff
    """) or {"total_staff": 0}

    # Separate monthly totals by collection system.
    # Combining both tables may double-count data if a dairy
    # has records in both systems.
    monthly_milk = fetch_all("""
        SELECT month, SUM(quantity) AS total
        FROM (
            SELECT
                DATE_FORMAT(date, '%Y-%m') AS month,
                quantity
            FROM milk_collection
            WHERE date IS NOT NULL

            UNION ALL

            SELECT
                DATE_FORMAT(collection_date, '%Y-%m') AS month,
                quantity
            FROM fat_snf_milk_collection
            WHERE collection_date IS NOT NULL
        ) AS combined_milk
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)

    milk_totals = fetch_one("""
        SELECT
            (SELECT COALESCE(SUM(quantity), 0)
             FROM milk_collection) AS legacy_total,
            (SELECT COALESCE(SUM(quantity), 0)
             FROM fat_snf_milk_collection) AS fat_snf_total
    """) or {"legacy_total": 0, "fat_snf_total": 0}

    # Convert database numeric values safely to Decimal
    legacy_total = Decimal(str(milk_totals.get("legacy_total") or 0))
    fat_snf_total = Decimal(str(milk_totals.get("fat_snf_total") or 0))

    total_milk = legacy_total + fat_snf_total

    # Safely convert counts to integers
    total_dairies = int(dairy_counts.get("total_dairies") or 0)
    verified_dairies = int(dairy_counts.get("verified_dairies") or 0)
    unverified_dairies = int(dairy_counts.get("unverified_dairies") or 0)
    total_vendors = int(vendor_stats.get("total_vendors") or 0)
    total_staff = int(staff_stats.get("total_staff") or 0)

    analytics_stats = {
        "total_dairies": total_dairies,
        "verified_dairies": verified_dairies,
        "unverified_dairies": unverified_dairies,
        "total_vendors": total_vendors,
        "total_staff": total_staff,
        "total_users": total_dairies + total_vendors + total_staff,
        "total_milk": float(total_milk),
    }

    # users table has no created_at field.
    # Do not fabricate monthly dairy-registration history.
    dairy_growth = []

    return render_template(
        "analytics.html",
        analytics_stats=analytics_stats,
        monthly_milk=monthly_milk,
        dairy_growth=dairy_growth,
    )


from decimal import Decimal


def _fmt_dt(value, with_time=False):
    """Format a datetime for display; returns None if empty."""
    if not value:
        return None
    try:
        return value.strftime("%d %b %Y, %I:%M %p" if with_time else "%d %b %Y")
    except AttributeError:
        return str(value)


def _paise_to_rupees(paise):
    return float(Decimal(str(paise or 0)) / Decimal("100"))

# =============================================================
# 13. SUBSCRIPTIONS
# =============================================================

@app.route("/subscriptions")
@login_required
def subscriptions():
    search = request.args.get("search", "").strip()

    subscription_stats = {
        "total": 0, "active": 0, "expired": 0, "paid": 0, "free": 0,
    }
    subscription_rows = []
    available = True

    try:
        where_clause = ""
        params = []
        if search:
            where_clause = "WHERE (u.dairy_name LIKE %s OR u.email LIKE %s)"
            value = f"%{search}%"
            params = [value, value]

        rows = fetch_all(
            f"""
            SELECT
                s.id,
                u.dairy_name,
                u.email,
                COALESCE(p.name, s.plan_code) AS plan_name,
                o.amount_paise,
                s.starts_at,
                s.ends_at,
                CASE
                    WHEN s.status = 'active' AND s.ends_at > NOW() THEN 'active'
                    WHEN s.status = 'active' THEN 'expired'
                    ELSE s.status
                END AS status
            FROM dp_subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN dp_plans p ON p.code = s.plan_code
            LEFT JOIN dp_payment_orders o ON o.id = s.order_id
            {where_clause}
            ORDER BY s.id DESC
            LIMIT 200
            """,
            tuple(params),
        )

        for row in rows:
            subscription_rows.append({
                "dairy_name": row["dairy_name"],
                "email": row["email"],
                "plan_name": row["plan_name"],
                "amount": (
                    _paise_to_rupees(row["amount_paise"])
                    if row["amount_paise"] is not None else None
                ),
                "start_date": _fmt_dt(row["starts_at"]),
                "expiry_date": _fmt_dt(row["ends_at"]),
                "status": row["status"],
            })

        # Global stats (not affected by search / LIMIT)
        counts = fetch_one("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(status = 'active' AND ends_at > NOW()), 0) AS active,
                COALESCE(SUM(status = 'active' AND ends_at <= NOW()), 0) AS expired,
                COUNT(DISTINCT CASE
                    WHEN status = 'active' AND ends_at > NOW() THEN user_id
                END) AS paid_dairies
            FROM dp_subscriptions
        """) or {}

        total_dairies = (fetch_one(
            "SELECT COUNT(*) AS n FROM users"
        ) or {}).get("n") or 0

        paid_dairies = int(counts.get("paid_dairies") or 0)

        subscription_stats = {
            "total": int(counts.get("total") or 0),
            "active": int(counts.get("active") or 0),
            "expired": int(counts.get("expired") or 0),
            "paid": paid_dairies,
            "free": max(int(total_dairies) - paid_dairies, 0),
        }

    except Exception:
        logger.exception("Subscriptions page load failed")
        available = False
        flash("Subscription data could not be loaded.", "danger")

    return render_template(
        "subscriptions.html",
        subscription_stats=subscription_stats,
        subscriptions=subscription_rows,
        search=search,
        available=available,
    )


@app.route("/payments")
@login_required
def payments():
    search = request.args.get("search", "").strip()

    payment_stats = {
        "total": 0, "successful": 0, "pending": 0, "failed": 0, "revenue": 0,
    }
    payment_rows = []
    available = True

    # Razorpay order status -> status values used by payments.html
    status_map = {
        "paid": "success",
        "partially_refunded": "success",
        "created": "pending",
        "attempted": "pending",
        "pending": "pending",
        "failed": "failed",
        "cancelled": "failed",
        "refunded": "refunded",
    }

    try:
        where_clause = ""
        params = []
        if search:
            where_clause = """
                WHERE (
                    u.dairy_name LIKE %s
                    OR u.email LIKE %s
                    OR o.razorpay_payment_id LIKE %s
                    OR o.razorpay_order_id LIKE %s
                    OR o.receipt LIKE %s
                )
            """
            value = f"%{search}%"
            params = [value] * 5

        rows = fetch_all(
            f"""
            SELECT
                o.id,
                u.dairy_name,
                u.email,
                o.razorpay_payment_id,
                o.razorpay_order_id,
                o.receipt,
                o.amount_paise,
                o.refunded_paise,
                o.verified_via,
                o.status,
                COALESCE(o.paid_at, o.created_at) AS payment_date
            FROM dp_payment_orders o
            LEFT JOIN users u ON u.id = o.user_id
            {where_clause}
            ORDER BY o.id DESC
            LIMIT 200
            """,
            tuple(params),
        )

        for row in rows:
            payment_rows.append({
                "dairy_name": row["dairy_name"],
                "email": row["email"],
                "transaction_id": (
                    row["razorpay_payment_id"]
                    or row["razorpay_order_id"]
                    or row["receipt"]
                ),
                "amount": _paise_to_rupees(row["amount_paise"]),
                "payment_method": "Razorpay",
                "payment_date": _fmt_dt(row["payment_date"], with_time=True),
                "status": status_map.get(row["status"], row["status"]),
            })

        # Global stats (not affected by search / LIMIT)
        stats = fetch_one("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(status IN ('paid','partially_refunded')), 0) AS successful,
                COALESCE(SUM(status IN ('created','attempted','pending')), 0) AS pending,
                COALESCE(SUM(status IN ('failed','cancelled')), 0) AS failed,
                COALESCE(SUM(CASE
                    WHEN status IN ('paid','partially_refunded')
                    THEN amount_paise - refunded_paise ELSE 0
                END), 0) AS revenue_paise
            FROM dp_payment_orders
        """) or {}

        payment_stats = {
            "total": int(stats.get("total") or 0),
            "successful": int(stats.get("successful") or 0),
            "pending": int(stats.get("pending") or 0),
            "failed": int(stats.get("failed") or 0),
            "revenue": _paise_to_rupees(stats.get("revenue_paise")),
        }

    except Exception:
        logger.exception("Payments page load failed")
        available = False
        flash("Payment data could not be loaded.", "danger")

    return render_template(
        "payments.html",
        payment_stats=payment_stats,
        payments=payment_rows,
        search=search,
        available=available,
    )


# =============================================================
# 15. NOTIFICATIONS
# =============================================================

@app.route("/notifications")
@login_required
def notifications():
    # Notification table columns/status workflow must be confirmed
    # before querying it. No unverified notification records are shown.
    notification_stats = {
        "total": 0,
        "sent": 0,
        "pending": 0,
        "failed": 0,
    }

    return render_template(
        "notifications.html",
        notification_stats=notification_stats,
        notifications=[],
        search=request.args.get("search", "").strip(),
        available=False,
    )


# =============================================================
# 16. SUPPORT
# =============================================================

@app.route("/support")
@login_required
def support():
    # No confirmed support-ticket table in the supplied schema.
    support_stats = {
        "total": 0,
        "open": 0,
        "in_progress": 0,
        "resolved": 0,
    }

    return render_template(
        "support.html",
        support_stats=support_stats,
        tickets=[],
        search=request.args.get("search", "").strip(),
        available=False,
    )


# =============================================================
# 17. ACTIVITY LOGS
# =============================================================

@app.route("/activity-logs")
@login_required
def activity_logs():
    # A dedicated audit log table is not yet integrated.
    activity_stats = {
        "total": 0,
        "logins": 0,
        "account_activities": 0,
        "other": 0,
    }

    return render_template(
        "activity_logs.html",
        activity_stats=activity_stats,
        activities=[],
        search=request.args.get("search", "").strip(),
        available=False,
    )


# =============================================================
# 18. SETTINGS
# =============================================================

@app.route("/settings")
@login_required
def settings():
    database_connected = False

    try:
        result = fetch_one("SELECT 1 AS connected")
        database_connected = bool(result and result.get("connected") == 1)
    except Exception:
        logger.exception("Settings page database health check failed")

    return render_template(
        "settings.html",
        admin_email=SUPERADMIN_EMAIL,
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        database_name=DB_CONFIG["database"],
        database_connected=database_connected,
        app_environment=ENVIRONMENT,
        environment=ENVIRONMENT,
        debug_mode=app.debug,
        secure_cookie=app.config["SESSION_COOKIE_SECURE"],
    )




# =============================================================
# MONITORING ROUTES AND MAIN-APP EVENT API
# =============================================================

@app.route("/monitoring")
@login_required
def monitoring_dashboard():
    try:
        stats = monitoring_stats_data()
        events = fetch_all("""
            SELECT id,event_type,event_title,severity,source,actor_email,
                   dairy_id,dairy_name,ip_address,details,created_at
            FROM platform_monitoring_events ORDER BY id DESC LIMIT 20
        """)
        email_stats = fetch_one("""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(status='SENT'),0) AS sent,
                   COALESCE(SUM(status='FAILED'),0) AS failed,
                   COALESCE(SUM(status='SKIPPED'),0) AS skipped
            FROM platform_monitoring_email_log
            WHERE sent_at >= NOW() - INTERVAL 30 DAY
        """) or {}
        return render_template(
            "monitoring.html", monitoring_stats=stats,
            recent_events=events, email_stats=email_stats,
            monitoring_email=monitoring_setting("alert_email", MONITORING_ALERT_EMAIL)
        )
    except Exception:
        logger.exception("Monitoring dashboard load failed")
        flash("Monitoring data could not be loaded.", "danger")
        return render_template(
            "monitoring.html", monitoring_stats={}, recent_events=[],
            email_stats={}, monitoring_email=MONITORING_ALERT_EMAIL
        )


@app.route("/monitoring/events")
@login_required
def monitoring_events():
    ensure_monitoring_tables()
    search = request.args.get("q", "").strip()
    severity = request.args.get("severity", "").upper()
    where, params = [], []
    if search:
        where.append("(event_title LIKE %s OR event_type LIKE %s OR actor_email LIKE %s OR dairy_name LIKE %s)")
        params.extend([f"%{search}%"] * 4)
    if severity in ("CRITICAL", "WARNING", "INFO"):
        where.append("severity=%s")
        params.append(severity)
    clause = "WHERE " + " AND ".join(where) if where else ""
    events = fetch_all(f"""
        SELECT id,event_type,event_title,severity,source,actor_email,
               dairy_id,dairy_name,ip_address,details,created_at
        FROM platform_monitoring_events {clause}
        ORDER BY id DESC LIMIT 200
    """, tuple(params))
    return render_template(
        "monitoring_events.html", events=events,
        search=search, selected_severity=severity
    )


@app.route("/monitoring/email-history")
@login_required
def monitoring_email_history():
    ensure_monitoring_tables()
    logs = fetch_all("""
        SELECT id,event_id,recipient,subject,status,error_message,sent_at
        FROM platform_monitoring_email_log ORDER BY id DESC LIMIT 200
    """)
    return render_template("monitoring_email_history.html", email_logs=logs)


@app.route("/monitoring/settings", methods=["GET", "POST"])
@login_required
def monitoring_settings():
    ensure_monitoring_tables()
    if request.method == "POST":
        email = request.form.get("alert_email", "").strip()
        if not email or "@" not in email:
            flash("Enter a valid monitoring email address.", "danger")
            return redirect(url_for("monitoring_settings"))
        settings_to_save = {
            "alert_email": email,
            "critical_email_enabled": "1" if request.form.get("critical_email_enabled") == "on" else "0",
            "warning_email_enabled": "1" if request.form.get("warning_email_enabled") == "on" else "0",
            "info_email_enabled": "1" if request.form.get("info_email_enabled") == "on" else "0",
            "daily_summary_enabled": "1" if request.form.get("daily_summary_enabled") == "on" else "0",
        }
        db = get_db()
        cur = db.cursor()
        try:
            for key, value in settings_to_save.items():
                cur.execute("""
                    INSERT INTO platform_monitoring_settings(setting_key,setting_value)
                    VALUES(%s,%s)
                    ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)
                """, (key, value))
        finally:
            cur.close()
        try:
            record_monitoring_event(
                "notification_settings_changed", source="superadmin",
                actor_email=session.get("super_admin_email"),
                ip_address=monitoring_client_ip(),
                details={"changed_fields": list(settings_to_save.keys())}
            )
        except Exception:
            logger.exception("Could not log monitoring settings update")
        flash("Monitoring settings saved.", "success")
        return redirect(url_for("monitoring_settings"))

    data = {
        "alert_email": monitoring_setting("alert_email", MONITORING_ALERT_EMAIL),
        "critical_email_enabled": monitoring_setting("critical_email_enabled", "1") == "1",
        "warning_email_enabled": monitoring_setting("warning_email_enabled", "1") == "1",
        "info_email_enabled": monitoring_setting("info_email_enabled", "0") == "1",
        "daily_summary_enabled": monitoring_setting("daily_summary_enabled", "1") == "1",
        "smtp_configured": bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM_EMAIL),
    }
    return render_template("monitoring_settings.html", settings=data)


@app.route("/monitoring/test-email", methods=["POST"])
@login_required
def monitoring_test_email():
    ok = send_monitoring_email(
        "[DairyMitr] Monitoring test email",
        "This is a test email from DairyMitr SuperAdmin Monitoring.\nSMTP delivery is working."
    )
    flash("Test email sent." if ok else "Test email failed. Check SMTP configuration and email history.",
          "success" if ok else "danger")
    return redirect(url_for("monitoring_settings"))


@app.route("/api/monitoring/event", methods=["POST"])
@limiter.limit("120 per minute")
def monitoring_event_ingest():
    if not MONITORING_INGEST_TOKEN:
        return {"ok": False, "error": "Monitoring ingestion is not configured."}, 503
    supplied = request.headers.get("X-Monitoring-Token", "")
    if not hmac.compare_digest(supplied, MONITORING_INGEST_TOKEN):
        return {"ok": False, "error": "Unauthorized."}, 401
    payload = request.get_json(silent=True) or {}
    event_type = str(payload.get("event_type", "")).strip().lower()
    if not event_type or len(event_type) > 80:
        return {"ok": False, "error": "Valid event_type is required."}, 400
    details = payload.get("details", {})
    if not isinstance(details, dict):
        return {"ok": False, "error": "details must be an object."}, 400
    try:
        event_id = record_monitoring_event(
            event_type=event_type,
            severity=payload.get("severity"),
            source=str(payload.get("source", "dairymitra"))[:40],
            actor_email=str(payload.get("actor_email", ""))[:190] or None,
            dairy_id=payload.get("dairy_id"),
            dairy_name=str(payload.get("dairy_name", ""))[:190] or None,
            ip_address=str(payload.get("ip_address") or monitoring_client_ip())[:64],
            user_agent=str(payload.get("user_agent", ""))[:500] or None,
            details=details
        )
        return {"ok": True, "event_id": event_id}, 201
    except Exception:
        logger.exception("Monitoring event ingestion failed")
        return {"ok": False, "error": "Event could not be recorded."}, 500


@app.route("/internal/monitoring/daily-summary", methods=["POST"])
def monitoring_daily_summary():
    if not MONITORING_INGEST_TOKEN:
        abort(503)
    if not hmac.compare_digest(
        request.headers.get("X-Monitoring-Token", ""), MONITORING_INGEST_TOKEN
    ):
        abort(401)
    ensure_monitoring_tables()
    stats = fetch_one("""
        SELECT COUNT(*) AS total_events,
               COALESCE(SUM(severity='CRITICAL'),0) AS critical_events,
               COALESCE(SUM(severity='WARNING'),0) AS warning_events,
               COALESCE(SUM(event_type='dairy_registered'),0) AS new_dairies,
               COALESCE(SUM(event_type IN ('superadmin_login','dairy_first_login')),0) AS login_events
        FROM platform_monitoring_events WHERE created_at >= CURDATE()
    """) or {}
    if monitoring_setting("daily_summary_enabled", "1") == "1":
        body = (
            f"DairyMitr Daily Summary - {datetime.now().astimezone().strftime('%d %b %Y')}\n\n"
            f"Events: {stats.get('total_events') or 0}\n"
            f"Critical: {stats.get('critical_events') or 0}\n"
            f"Warnings: {stats.get('warning_events') or 0}\n"
            f"New Dairies: {stats.get('new_dairies') or 0}\n"
            f"Login Events: {stats.get('login_events') or 0}\n"
        )
        send_monitoring_email("[DairyMitr] Daily Platform Summary", body)
    return {"ok": True, "summary": stats}, 200



# =============================================================
# 19. OPTIONAL HEALTH CHECK
# =============================================================

@app.route("/health")
def health():
    try:
        result = fetch_one("SELECT 1 AS ok")
        if result and result.get("ok") == 1:
            return {"status": "ok", "database": "connected"}, 200
    except Exception:
        logger.exception("Health check failed")

    return {"status": "unavailable", "database": "disconnected"}, 503


# =============================================================
# 20. ERROR HANDLERS
# =============================================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(429)
def too_many_requests(error):
    return "Too many requests. Please try again later.", 429


@app.errorhandler(503)
def service_unavailable(error):
    return (
        "DairyMitr Super Admin is temporarily unavailable. "
        "Please try again later."
    ), 503


@app.errorhandler(500)
def internal_server_error(error):
    logger.error("Internal server error: %s", error, exc_info=True)
    return "An unexpected error occurred.", 500


# =============================================================
# 21. APPLICATION START
# =============================================================

if __name__ == "__main__":
    # Auto-reload is ON by default in development.
    # Set FLASK_DEBUG=0 in .env to turn it off.
    debug_mode = (
        ENVIRONMENT == "development"
        and os.getenv("FLASK_DEBUG", "1") == "1"
    )

    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=debug_mode,
        use_reloader=debug_mode,
    )
