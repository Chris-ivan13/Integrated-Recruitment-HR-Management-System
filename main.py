import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from database import setup_database, query, execute, run_transaction, hash_password, verify_password

APP_TITLE = "Integrated Recruitment and HR Management System"

def rows_to_text(rows, columns):
    # Turn database rows into readable lines for the Tkinter text boxes.
    if not rows:
        return "No records found."

    lines = []
    for row in rows:
        values = []
        for column in columns:
            value = str(row.get(column, ""))
            value = value.replace("\\n", "\n")
            values.append(value)
        lines.append(" | ".join(values))
    return "\n".join(lines)


def score_candidate(job, qualification, experience, skills):
    # Give up to 25 marks each for qualification, experience and skills.
    required_qualification = (job["qualification"] or "").strip().lower()
    qualification_score = 25 if qualification.strip().lower() == required_qualification else 0

    required_experience = float(job["experience"] or 0)
    candidate_experience = float(experience)
    if required_experience <= 0 or candidate_experience >= required_experience:
        experience_score = 25
    else:
        experience_score = round(candidate_experience / required_experience * 25)

    required_skills = [item.strip().lower() for item in (job["skills"] or "").split(",") if item.strip()]
    candidate_skills = [item.strip().lower() for item in skills.split(",") if item.strip()]
    if required_skills:
        matched = sum(1 for item in required_skills if item in candidate_skills)
        skills_score = round(matched / len(required_skills) * 25)
    else:
        skills_score = 25

    # The total is out of 75; applicants do not see this score.
    return qualification_score, experience_score, skills_score


def next_employee_id():
    # Find the next EMP number without relying on the number of current employees.
    rows = query("SELECT emp_id FROM employees WHERE emp_id LIKE 'EMP%'")
    largest_number = 0
    for row in rows:
        number = row["emp_id"][3:]
        if number.isdigit():
            largest_number = max(largest_number, int(number))
    return "EMP" + str(largest_number + 1).zfill(3)


def month_working_days():
    # Count weekdays from the first day of this month until today.
    today = date.today()
    total = 0
    for day_number in range(1, today.day + 1):
        if date(today.year, today.month, day_number).weekday() < 5:
            total += 1
    return total


def attendance_percentage(rows):
    # Count unique Present, WFH and Late dates against weekdays elapsed this month.
    present_dates = set()
    for row in rows:
        status = str(row["status"]).upper()
        if status in ["PRESENT", "WFH", "LATE"]:
            present_dates.add(str(row["attendance_date"]))
    working_days = month_working_days()
    present = len(present_dates)
    if working_days == 0:
        return present, 0
    return present, round(min(100, present / working_days * 100), 2)

