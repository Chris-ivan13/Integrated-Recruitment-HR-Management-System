import mysql.connector
import os
import hashlib
import hmac

# MySQL connection details for the local computer.
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "12345",
    "database": "integrated_hr"
}


# Open one connection to the HR database.
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# Check whether a column already exists before changing an older database.
def column_exists(cursor, table_name, column_name):
    # Check the system table so this also works with parameterized queries.
    cursor.execute(
        "SELECT COUNT(*) AS total FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DB_CONFIG["database"], table_name, column_name)
    )
    row = cursor.fetchone()
    return bool(row and row[0] > 0)


# Create all project tables and safely add columns used by newer code.
def setup_database():
    database_name = DB_CONFIG["database"]
    conn = None
    cursor = None

    try:
        # Create the database if this is the first run.
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS `" + database_name + "`")
        cursor.close()
        conn.close()

        # Connect to the project database and create the required tables.
        conn = get_connection()
        cursor = conn.cursor()
        tables = [
            ("users", """CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                linked_id VARCHAR(20),
                must_change_password TINYINT(1) DEFAULT 0
            )"""),
            ("departments", """CREATE TABLE IF NOT EXISTS departments (
                department_id INT AUTO_INCREMENT PRIMARY KEY,
                department_name VARCHAR(100) UNIQUE NOT NULL
            )"""),
            ("employees", """CREATE TABLE IF NOT EXISTS employees (
                emp_id VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(30),
                qualification VARCHAR(150),
                experience FLOAT DEFAULT 0,
                skills TEXT,
                department VARCHAR(100),
                designation VARCHAR(100),
                salary DECIMAL(12,2) DEFAULT 0,
                leave_balance INT DEFAULT 15,
                status VARCHAR(30) DEFAULT 'ACTIVE'
            )"""),
            ("jobs", """CREATE TABLE IF NOT EXISTS jobs (
                job_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                department VARCHAR(100),
                qualification VARCHAR(150),
                experience FLOAT DEFAULT 0,
                skills TEXT,
                vacancies INT DEFAULT 1,
                status VARCHAR(20) DEFAULT 'Open'
            )"""),
            ("applicants", """CREATE TABLE IF NOT EXISTS applicants (
                applicant_id INT AUTO_INCREMENT PRIMARY KEY,
                job_id INT NOT NULL,
                name VARCHAR(100),
                phone VARCHAR(30),
                qualification VARCHAR(150),
                experience FLOAT DEFAULT 0,
                skills TEXT,
                qualification_score FLOAT DEFAULT 0,
                experience_score FLOAT DEFAULT 0,
                skills_score FLOAT DEFAULT 0,
                interview_score FLOAT DEFAULT 0,
                total_score FLOAT DEFAULT 0,
                status VARCHAR(30) DEFAULT 'Applied',
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )"""),
            ("attendance", """CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                attendance_date DATE,
                status VARCHAR(20),
                marked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("attendance_corrections", """CREATE TABLE IF NOT EXISTS attendance_corrections (
                correction_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20) NOT NULL,
                attendance_date DATE NOT NULL,
                requested_status VARCHAR(20) NOT NULL,
                reason TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending',
                hr_remark TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("leave_requests", """CREATE TABLE IF NOT EXISTS leave_requests (
                request_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                reason TEXT,
                days INT,
                status VARCHAR(20) DEFAULT 'Pending',
                hr_remark TEXT,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("hr_requests", """CREATE TABLE IF NOT EXISTS hr_requests (
                request_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                request_type VARCHAR(40),
                details TEXT,
                reason TEXT,
                status VARCHAR(20) DEFAULT 'Pending',
                hr_remark TEXT,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("exits", """CREATE TABLE IF NOT EXISTS exits (
                exit_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                resignation_date VARCHAR(30),
                reason TEXT,
                last_working_day VARCHAR(30),
                final_dues DECIMAL(12,2) DEFAULT 0,
                status VARCHAR(30) DEFAULT 'EXIT PROCESS',
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("evaluations", """CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                task_completion FLOAT,
                work_quality FLOAT,
                attendance FLOAT,
                teamwork FLOAT,
                skill_development FLOAT,
                manager_feedback FLOAT,
                overall FLOAT,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("training_requests", """CREATE TABLE IF NOT EXISTS training_requests (
                training_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                course VARCHAR(100),
                status VARCHAR(30) DEFAULT 'Pending',
                employee_response_reason TEXT,
                responded_at DATETIME,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )"""),
            ("payroll", """CREATE TABLE IF NOT EXISTS payroll (
                payroll_id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(20),
                month_name VARCHAR(30),
                basic_salary DECIMAL(12,2),
                allowances DECIMAL(12,2) DEFAULT 0,
                deductions DECIMAL(12,2) DEFAULT 0,
                bonus DECIMAL(12,2) DEFAULT 0,
                net_salary DECIMAL(12,2),
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
            )""")
        ]

        # Run each table command separately so an error names the table involved.
        for table_name, sql in tables:
            try:
                cursor.execute(sql)
            except Exception as error:
                raise RuntimeError("Problem creating the " + table_name + " table: " + str(error))

        # Upgrade databases made by earlier project versions. No tables or records are deleted.
        if not column_exists(cursor, "users", "must_change_password"):
            cursor.execute("ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) DEFAULT 0")
        cursor.execute("ALTER TABLE users MODIFY password VARCHAR(255) NOT NULL")
        cursor.execute("ALTER TABLE users MODIFY must_change_password TINYINT(1) DEFAULT 0")

        if not column_exists(cursor, "attendance", "marked_at"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN marked_at DATETIME DEFAULT CURRENT_TIMESTAMP")

        if not column_exists(cursor, "training_requests", "employee_response_reason"):
            cursor.execute("ALTER TABLE training_requests ADD COLUMN employee_response_reason TEXT")
        if not column_exists(cursor, "training_requests", "responded_at"):
            cursor.execute("ALTER TABLE training_requests ADD COLUMN responded_at DATETIME")

        # Use named columns and one insert per department to avoid column-count errors.
        cursor.execute(
            "INSERT IGNORE INTO users "
            "(username, password, role, linked_id, must_change_password) "
            "VALUES (%s, %s, %s, %s, %s)",
            ("hr", "hr123", "HR", None, 0)
        )
        for department in ["Engineering", "Human Resources", "Finance", "Operations"]:
            cursor.execute(
                "INSERT IGNORE INTO departments (department_name) VALUES (%s)",
                (department,)
            )

        conn.commit()

    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Read rows from MySQL and return them as dictionaries.
def query(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


# Save one database change and return the new row ID when available.
def execute(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# Save related changes together, or undo them all if one step fails.
def run_transaction(steps):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for sql, params in steps:
            cursor.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# Store new employee passwords in a protected form instead of plain text.
def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return "pbkdf2$" + salt.hex() + "$" + digest.hex()


# Check both newer protected passwords and older plain demo passwords.
def verify_password(password, stored):
    if stored.startswith("pbkdf2$"):
        try:
            _, salt, expected = stored.split("$", 2)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200000)
            return hmac.compare_digest(actual.hex(), expected)
        except (ValueError, TypeError):
            return False
    return password == stored
