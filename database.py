import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "integrated_hr"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def setup_database():
    # Create the database first, then create the tables.
    config = DB_CONFIG.copy()
    database = config.pop("database")
    conn = mysql.connector.connect(**config)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
    cur.close()
    conn.close()

    conn = get_connection()
    cur = conn.cursor()
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(50) PRIMARY KEY,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            linked_id VARCHAR(20),
            must_change_password TINYINT(1) DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS departments (
            department_id INT AUTO_INCREMENT PRIMARY KEY,
            department_name VARCHAR(100) UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS employees (
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
        )""",
        """CREATE TABLE IF NOT EXISTS jobs (
            job_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            qualification VARCHAR(150),
            experience FLOAT DEFAULT 0,
            skills TEXT,
            vacancies INT DEFAULT 1,
            status VARCHAR(20) DEFAULT 'Open'
        )""",
        """CREATE TABLE IF NOT EXISTS applicants (
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
        )""",
        """CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            attendance_date DATE,
            status VARCHAR(20),
            marked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS leave_requests (
            request_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            reason TEXT,
            days INT,
            status VARCHAR(20) DEFAULT 'Pending',
            hr_remark TEXT,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS hr_requests (
            request_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            request_type VARCHAR(40),
            details TEXT,
            reason TEXT,
            status VARCHAR(20) DEFAULT 'Pending',
            hr_remark TEXT,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS exits (
            exit_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            resignation_date VARCHAR(30),
            reason TEXT,
            last_working_day VARCHAR(30),
            final_dues DECIMAL(12,2) DEFAULT 0,
            status VARCHAR(30) DEFAULT 'EXIT PROCESS',
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS evaluations (
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
        )""",
        """CREATE TABLE IF NOT EXISTS training_requests (
            training_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            course VARCHAR(100),
            status VARCHAR(30) DEFAULT 'Pending',
            employee_response_reason TEXT,
            responded_at DATETIME,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS attendance_corrections (
            correction_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20) NOT NULL,
            attendance_date DATE NOT NULL,
            requested_status VARCHAR(20) NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            hr_remark TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )""",
        """CREATE TABLE IF NOT EXISTS payroll (
            payroll_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(20),
            month_name VARCHAR(30),
            basic_salary DECIMAL(12,2),
            allowances DECIMAL(12,2) DEFAULT 0,
            deductions DECIMAL(12,2) DEFAULT 0,
            bonus DECIMAL(12,2) DEFAULT 0,
            net_salary DECIMAL(12,2),
            FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
        )"""
    ]
    for sql in statements:
        cur.execute(sql)

    # Upgrade an existing users table without deleting employee or HR records.
    cur.execute("SHOW COLUMNS FROM users LIKE 'must_change_password'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) DEFAULT 0")
    cur.execute("ALTER TABLE users MODIFY password VARCHAR(255) NOT NULL")

    cur.execute("SHOW COLUMNS FROM attendance LIKE 'marked_at'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE attendance ADD COLUMN marked_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    cur.execute("SHOW COLUMNS FROM training_requests LIKE 'employee_response_reason'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE training_requests ADD COLUMN employee_response_reason TEXT")
    cur.execute("SHOW COLUMNS FROM training_requests LIKE 'responded_at'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE training_requests ADD COLUMN responded_at DATETIME")

    # Simple demo logins. Change these passwords before real use.
    cur.execute("INSERT IGNORE INTO users(username,password,role,linked_id,must_change_password) VALUES (%s,%s,%s,%s,0)",
                ("hr", "hr123", "HR", None))
    cur.execute("INSERT IGNORE INTO departments (department_name) VALUES "
                "('Engineering'),('Human Resources'),('Finance'),('Operations')")
    conn.commit()
    cur.close()
    conn.close()

def query(sql, params=(), fetch=True):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    result = cur.fetchall() if fetch else None
    if not fetch:
        conn.commit()
    cur.close()
    conn.close()
    return result

def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id


def hash_password(password):
    import hashlib
    import os
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), 200000).hex()
    return "pbkdf2$" + salt + "$" + digest


def verify_password(password, stored):
    import hashlib
    if stored.startswith("pbkdf2$"):
        try:
            _, salt, expected = stored.split("$", 2)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                         bytes.fromhex(salt), 200000).hex()
            return actual == expected
        except Exception:
            return False
    # Supports the existing HR demo login and upgrades old employee passwords on first login.
    return password == stored