class HRApp:
    # Set the main window and show the login screen.
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x680")
        self.root.minsize(900, 600)
        self.user = None
        self.show_login()

    # Remove the old screen before opening another one.
    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # Display a heading in a window or tab.
    def heading(self, parent, title):
        ttk.Label(parent, text=title, font=("Arial", 18, "bold")).pack(pady=12)

    # Build the login screen for HR and employees.
    def show_login(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=35)
        frame.pack(expand=True)
        self.heading(frame, APP_TITLE)
        ttk.Label(frame, text="Simple desktop HR application").pack(pady=5)
        ttk.Label(frame, text="Username").pack(anchor="w", pady=(18, 2))
        self.username = ttk.Entry(frame, width=35)
        self.username.pack()
        ttk.Label(frame, text="Password").pack(anchor="w", pady=(12, 2))
        self.password = ttk.Entry(frame, width=35, show="*")
        self.password.pack()
        ttk.Button(frame, text="Login", command=self.login).pack(pady=18, fill="x")
        ttk.Label(frame, text="Demo HR login: hr / hr123").pack()
        ttk.Button(frame, text="View Jobs / Apply (No Login Needed)",
                   command=self.open_jobseeker_portal).pack(pady=14, fill="x")

    # Open the public job portal without requiring an account.
    def open_jobseeker_portal(self):
        self.user = {"username": "Guest Applicant", "role": "JOBSEEKER", "linked_id": None}
        self.clear()
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Back to Login", command=self.show_login).pack(side="right")
        ttk.Label(self.root, text="Job seeker portal — no account required").pack(anchor="w", padx=14)
        self.jobseeker_dashboard()

    # Check the login details and require new employees to change temporary passwords.
    def login(self):
        username = self.username.get().strip().lower()
        password = self.password.get().strip()
        users = query("SELECT * FROM users WHERE username=%s", (username,))
        if not users or not verify_password(password, users[0]["password"]):
            messagebox.showerror("Login failed", "Incorrect username or password.")
            return
        self.user = users[0]
        if self.user["role"] == "EMPLOYEE" and self.user.get("must_change_password", 0):
            self.force_password_change()
            return
        self.show_dashboard()

    # Let a new employee create a private password at first login.
    def force_password_change(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=35)
        frame.pack(expand=True)
        self.heading(frame, "Create Your Personal Password")
        ttk.Label(frame, text="You must set a personal password before entering your account.").pack(pady=8)
        entries = self.form(frame, [("new", "New password"), ("confirm", "Confirm password")])
        entries["new"].configure(show="*")
        entries["confirm"].configure(show="*")
        def save():
            v = self.values(entries)
            if len(v["new"]) < 8:
                messagebox.showerror("Invalid password", "Use at least 8 characters.")
                return
            if v["new"] != v["confirm"]:
                messagebox.showerror("Mismatch", "The passwords do not match.")
                return
            execute("UPDATE users SET password=%s, must_change_password=0 WHERE username=%s",
                    (hash_password(v["new"]), self.user["username"]))
            self.user["must_change_password"] = 0
            messagebox.showinfo("Password saved", "Your personal password has been created.")
            self.show_dashboard()
        ttk.Button(frame, text="Save password", command=save).pack(pady=15)

    # Open the dashboard that matches the user's role.
    def show_dashboard(self):
        self.clear()
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Logout", command=self.show_login).pack(side="right")
        role = self.user["role"]
        ttk.Label(self.root, text=f"Logged in as: {self.user['username']} ({role})").pack(anchor="w", padx=14)
        if role == "HR":
            self.hr_dashboard()
        elif role == "EMPLOYEE":
            self.employee_dashboard(self.user["linked_id"])
        else:
            self.jobseeker_dashboard()

    # Create the tabs used by each dashboard.
    def make_tabs(self, names):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        frames = {}
        for name in names:
            frame = ttk.Frame(notebook, padding=12)
            notebook.add(frame, text=name)
            frames[name] = frame
        return frames

    # Create a text area for database results.
    def output_box(self, parent):
        box = tk.Text(parent, height=15, wrap="word")
        box.pack(fill="both", expand=True, pady=8)
        return box

    # Run a query and display the returned rows.
    def show_rows(self, box, sql, params, cols):
        box.delete("1.0", "end")
        try:
            box.insert("end", rows_to_text(query(sql, params), cols))
        except Exception as e:
            messagebox.showerror("Database error", str(e))

    # Build a group of labelled input boxes.
    def form(self, parent, fields):
        entries = {}
        grid = ttk.Frame(parent)
        grid.pack(anchor="nw", fill="x")
        for i, (key, label) in enumerate(fields):
            ttk.Label(grid, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = ttk.Entry(grid, width=35)
            entry.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            entries[key] = entry
        return entries

    def one_form(self, title, fields, submit_text, on_submit):
        # Open one window for an action that needs several related values.
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        entries = {}
        optional_fields = []

        # Create one input for each value needed by this action.
        for row, field in enumerate(fields):
            key, label, kind = field[:3]
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=6)
            if kind == "choice":
                widget = ttk.Combobox(frame, width=32, state="readonly", values=field[3])
            else:
                widget = ttk.Entry(frame, width=35, show="*" if kind == "password" else "")
            widget.grid(row=row, column=1, sticky="ew", padx=6, pady=6)
            entries[key] = widget
            if kind == "optional":
                optional_fields.append(key)

        # Check the form and call the action function when the user submits it.
        def submit():
            values = {key: widget.get().strip() for key, widget in entries.items()}
            missing = [key for key in entries if key not in optional_fields and not values[key]]
            if missing:
                messagebox.showerror("Missing information", "Please complete all required fields.", parent=win)
                return
            try:
                if on_submit(values):
                    win.destroy()
            except Exception as error:
                messagebox.showerror("Error", str(error), parent=win)

        ttk.Button(frame, text=submit_text, command=submit).grid(
            row=len(fields), column=0, columnspan=2, pady=12
        )
        win.resizable(False, False)
        win.wait_window()

    # Read all values entered in a form.
    def values(self, entries):
        return {k: v.get().strip() for k, v in entries.items()}

    # Connect the HR functions to the main HR dashboard.
    def hr_dashboard(self):
        tabs = self.make_tabs(["Overview", "Recruitment", "Employees", "Departments",
                               "Attendance", "Leave", "HR Requests", "Performance & Training",
                               "Payroll", "Bonus & Promotion", "Employee Exit"])
        self.hr_overview(tabs["Overview"])
        self.hr_recruitment(tabs["Recruitment"])
        self.hr_employees(tabs["Employees"])
        self.hr_departments(tabs["Departments"])
        self.hr_attendance(tabs["Attendance"])
        self.hr_leave(tabs["Leave"])
        self.hr_requests(tabs["HR Requests"])
        self.hr_performance(tabs["Performance & Training"])
        self.hr_payroll(tabs["Payroll"])
        self.hr_bonus_promotion(tabs["Bonus & Promotion"])
        self.hr_exit(tabs["Employee Exit"])

    # Show employee totals, open jobs and pending leave requests.
    def hr_overview(self, parent):
        self.heading(parent, "HR Dashboard")
        box = self.output_box(parent)
        def refresh():
            counts = query("SELECT status, COUNT(*) AS total FROM employees GROUP BY status")
            jobs = query("SELECT COUNT(*) AS total FROM jobs WHERE status='Open'")
            pending = query("SELECT COUNT(*) AS total FROM leave_requests WHERE status='Pending'")
            box.delete("1.0", "end")
            box.insert("end", "EMPLOYEE STATUS\n")
            box.insert("end", rows_to_text(counts, ["status", "total"]) + "\n\n")
            box.insert("end", "Open jobs: " + str(jobs[0]["total"]) + "\n")
            box.insert("end", "Pending leave requests: " + str(pending[0]["total"]) + "\n")
        ttk.Button(parent, text="Refresh dashboard", command=refresh).pack()
        refresh()

    def hr_recruitment(self, parent):
        # Let HR create vacancies, review ranked applicants, update status and hire.
        self.heading(parent, "Recruitment")
        left = ttk.Frame(parent)
        left.pack(side="left", fill="y", padx=8)
        right = ttk.Frame(parent)
        right.pack(side="right", fill="both", expand=True)

        # HR enters the job details in this form.
        job_form = self.form(left, [
            ("title", "Job title"),
            ("department", "Department"),
            ("qualification", "Required qualification"),
            ("experience", "Experience years"),
            ("skills", "Required skills (comma separated)"),
            ("vacancies", "Vacancies")
        ])
        box = self.output_box(right)

        # Save a new job after checking its numeric values.
        def create_job():
            values = self.values(job_form)
            try:
                experience = float(values["experience"])
                vacancies = int(values["vacancies"])
                if experience < 0 or vacancies < 1:
                    raise ValueError("Experience cannot be negative and vacancies must be at least 1.")
                if not values["title"] or not values["qualification"] or not values["skills"]:
                    raise ValueError("Enter the job title, required qualification and required skills.")
                execute(
                    "INSERT INTO jobs (title, department, qualification, experience, skills, vacancies) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (values["title"], values["department"], values["qualification"],
                     experience, values["skills"], vacancies)
                )
                messagebox.showinfo("Saved", "Job opening created.")
                refresh_jobs()
            except Exception as error:
                messagebox.showerror("Error", str(error))

        ttk.Button(left, text="Create job", command=create_job).pack(pady=5, fill="x")

        # Display jobs created by HR.
        def refresh_jobs():
            self.show_rows(
                box,
                "SELECT job_id, title, department, qualification, experience, skills, vacancies, status "
                "FROM jobs ORDER BY job_id DESC",
                (),
                ["job_id", "title", "department", "qualification", "experience", "skills", "vacancies", "status"]
            )

        ttk.Button(right, text="Refresh jobs", command=refresh_jobs).pack()

        # Show candidate scores only to HR and rank candidates separately for each job.
        def refresh_applicants():
            rows = query(
                "SELECT applicant_id, job_id, name, phone, qualification, experience, skills, total_score, status "
                "FROM applicants WHERE UPPER(COALESCE(status, '')) <> 'HIRED' "
                "ORDER BY job_id, total_score DESC, applicant_id"
            )
            box.delete("1.0", "end")
            if not rows:
                box.insert("end", "No applications received yet.")
                return

            box.insert("end", "CANDIDATE RANKING – SCORE OUT OF 75\n")
            current_job = None
            rank = 0
            for row in rows:
                if row["job_id"] != current_job:
                    current_job = row["job_id"]
                    rank = 1
                    box.insert("end", f"\nJOB ID: {current_job}\n")
                else:
                    rank += 1
                box.insert(
                    "end",
                    f"Rank {rank} | Applicant ID: {row['applicant_id']} | {row['name']} | "
                    f"Qualification: {row['qualification']} | Experience: {row['experience']} years | "
                    f"Skills: {row['skills']} | Score: {round(float(row['total_score'] or 0))}/75 | "
                    f"Status: {row['status']}\n"
                )

        ttk.Button(right, text="View Applications / Candidate Ranking", command=refresh_applicants).pack(pady=4)

        # HR can move an applicant through the recruitment stages.
        def update_status():
            def save(values):
                applicant_id = int(values["applicant_id"])
                status = values["status"]
                existing = query("SELECT status FROM applicants WHERE applicant_id=%s", (applicant_id,))
                if not existing:
                    raise ValueError("Applicant ID was not found.")
                if existing[0]["status"] == "Hired":
                    raise ValueError("This applicant has already been hired. Their status cannot be changed.")
                execute("UPDATE applicants SET status=%s WHERE applicant_id=%s", (status, applicant_id))
                refresh_applicants()
                return True

            self.one_form(
                "Update applicant status",
                [("applicant_id", "Applicant ID", "text"),
                 ("status", "New status", "choice", ["Applied", "Shortlisted", "Interviewed", "Selected", "Rejected"])],
                "Update Status", save
            )

        ttk.Button(right, text="Update applicant status", command=update_status).pack(pady=4)

        # Hire only a candidate marked Selected, then create an employee login.
        def hire():
            def save(values):
                applicant_id = int(values["applicant_id"])
                applicant = query(
                    "SELECT * FROM applicants WHERE applicant_id=%s AND status='Selected'",
                    (applicant_id,)
                )
                if not applicant:
                    raise ValueError("Applicant must be marked Selected before hiring.")
                applicant = applicant[0]
                employee_id = next_employee_id()
                salary = float(values["salary"])
                if salary < 0:
                    raise ValueError("Salary cannot be negative.")
                temporary_password = hash_password("Welcome123")

                steps = [
                    ("INSERT INTO employees "
                     "(emp_id, name, phone, qualification, experience, skills, department, designation, salary) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (employee_id, applicant["name"], applicant["phone"], applicant["qualification"],
                      applicant["experience"], applicant["skills"], values["department"],
                      values["designation"], salary)),
                    ("INSERT INTO users "
                     "(username, password, role, linked_id, must_change_password) VALUES (%s,%s,%s,%s,%s)",
                     (employee_id.lower(), temporary_password, "EMPLOYEE", employee_id, 1)),
                    ("UPDATE applicants SET status='Hired' WHERE applicant_id=%s", (applicant_id,))
                ]
                run_transaction(steps)
                messagebox.showinfo(
                    "Hired",
                    f"Employee created: {employee_id}\nUsername: {employee_id.lower()}\n"
                    "Temporary password: Welcome123\nThe employee must change it at first login."
                )
                refresh_applicants()
                refresh_jobs()
                return True

            self.one_form(
                "Hire selected applicant",
                [("applicant_id", "Selected Applicant ID", "text"),
                 ("department", "Department", "text"),
                 ("designation", "Designation", "text"),
                 ("salary", "Basic salary", "text")],
                "Confirm Hire", save
            )

        ttk.Button(right, text="Hire selected applicant", command=hire).pack(pady=4)
        refresh_jobs()

    def hr_employees(self, parent):
        # Let HR view, add and search employee records using Employee ID.
        self.heading(parent, "Employee Records")
        box = self.output_box(parent)

        # Show all current employee records.
        def refresh():
            self.show_rows(
                box,
                "SELECT emp_id, name, phone, department, designation, salary, status FROM employees ORDER BY emp_id",
                (),
                ["emp_id", "name", "phone", "department", "designation", "salary", "status"]
            )

        ttk.Button(parent, text="View / Refresh employees", command=refresh).pack()

        # Add an employee and create the matching login account together.
        def add():
            def save(values):
                employee_id = values["empid"].upper()
                experience = float(values["experience"])
                salary = float(values["salary"])
                if experience < 0 or salary < 0:
                    raise ValueError("Experience and salary cannot be negative.")
                if query("SELECT emp_id FROM employees WHERE emp_id=%s", (employee_id,)):
                    raise ValueError("That Employee ID already exists.")

                steps = [
                    ("INSERT INTO employees "
                     "(emp_id, name, phone, qualification, experience, skills, department, designation, salary) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (employee_id, values["name"], values["phone"], values["qualification"],
                      experience, values["skills"], values["department"], values["designation"], salary)),
                    ("INSERT INTO users "
                     "(username, password, role, linked_id, must_change_password) VALUES (%s,%s,%s,%s,%s)",
                     (employee_id.lower(), hash_password("Welcome123"), "EMPLOYEE", employee_id, 1))
                ]
                run_transaction(steps)
                messagebox.showinfo(
                    "Employee created",
                    f"Username: {employee_id.lower()}\nTemporary password: Welcome123\n"
                    "The employee must create a personal password at first login."
                )
                refresh()
                return True

            self.one_form(
                "Add employee",
                [("empid", "Employee ID", "text"), ("name", "Name", "text"),
                 ("phone", "Phone", "text"), ("qualification", "Qualification", "text"),
                 ("experience", "Experience years", "text"), ("skills", "Skills", "text"),
                 ("department", "Department", "text"), ("designation", "Designation", "text"),
                 ("salary", "Basic salary", "text")],
                "Create Employee", save
            )

        ttk.Button(parent, text="Add employee", command=add).pack(pady=5)

        # Search for one employee using the Employee ID only.
        def search():
            def find(values):
                self.show_rows(
                    box,
                    "SELECT emp_id, name, phone, department, designation, salary, status "
                    "FROM employees WHERE emp_id=%s",
                    (values["empid"].upper(),),
                    ["emp_id", "name", "phone", "department", "designation", "salary", "status"]
                )
                return True

            self.one_form("Search employee by ID", [("empid", "Employee ID", "text")], "Search", find)

        ttk.Button(parent, text="Search employee", command=search).pack(pady=4)
        refresh()

    # Let HR add and view department names.
    # Let HR add new departments and view the department list.
    def hr_departments(self,parent):
        self.heading(parent,"Departments")
        box=self.output_box(parent)
        def refresh():
            self.show_rows(box,"SELECT * FROM departments",(),["department_id","department_name"])
        def add():
            def submit(v):
                execute("INSERT INTO departments(department_name) VALUES(%s)",(v["name"],))
                refresh()
                return True
            self.one_form("Add department", [("name","Department name","text")], "Save Department", submit)
        ttk.Button(parent,text="Add department",command=add).pack()
        ttk.Button(parent,text="Refresh departments",command=refresh).pack(pady=4)
        refresh()

    def hr_attendance(self, parent):
        # Let HR search attendance by Employee ID and review correction requests.
        self.heading(parent, "Attendance")
        search_row = ttk.Frame(parent)
        search_row.pack(fill="x", pady=5)
        ttk.Label(search_row, text="Employee ID:").pack(side="left", padx=5)
        employee_entry = ttk.Entry(search_row, width=22)
        employee_entry.pack(side="left", padx=5)
        box = self.output_box(parent)
        box.configure(height=9)

        # Show the employee's attendance percentage for the current month.
        def view_attendance():
            employee_id = employee_entry.get().strip().upper()
            if not employee_id:
                messagebox.showwarning("Employee ID required", "Enter an Employee ID.")
                return
            employee = query("SELECT emp_id, name FROM employees WHERE emp_id=%s", (employee_id,))
            if not employee:
                messagebox.showerror("Not found", "Employee ID was not found.")
                return

            records = query(
                "SELECT attendance_date, status, marked_at FROM attendance "
                "WHERE emp_id=%s AND YEAR(attendance_date)=YEAR(CURDATE()) "
                "AND MONTH(attendance_date)=MONTH(CURDATE()) ORDER BY attendance_date DESC",
                (employee_id,)
            )
            present_days, percentage = attendance_percentage(records)
            box.delete("1.0", "end")
            box.insert("end", f"Employee: {employee[0]['name']} ({employee_id})\n")
            box.insert("end", f"Present days this month: {present_days}/{month_working_days()}\n")
            box.insert("end", f"Attendance percentage: {percentage}%\n\n")
            box.insert("end", "DAILY RECORDS\n")
            box.insert("end", rows_to_text(records, ["attendance_date", "status", "marked_at"]))

        ttk.Button(search_row, text="Search / View Attendance", command=view_attendance).pack(side="left", padx=5)

        # Allow HR to add or correct a daily attendance record manually.
        def add_record():
            def save(values):
                employee_id = values["emp"].upper()
                if not query("SELECT emp_id FROM employees WHERE emp_id=%s", (employee_id,)):
                    raise ValueError("Employee ID was not found.")
                record_date = date.fromisoformat(values["day"])
                if record_date > date.today():
                    raise ValueError("Attendance date cannot be in the future.")
                existing = query(
                    "SELECT attendance_id FROM attendance WHERE emp_id=%s AND attendance_date=%s",
                    (employee_id, values["day"])
                )
                if existing:
                    execute("UPDATE attendance SET status=%s, marked_at=NOW() WHERE attendance_id=%s",
                            (values["status"], existing[0]["attendance_id"]))
                else:
                    execute("INSERT INTO attendance (emp_id, attendance_date, status) VALUES (%s,%s,%s)",
                            (employee_id, values["day"], values["status"]))
                employee_entry.delete(0, "end")
                employee_entry.insert(0, employee_id)
                view_attendance()
                return True

            self.one_form(
                "Add or correct attendance",
                [("emp", "Employee ID", "text"), ("day", "Date (YYYY-MM-DD)", "text"),
                 ("status", "Attendance status", "choice", ["Present", "Absent", "Late", "WFH"])],
                "Save Attendance", save
            )

        ttk.Button(parent, text="Add / Correct Attendance (HR)", command=add_record).pack(pady=3)

        # Display correction requests sent by employees.
        correction_box = self.output_box(parent)
        correction_box.configure(height=7)

        def refresh_corrections():
            rows = query(
                "SELECT correction_id, emp_id, attendance_date, requested_status, reason, status, hr_remark "
                "FROM attendance_corrections ORDER BY correction_id DESC"
            )
            correction_box.delete("1.0", "end")
            correction_box.insert("end", "ATTENDANCE CORRECTION REQUESTS\n")
            correction_box.insert("end", rows_to_text(
                rows, ["correction_id", "emp_id", "attendance_date", "requested_status", "reason", "status", "hr_remark"]
            ))

        # Approve or reject an employee's attendance correction request.
        def review_correction():
            def save(values):
                correction_id = int(values["correction_id"])
                rows = query(
                    "SELECT * FROM attendance_corrections WHERE correction_id=%s AND status='Pending'",
                    (correction_id,)
                )
                if not rows:
                    raise ValueError("Pending correction request was not found.")
                request = rows[0]
                decision = values["decision"]
                if decision == "Approve":
                    existing = query(
                        "SELECT attendance_id FROM attendance WHERE emp_id=%s AND attendance_date=%s",
                        (request["emp_id"], request["attendance_date"])
                    )
                    steps = []
                    if existing:
                        steps.append(("UPDATE attendance SET status=%s WHERE attendance_id=%s",
                                      (request["requested_status"], existing[0]["attendance_id"])))
                    else:
                        steps.append(("INSERT INTO attendance (emp_id, attendance_date, status) VALUES (%s,%s,%s)",
                                      (request["emp_id"], request["attendance_date"], request["requested_status"])))
                    steps.append(("UPDATE attendance_corrections SET status='Approved', hr_remark=%s WHERE correction_id=%s",
                                  (values["remark"], correction_id)))
                    run_transaction(steps)
                else:
                    execute(
                        "UPDATE attendance_corrections SET status='Rejected', hr_remark=%s WHERE correction_id=%s",
                        (values["remark"], correction_id)
                    )
                refresh_corrections()
                if employee_entry.get().strip():
                    view_attendance()
                return True

            self.one_form(
                "Review attendance correction",
                [("correction_id", "Correction ID", "text"),
                 ("decision", "Decision", "choice", ["Approve", "Reject"]),
                 ("remark", "HR remark", "optional")],
                "Save Decision", save
            )

        ttk.Button(parent, text="Refresh correction requests", command=refresh_corrections).pack(pady=2)
        ttk.Button(parent, text="Approve / Reject correction", command=review_correction).pack(pady=2)
        ttk.Label(parent, text="Monthly percentage uses weekdays (Monday to Friday) up to today's date.").pack(pady=3)
        refresh_corrections()

    def hr_leave(self, parent):
        # Let HR review leave requests and update the employee's balance after approval.
        self.heading(parent, "Leave Requests")
        box = self.output_box(parent)

        def refresh():
            self.show_rows(
                box,
                "SELECT request_id, emp_id, reason, days, status, hr_remark FROM leave_requests ORDER BY request_id DESC",
                (),
                ["request_id", "emp_id", "reason", "days", "status", "hr_remark"]
            )

        def decide():
            def save(values):
                request_id = int(values["request_id"])
                requests = query(
                    "SELECT emp_id, days FROM leave_requests WHERE request_id=%s AND status='Pending'",
                    (request_id,)
                )
                if not requests:
                    raise ValueError("Pending leave request was not found.")
                request = requests[0]
                decision = values["decision"]
                if decision == "Approve":
                    employee = query("SELECT leave_balance FROM employees WHERE emp_id=%s", (request["emp_id"],))
                    if not employee or int(employee[0]["leave_balance"]) < int(request["days"]):
                        raise ValueError("The employee does not have enough leave balance now.")
                    run_transaction([
                        ("UPDATE employees SET leave_balance=leave_balance-%s WHERE emp_id=%s",
                         (request["days"], request["emp_id"])),
                        ("UPDATE leave_requests SET status='Approved', hr_remark=%s WHERE request_id=%s",
                         (values["remark"], request_id))
                    ])
                else:
                    execute(
                        "UPDATE leave_requests SET status='Rejected', hr_remark=%s WHERE request_id=%s",
                        (values["remark"], request_id)
                    )
                refresh()
                return True

            self.one_form(
                "Review leave request",
                [("request_id", "Request ID", "text"),
                 ("decision", "Decision", "choice", ["Approve", "Reject"]),
                 ("remark", "HR remark", "optional")],
                "Save Decision", save
            )

        ttk.Button(parent, text="Refresh leave requests", command=refresh).pack()
        ttk.Button(parent, text="Approve / Reject", command=decide).pack(pady=4)
        refresh()

    # Let HR review employee requests and save decisions.
    def hr_requests(self,parent):
        self.heading(parent,"Employee HR Requests")
        box=self.output_box(parent)
        def refresh():
            self.show_rows(box,"SELECT request_id,emp_id,request_type,details,reason,status,hr_remark FROM hr_requests ORDER BY request_id DESC",(),
                ["request_id","emp_id","request_type","details","reason","status","hr_remark"])
        def decide():
            def submit(v):
                decision=v["decision"].lower()
                if decision not in ["approve","reject"]:
                    raise ValueError("Decision must be Approve or Reject.")
                execute("UPDATE hr_requests SET status=%s,hr_remark=%s WHERE request_id=%s AND status='Pending'",
                        ("Approved" if decision=="approve" else "Rejected",v["remark"],int(v["rid"])))
                refresh()
                return True
            self.one_form("Review employee request",[("rid","Request ID","text"),
                ("decision","Decision (Approve / Reject)","text"),("remark","HR remark","text")],
                "Submit Decision",submit)
        ttk.Button(parent,text="Refresh employee requests",command=refresh).pack()
        ttk.Button(parent,text="Approve / Reject",command=decide).pack(pady=4)
        refresh()

    def hr_performance(self, parent):
        # Evaluate employees, suggest training and track accepted training progress.
        self.heading(parent, "Performance and Training")
        box = self.output_box(parent)

        # Save an evaluation using the project's six weighted performance factors.
        def evaluate():
            factors = ["Task Completion", "Work Quality", "Attendance", "Teamwork",
                       "Skill Development", "Manager Feedback"]
            fields = [("emp", "Employee ID", "text")]
            for factor in factors:
                key = factor.lower().replace(" ", "_")
                fields.append((key, factor + " score (0-100)", "text"))

            def save(values):
                employee_id = values["emp"].upper()
                if not query("SELECT emp_id FROM employees WHERE emp_id=%s", (employee_id,)):
                    raise ValueError("Employee ID was not found.")
                scores = [float(values[factor.lower().replace(" ", "_")]) for factor in factors]
                if any(score < 0 or score > 100 for score in scores):
                    raise ValueError("Every score must be between 0 and 100.")

                weights = [0.30, 0.20, 0.15, 0.15, 0.10, 0.10]
                overall = round(sum(score * weight for score, weight in zip(scores, weights)), 2)
                execute(
                    "INSERT INTO evaluations "
                    "(emp_id, task_completion, work_quality, attendance, teamwork, skill_development, manager_feedback, overall) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (employee_id, *scores, overall)
                )

                # Match weak areas to a suitable course and create one pending recommendation.
                weak_areas = [factor for factor, score in zip(factors, scores) if score < 80]
                courses = {
                    "Task Completion": "Project Management",
                    "Work Quality": "Technical Skills",
                    "Attendance": "Attendance Management",
                    "Teamwork": "Communication",
                    "Skill Development": "Advanced CAD",
                    "Manager Feedback": "Communication"
                }
                if weak_areas:
                    course = courses[weak_areas[0]]
                    execute(
                        "INSERT INTO training_requests (emp_id, course, status) VALUES (%s,%s,'Pending')",
                        (employee_id, course)
                    )

                messagebox.showinfo(
                    "Evaluation saved",
                    f"Overall performance: {overall}%\nWeak areas: {', '.join(weak_areas) if weak_areas else 'None'}"
                )
                refresh()
                return True

            self.one_form("Evaluate employee", fields, "Save Evaluation", save)

        # Show all evaluations and the employee's training response.
        def refresh():
            box.delete("1.0", "end")
            evaluations = query(
                "SELECT emp_id, overall, evaluation_id FROM evaluations ORDER BY evaluation_id DESC"
            )
            training = query(
                "SELECT training_id, emp_id, course, status, employee_response_reason "
                "FROM training_requests ORDER BY training_id DESC"
            )
            box.insert("end", "EVALUATIONS\n")
            box.insert("end", rows_to_text(evaluations, ["emp_id", "overall", "evaluation_id"]))
            box.insert("end", "\n\nTRAINING REQUESTS\n")
            box.insert("end", rows_to_text(
                training, ["training_id", "emp_id", "course", "status", "employee_response_reason"]
            ))

        # HR can update progress only after the employee accepts the recommendation.
        def update_training():
            def save(values):
                training_id = int(values["training_id"])
                request = query("SELECT status FROM training_requests WHERE training_id=%s", (training_id,))
                if not request or request[0]["status"] != "Accepted":
                    raise ValueError("The employee must accept this training before progress can be updated.")
                execute(
                    "UPDATE training_requests SET status=%s WHERE training_id=%s",
                    (values["status"], training_id)
                )
                refresh()
                return True

            self.one_form(
                "Update training progress",
                [("training_id", "Training request ID", "text"),
                 ("status", "New status", "choice", ["In Progress", "Completed"])],
                "Update Training", save
            )

        ttk.Button(parent, text="Evaluate employee", command=evaluate).pack()
        ttk.Button(parent, text="View / Refresh evaluations and training", command=refresh).pack(pady=4)
        ttk.Button(parent, text="Update accepted training status", command=update_training).pack(pady=4)
        refresh()

    # Calculate and display monthly employee payroll.
    def hr_payroll(self,parent):
        self.heading(parent,"Payroll")
        box=self.output_box(parent)
        def generate():
            def submit(v):
                emp=v["emp"].upper(); month=v["month"]
                e=query("SELECT salary FROM employees WHERE emp_id=%s",(emp,))
                if not e: raise ValueError("Employee not found.")
                basic=float(e[0]["salary"]); allowance=float(v["allowance"]); deduction=float(v["deduction"]); bonus=float(v["bonus"])
                net=basic+allowance+bonus-deduction
                execute("INSERT INTO payroll(emp_id,month_name,basic_salary,allowances,deductions,bonus,net_salary) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (emp,month,basic,allowance,deduction,bonus,net))
                refresh(); return True
            self.one_form("Generate payroll",[("emp","Employee ID","text"),("month","Month","text"),
                ("allowance","Allowances","text"),("deduction","Deductions","text"),("bonus","Bonus","text")],
                "Generate Payslip",submit)
        def refresh():
            self.show_rows(box,"SELECT emp_id,month_name,basic_salary,allowances,deductions,bonus,net_salary FROM payroll ORDER BY payroll_id DESC",(),
                ["emp_id","month_name","basic_salary","allowances","deductions","bonus","net_salary"])
        ttk.Button(parent,text="Generate payroll",command=generate).pack()
        ttk.Button(parent,text="View payroll",command=refresh).pack(pady=4)
        refresh()


    # Recommend bonuses and promotions using employee data.
    def hr_bonus_promotion(self, parent):
        # Recommend bonuses and promotions using the latest evaluation and attendance.
        self.heading(parent, "Bonus and Promotion Recommendations")
        box = self.output_box(parent)

        def recommend():
            # Ask HR for the employee ID in one small form.
            def calculate(values):
                employee_id = values["emp"].upper()
                employee = query("SELECT * FROM employees WHERE emp_id=%s", (employee_id,))
                if not employee:
                    raise ValueError("Employee not found.")
                evaluation = query(
                    "SELECT overall FROM evaluations WHERE emp_id=%s ORDER BY evaluation_id DESC LIMIT 1",
                    (employee_id,)
                )
                if not evaluation:
                    raise ValueError("Complete a performance evaluation first.")

                performance = float(evaluation[0]["overall"])
                attendance_rows = query(
                    "SELECT attendance_date, status FROM attendance WHERE emp_id=%s "
                    "AND YEAR(attendance_date)=YEAR(CURDATE()) AND MONTH(attendance_date)=MONTH(CURDATE())",
                    (employee_id,)
                )
                present_days, attendance = attendance_percentage(attendance_rows)
                experience = float(employee[0]["experience"] or 0)

                # Apply the project's bonus recommendation rules.
                if performance >= 90 and attendance >= 95:
                    bonus = 15
                elif performance >= 80 and attendance >= 90:
                    bonus = 10
                elif performance >= 70 and attendance >= 85:
                    bonus = 5
                else:
                    bonus = 0

                # Apply the project's promotion recommendation rules.
                if performance >= 90 and attendance >= 90 and experience >= 3:
                    promotion = "Strongly Recommended"
                elif performance >= 80 and attendance >= 85 and experience >= 2:
                    promotion = "Recommended"
                else:
                    promotion = "Not Recommended"

                box.insert(
                    "end",
                    f"\nEmployee: {employee_id} - {employee[0]['name']}\n"
                    f"Performance: {performance:.2f}%\n"
                    f"Attendance: {attendance:.2f}%\n"
                    f"Experience: {experience} years\n"
                    f"Suggested bonus: {bonus}% of basic salary\n"
                    f"Promotion: {promotion}\n"
                    "These are recommendations only. HR makes the final decision.\n"
                    "----------------------------------------\n"
                )
                return True

            self.one_form(
                "Calculate employee recommendations",
                [("emp", "Employee ID", "text")],
                "Calculate", calculate
            )

        ttk.Button(parent, text="Calculate recommendations", command=recommend).pack()
        ttk.Button(parent, text="Clear / Refresh display", command=lambda: box.delete("1.0", "end")).pack(pady=4)
        ttk.Label(parent, text="Attendance is calculated for the current month to date.").pack(pady=5)

    def hr_exit(self, parent):
        # Record employee resignations and mark the employee inactive after exit is complete.
        self.heading(parent, "Employee Exit")
        box = self.output_box(parent)

        def start():
            def save(values):
                employee_id = values["emp"].upper()
                if not query("SELECT emp_id FROM employees WHERE emp_id=%s", (employee_id,)):
                    raise ValueError("Employee ID was not found.")
                open_exit = query(
                    "SELECT exit_id FROM exits WHERE emp_id=%s AND status='EXIT PROCESS'",
                    (employee_id,)
                )
                if open_exit:
                    raise ValueError("An exit process is already open for this employee.")
                dues = float(values["dues"])
                if dues < 0:
                    raise ValueError("Final dues cannot be negative.")
                run_transaction([
                    ("INSERT INTO exits (emp_id, resignation_date, reason, last_working_day, final_dues) "
                     "VALUES (%s,%s,%s,%s,%s)",
                     (employee_id, values["date"], values["reason"], values["last"], dues)),
                    ("UPDATE employees SET status='EXIT PROCESS' WHERE emp_id=%s", (employee_id,))
                ])
                refresh()
                return True

            self.one_form(
                "Start employee exit",
                [("emp", "Employee ID", "text"), ("date", "Resignation date", "text"),
                 ("reason", "Reason", "text"), ("last", "Last working day", "text"),
                 ("dues", "Final dues", "text")],
                "Start Exit Process", save
            )

        def complete():
            def save(values):
                employee_id = values["emp"].upper()
                exits = query(
                    "SELECT exit_id FROM exits WHERE emp_id=%s AND status='EXIT PROCESS'",
                    (employee_id,)
                )
                if not exits:
                    raise ValueError("No open exit process was found for this Employee ID.")
                run_transaction([
                    ("UPDATE exits SET status='INACTIVE' WHERE emp_id=%s AND status='EXIT PROCESS'", (employee_id,)),
                    ("UPDATE employees SET status='INACTIVE' WHERE emp_id=%s", (employee_id,))
                ])
                refresh()
                return True

            self.one_form("Complete employee exit", [("emp", "Employee ID", "text")], "Complete Exit", save)

        # Refresh the exit records displayed to HR.
        def refresh():
            self.show_rows(
                box,
                "SELECT emp_id, resignation_date, last_working_day, final_dues, status FROM exits ORDER BY exit_id DESC",
                (),
                ["emp_id", "resignation_date", "last_working_day", "final_dues", "status"]
            )

        ttk.Button(parent, text="Start exit process", command=start).pack()
        ttk.Button(parent, text="Complete exit", command=complete).pack(pady=4)
        ttk.Button(parent, text="View exits", command=refresh).pack()
        refresh()

    def employee_dashboard(self, emp_id):
        # Show the employee's profile and personal HR services after login.
        tabs = self.make_tabs(["My Profile", "Attendance", "Leave", "HR Requests", "Performance & Training", "Payroll"])

        # Display the employee's own profile details.
        profile = tabs["My Profile"]
        self.heading(profile, "My Profile")
        profile_box = self.output_box(profile)
        self.show_rows(
            profile_box,
            "SELECT emp_id, name, phone, qualification, experience, skills, department, designation, salary, status "
            "FROM employees WHERE emp_id=%s",
            (emp_id,),
            ["emp_id", "name", "phone", "qualification", "experience", "skills", "department", "designation", "salary", "status"]
        )

        # Let the employee punch attendance once per day and request a correction if needed.
        attendance_tab = tabs["Attendance"]
        self.heading(attendance_tab, "My Attendance")
        attendance_box = self.output_box(attendance_tab)
        attendance_box.configure(height=9)
        correction_box = self.output_box(attendance_tab)
        correction_box.configure(height=5)

        def refresh_attendance():
            records = query(
                "SELECT attendance_date, status, marked_at FROM attendance "
                "WHERE emp_id=%s ORDER BY attendance_date DESC",
                (emp_id,)
            )
            this_month = query(
                "SELECT attendance_date, status FROM attendance WHERE emp_id=%s "
                "AND YEAR(attendance_date)=YEAR(CURDATE()) AND MONTH(attendance_date)=MONTH(CURDATE())",
                (emp_id,)
            )
            present_days, percentage = attendance_percentage(this_month)
            attendance_box.delete("1.0", "end")
            attendance_box.insert("end", f"This month's attendance: {present_days}/{month_working_days()} working days\n")
            attendance_box.insert("end", f"Attendance percentage: {percentage}%\n\nDAILY RECORDS\n")
            attendance_box.insert("end", rows_to_text(records, ["attendance_date", "status", "marked_at"]))

            corrections = query(
                "SELECT correction_id, attendance_date, requested_status, status, reason "
                "FROM attendance_corrections WHERE emp_id=%s ORDER BY correction_id DESC",
                (emp_id,)
            )
            correction_box.delete("1.0", "end")
            correction_box.insert("end", "MY ATTENDANCE CORRECTION REQUESTS\n")
            correction_box.insert("end", rows_to_text(
                corrections, ["correction_id", "attendance_date", "requested_status", "status", "reason"]
            ))

        def punch_attendance():
            already_marked = query(
                "SELECT attendance_id FROM attendance WHERE emp_id=%s AND attendance_date=CURDATE()",
                (emp_id,)
            )
            if already_marked:
                messagebox.showwarning("Already marked", "You have already punched attendance today.")
                return
            execute(
                "INSERT INTO attendance (emp_id, attendance_date, status) VALUES (%s, CURDATE(), %s)",
                (emp_id, "Present")
            )
            messagebox.showinfo("Attendance marked", "Your attendance has been marked for today.")
            refresh_attendance()

        def request_correction():
            def save(values):
                correction_date = date.fromisoformat(values["day"])
                if correction_date > date.today():
                    raise ValueError("You cannot request a correction for a future date.")
                pending = query(
                    "SELECT correction_id FROM attendance_corrections "
                    "WHERE emp_id=%s AND attendance_date=%s AND status='Pending'",
                    (emp_id, values["day"])
                )
                if pending:
                    raise ValueError("A correction request for this date is already pending.")
                execute(
                    "INSERT INTO attendance_corrections "
                    "(emp_id, attendance_date, requested_status, reason) VALUES (%s,%s,%s,%s)",
                    (emp_id, values["day"], values["status"], values["reason"])
                )
                refresh_attendance()
                return True

            self.one_form(
                "Request attendance correction",
                [("day", "Date (YYYY-MM-DD)", "text"),
                 ("status", "Correct status", "choice", ["Present", "Absent", "WFH"]),
                 ("reason", "Reason", "text")],
                "Send Request", save
            )

        ttk.Button(attendance_tab, text="Punch Attendance (Today)", command=punch_attendance).pack(pady=3)
        ttk.Button(attendance_tab, text="Request Attendance Correction", command=request_correction).pack(pady=3)
        ttk.Button(attendance_tab, text="Refresh Attendance", command=refresh_attendance).pack(pady=3)
        ttk.Label(attendance_tab, text="Attendance percentage is based on weekdays (Monday to Friday) in the current month.").pack(pady=3)
        refresh_attendance()

        # Show the employee's leave balance and previous leave requests.
        leave_tab = tabs["Leave"]
        self.heading(leave_tab, "Leave")
        leave_box = self.output_box(leave_tab)

        def refresh_leave():
            employee = query("SELECT leave_balance FROM employees WHERE emp_id=%s", (emp_id,))
            requests = query(
                "SELECT request_id, reason, days, status, hr_remark FROM leave_requests WHERE emp_id=%s ORDER BY request_id DESC",
                (emp_id,)
            )
            leave_box.delete("1.0", "end")
            balance = employee[0]["leave_balance"] if employee else 0
            leave_box.insert("end", f"Leave balance: {balance} days\n\nLEAVE REQUESTS\n")
            leave_box.insert("end", rows_to_text(requests, ["request_id", "reason", "days", "status", "hr_remark"]))

        # Submit a leave request only when enough leave days are available.
        def apply_leave():
            def save(values):
                days = int(values["days"])
                employee = query("SELECT leave_balance FROM employees WHERE emp_id=%s", (emp_id,))
                if days <= 0 or not employee or days > employee[0]["leave_balance"]:
                    raise ValueError("Invalid number of days or insufficient leave balance.")
                execute(
                    "INSERT INTO leave_requests (emp_id, reason, days) VALUES (%s,%s,%s)",
                    (emp_id, values["reason"], days)
                )
                refresh_leave()
                return True

            self.one_form(
                "Apply for leave",
                [("days", "Number of days", "text"), ("reason", "Reason", "text")],
                "Submit Leave Request", save
            )

        ttk.Button(leave_tab, text="Apply for leave", command=apply_leave).pack()
        ttk.Button(leave_tab, text="Refresh", command=refresh_leave).pack(pady=4)
        refresh_leave()

        # Display and submit employee requests such as transfer or work from home.
        request_tab = tabs["HR Requests"]
        self.heading(request_tab, "My HR Requests")
        request_box = self.output_box(request_tab)

        def refresh_requests():
            self.show_rows(
                request_box,
                "SELECT request_id, request_type, details, reason, status, hr_remark "
                "FROM hr_requests WHERE emp_id=%s ORDER BY request_id DESC",
                (emp_id,),
                ["request_id", "request_type", "details", "reason", "status", "hr_remark"]
            )

        def submit_request():
            def save(values):
                execute(
                    "INSERT INTO hr_requests (emp_id, request_type, details, reason) VALUES (%s,%s,%s,%s)",
                    (emp_id, values["type"], values["details"], values["reason"])
                )
                refresh_requests()
                return True

            self.one_form(
                "Submit HR request",
                [("type", "Request type", "choice", ["WFH", "Transfer", "Salary Revision", "Other"]),
                 ("details", "Details", "text"), ("reason", "Reason", "text")],
                "Submit Request", save
            )

        ttk.Button(request_tab, text="Submit request", command=submit_request).pack()
        ttk.Button(request_tab, text="Refresh", command=refresh_requests).pack(pady=4)
        refresh_requests()

        # Display performance results and let employees accept or reject training suggestions.
        performance_tab = tabs["Performance & Training"]
        self.heading(performance_tab, "My Performance & Training")
        performance_box = self.output_box(performance_tab)

        def refresh_performance():
            evaluations = query(
                "SELECT overall, evaluation_id FROM evaluations WHERE emp_id=%s ORDER BY evaluation_id DESC",
                (emp_id,)
            )
            training = query(
                "SELECT training_id, course, status, employee_response_reason "
                "FROM training_requests WHERE emp_id=%s ORDER BY training_id DESC",
                (emp_id,)
            )
            performance_box.delete("1.0", "end")
            performance_box.insert("end", "PERFORMANCE EVALUATIONS\n")
            performance_box.insert("end", rows_to_text(evaluations, ["overall", "evaluation_id"]))
            performance_box.insert("end", "\n\nTRAINING RECOMMENDATIONS\n")
            performance_box.insert("end", rows_to_text(
                training, ["training_id", "course", "status", "employee_response_reason"]
            ))

        # Save the employee's decision for a pending training recommendation.
        def respond_to_training():
            def save(values):
                training_id = int(values["training_id"])
                request = query(
                    "SELECT status FROM training_requests WHERE training_id=%s AND emp_id=%s",
                    (training_id, emp_id)
                )
                if not request or request[0]["status"] != "Pending":
                    raise ValueError("Pending training recommendation was not found.")

                decision = values["decision"]
                reason = values["reason"]
                if decision == "Reject" and not reason:
                    raise ValueError("Please give a reason for rejecting the training.")
                new_status = "Accepted" if decision == "Accept" else "Rejected"
                execute(
                    "UPDATE training_requests SET status=%s, employee_response_reason=%s, responded_at=NOW() "
                    "WHERE training_id=%s AND emp_id=%s",
                    (new_status, reason if decision == "Reject" else None, training_id, emp_id)
                )
                refresh_performance()
                return True

            self.one_form(
                "Respond to training recommendation",
                [("training_id", "Training request ID", "text"),
                 ("decision", "Your decision", "choice", ["Accept", "Reject"]),
                 ("reason", "Reason if rejecting (optional if accepting)", "optional")],
                "Submit Response", save
            )

        ttk.Button(performance_tab, text="Accept / Reject Training", command=respond_to_training).pack(pady=3)
        ttk.Button(performance_tab, text="Refresh", command=refresh_performance).pack(pady=3)
        refresh_performance()

        # Display payslips created by HR.
        payroll_tab = tabs["Payroll"]
        self.heading(payroll_tab, "My Payslips")
        payroll_box = self.output_box(payroll_tab)
        self.show_rows(
            payroll_box,
            "SELECT month_name, basic_salary, allowances, deductions, bonus, net_salary "
            "FROM payroll WHERE emp_id=%s ORDER BY payroll_id DESC",
            (emp_id,),
            ["month_name", "basic_salary", "allowances", "deductions", "bonus", "net_salary"]
        )

    def jobseeker_dashboard(self):
        # Let the public job seeker view open jobs and submit applications without login.
        tabs = self.make_tabs(["Open Jobs", "Apply"])

        # Show only vacancies that are still open.
        jobs_tab = tabs["Open Jobs"]
        self.heading(jobs_tab, "Available Jobs")
        jobs_box = self.output_box(jobs_tab)

        def refresh_jobs():
            self.show_rows(
                jobs_box,
                "SELECT job_id, title, department, qualification, experience, skills, vacancies "
                "FROM jobs WHERE status='Open' ORDER BY job_id",
                (),
                ["job_id", "title", "department", "qualification", "experience", "skills", "vacancies"]
            )

        ttk.Button(jobs_tab, text="Refresh jobs", command=refresh_jobs).pack()
        refresh_jobs()

        # Collect applicant details and calculate the score in the background.
        apply_tab = tabs["Apply"]
        self.heading(apply_tab, "Apply for a Job")
        fields = self.form(apply_tab, [
            ("job_id", "Job ID"), ("name", "Full name"), ("phone", "Phone"),
            ("qualification", "Qualification"), ("experience", "Experience years"),
            ("skills", "Skills (comma separated)")
        ])

        def apply():
            values = self.values(fields)
            try:
                job_id = int(values["job_id"])
                experience = float(values["experience"])
                if experience < 0:
                    raise ValueError("Experience cannot be negative.")
                if not all([values["name"], values["phone"], values["qualification"], values["skills"]]):
                    raise ValueError("Please complete every application field.")
                jobs = query("SELECT * FROM jobs WHERE job_id=%s AND status='Open'", (job_id,))
                if not jobs:
                    raise ValueError("Open Job ID was not found.")

                job = jobs[0]
                qualification_score, experience_score, skills_score = score_candidate(
                    job, values["qualification"], experience, values["skills"]
                )
                total_score = qualification_score + experience_score + skills_score
                applicant_id = execute(
                    "INSERT INTO applicants "
                    "(job_id, name, phone, qualification, experience, skills, "
                    "qualification_score, experience_score, skills_score, total_score) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (job_id, values["name"], values["phone"], values["qualification"], experience,
                     values["skills"], qualification_score, experience_score, skills_score, total_score)
                )

                # Applicants receive only a confirmation, never their internal score.
                messagebox.showinfo(
                    "Application received",
                    f"Your application has been submitted successfully. Applicant ID: {applicant_id}"
                )
                for entry in fields.values():
                    entry.delete(0, "end")
            except Exception as error:
                messagebox.showerror("Application error", str(error))

        ttk.Button(apply_tab, text="Submit application", command=apply).pack(pady=8)

def main():
    try:
        # Create missing tables and update older tables without deleting any records.
        setup_database()
    except Exception as e:
        messagebox.showerror(
            "MySQL setup error",
            "The HR database could not be prepared.\n\n"
            "1. Check that MySQL Server is running.\n"
            "2. Check the MySQL details in database.py.\n"
            "3. Install mysql-connector-python.\n\n"
            "The exact step and error are shown below:\n" + str(e)
        )
        return
    root=tk.Tk()
    HRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
