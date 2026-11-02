import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import setup_database, query, execute, hash_password, verify_password

APP_TITLE = "Integrated Recruitment and HR Management System"

def rows_to_text(rows, columns):
    if not rows:
        return "No records found."
    lines = []
    for row in rows:
        lines.append(" | ".join(str(row.get(c, "")) for c in columns))
    return "\n".join(lines)

class HRApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x680")
        self.root.minsize(900, 600)
        self.user = None
        self.show_login()

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def heading(self, parent, title):
        ttk.Label(parent, text=title, font=("Arial", 18, "bold")).pack(pady=12)

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

    def open_jobseeker_portal(self):
        self.user = {"username": "Guest Applicant", "role": "JOBSEEKER", "linked_id": None}
        self.clear()
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Back to Login", command=self.show_login).pack(side="right")
        ttk.Label(self.root, text="Job seeker portal — no account required").pack(anchor="w", padx=14)
        self.jobseeker_dashboard()

    def login(self):
        username = self.username.get().strip()
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

    def make_tabs(self, names):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        frames = {}
        for name in names:
            frame = ttk.Frame(notebook, padding=12)
            notebook.add(frame, text=name)
            frames[name] = frame
        return frames

    def output_box(self, parent):
        box = tk.Text(parent, height=15, wrap="word")
        box.pack(fill="both", expand=True, pady=8)
        return box

    def show_rows(self, box, sql, params, cols):
        box.delete("1.0", "end")
        try:
            box.insert("end", rows_to_text(query(sql, params), cols))
        except Exception as e:
            messagebox.showerror("Database error", str(e))

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
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        entries = {}
        for i, (key, label, kind) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=6)
            if kind == "choice":
                widget = ttk.Combobox(frame, width=32, state="readonly",
                                      values=fields[i][3] if len(fields[i]) > 3 else [])
            else:
                widget = ttk.Entry(frame, width=35, show="*" if kind == "password" else "")
            widget.grid(row=i, column=1, sticky="ew", padx=6, pady=6)
            entries[key] = widget
        def submit():
            vals = {k: w.get().strip() for k, w in entries.items()}
            if any(not vals[k] for k, w in entries.items()):
                messagebox.showerror("Missing information", "Please complete all fields.", parent=win)
                return
            try:
                if on_submit(vals):
                    win.destroy()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)
        ttk.Button(frame, text=submit_text, command=submit).grid(
            row=len(fields), column=0, columnspan=2, pady=12)
        win.resizable(False, False)
        win.wait_window()

    def values(self, entries):
        return {k: v.get().strip() for k, v in entries.items()}

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
        self.heading(parent, "Recruitment")
        left = ttk.Frame(parent); left.pack(side="left", fill="y", padx=8)
        right = ttk.Frame(parent); right.pack(side="right", fill="both", expand=True)
        job = self.form(left, [("title","Job title"),("department","Department"),
            ("qualification","Required qualification"),("experience","Experience years"),
            ("skills","Required skills (comma separated)"),("vacancies","Vacancies")])
        def create_job():
            v = self.values(job)
            try:
                execute("INSERT INTO jobs(title,department,qualification,experience,skills,vacancies) VALUES(%s,%s,%s,%s,%s,%s)",
                    (v["title"],v["department"],v["qualification"],float(v["experience"]),v["skills"],int(v["vacancies"])))
                messagebox.showinfo("Saved","Job opening created.")
                refresh_jobs()
            except Exception as e: messagebox.showerror("Error",str(e))
        ttk.Button(left,text="Create job",command=create_job).pack(pady=5,fill="x")
        box = self.output_box(right)
        def refresh_jobs():
            self.show_rows(box,"SELECT job_id,title,department,qualification,experience,skills,vacancies,status FROM jobs",(),
                ["job_id","title","department","qualification","experience","skills","vacancies","status"])
        ttk.Button(right,text="Refresh jobs",command=refresh_jobs).pack()
        def refresh_applicants():
            self.show_rows(box,"SELECT applicant_id,job_id,name,phone,qualification,experience,skills,total_score,status FROM applicants ORDER BY total_score DESC",(),
                ["applicant_id","job_id","name","phone","qualification","experience","skills","total_score","status"])
        ttk.Button(right,text="View Applications / Refresh",command=refresh_applicants).pack(pady=4)
        def update_status():
            def submit(v):
                status=v["status"].title()
                if status not in ["Shortlisted","Selected","Rejected"]:
                    raise ValueError("Use Shortlisted, Selected or Rejected.")
                execute("UPDATE applicants SET status=%s WHERE applicant_id=%s",(status,int(v["aid"])))
                refresh_applicants()
                return True
            self.one_form("Update applicant status", [("aid","Applicant ID","text"),
                ("status","Status (Shortlisted / Selected / Rejected)","text")], "Update Status", submit)
        ttk.Button(right,text="Update applicant status",command=update_status).pack(pady=4)
        def hire():
            def submit(v):
                aid = int(v["applicant_id"])
                a = query("SELECT * FROM applicants WHERE applicant_id=%s AND status='Selected'", (aid,))
                if not a:
                    raise ValueError("Applicant must be Selected first.")
                a = a[0]
                empid = "EMP" + str(query("SELECT COUNT(*) AS n FROM employees", ())[0]["n"] + 1).zfill(3)
                execute("""INSERT INTO employees(emp_id,name,phone,qualification,experience,skills,department,designation,salary)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (empid,a["name"],a["phone"],a["qualification"],a["experience"],a["skills"],
                     v["department"],v["designation"],float(v["salary"])))
                execute("UPDATE applicants SET status='Hired' WHERE applicant_id=%s", (aid,))
                temp_hash = hash_password("Welcome123")
                execute("INSERT IGNORE INTO users(username,password,role,linked_id,must_change_password) VALUES(%s,%s,'EMPLOYEE',%s,1)",
                        (empid.lower(), temp_hash, empid))
                messagebox.showinfo("Hired", f"Employee created: {empid}\\nUsername: {empid.lower()}\\nTemporary password: Welcome123\\nEmployee must change it at first login.")
                refresh_applicants()
                return True
            self.one_form("Hire selected applicant",
                [("applicant_id","Selected Applicant ID","text"),
                 ("department","Department","text"),("designation","Designation","text"),
                 ("salary","Basic salary","text")], "Confirm Hire", submit)
        ttk.Button(right,text="Hire selected applicant",command=hire).pack(pady=4)
        refresh_jobs()

    def hr_employees(self,parent):
        self.heading(parent,"Employee Records")
        box=self.output_box(parent)
        def refresh():
            self.show_rows(box,"SELECT emp_id,name,phone,department,designation,salary,status FROM employees",(),
                ["emp_id","name","phone","department","designation","salary","status"])
        ttk.Button(parent,text="View / Refresh employees",command=refresh).pack()
        def add():
            def submit(v):
                empid=v["empid"].upper()
                execute("INSERT INTO employees(emp_id,name,department,designation,salary,phone,qualification,experience,skills) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (empid,v["name"],v["dept"],v["des"],float(v["sal"]),v["phone"],v["qualification"],float(v["experience"]),v["skills"]))
                execute("INSERT IGNORE INTO users(username,password,role,linked_id,must_change_password) VALUES(%s,%s,'EMPLOYEE',%s,1)",
                        (empid.lower(),hash_password("Welcome123"),empid))
                messagebox.showinfo("Employee created", f"Username: {empid.lower()}\\nTemporary password: Welcome123\\nEmployee must create a personal password at first login.")
                refresh()
                return True
            self.one_form("Add employee", [("empid","Employee ID","text"),("name","Name","text"),
                ("phone","Phone","text"),("qualification","Qualification","text"),
                ("experience","Experience years","text"),("skills","Skills","text"),
                ("dept","Department","text"),("des","Designation","text"),("sal","Basic salary","text")],
                "Create Employee", submit)
        ttk.Button(parent,text="Add employee",command=add).pack(pady=5)
        def search():
            def submit(v):
                self.show_rows(box,"SELECT emp_id,name,phone,department,designation,salary,status FROM employees WHERE emp_id=%s",
                    (v["empid"].upper(),),["emp_id","name","phone","department","designation","salary","status"])
                return True
            self.one_form("Search employee by ID", [("empid","Employee ID","text")], "Search", submit)
        ttk.Button(parent,text="Search employee",command=search).pack(pady=4)

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

    def hr_attendance(self,parent):
        self.heading(parent,"Attendance")
        box=self.output_box(parent)
        def add():
            def submit(v):
                execute("INSERT INTO attendance(emp_id,attendance_date,status) VALUES(%s,%s,%s)",
                        (v["emp"].upper(),v["day"],v["status"].title()))
                refresh()
                return True
            self.one_form("Add attendance record", [("emp","Employee ID","text"),("day","Date (YYYY-MM-DD)","text"),
                ("status","Status (Present / Absent / Late / WFH)","text")], "Save Attendance", submit)
        def refresh():
            self.show_rows(box,"SELECT emp_id,attendance_date,status,marked_at FROM attendance ORDER BY attendance_date DESC",(),
                ["emp_id","attendance_date","status","marked_at"])
        ttk.Button(parent,text="Add attendance record",command=add).pack()
        ttk.Button(parent,text="View attendance",command=refresh).pack(pady=4)
        ttk.Label(parent,text="Excel import can be added after the basic database version is working.").pack()
        refresh()

    def hr_leave(self,parent):
        self.heading(parent,"Leave Requests")
        box=self.output_box(parent)
        def refresh():
            self.show_rows(box,"SELECT request_id,emp_id,reason,days,status,hr_remark FROM leave_requests",(),
                ["request_id","emp_id","reason","days","status","hr_remark"])
        def decide():
            def submit(v):
                rid=int(v["rid"])
                r=query("SELECT * FROM leave_requests WHERE request_id=%s AND status='Pending'",(rid,))
                if not r: raise ValueError("Pending leave request not found.")
                decision=v["decision"].lower()
                if decision=="approve":
                    execute("UPDATE employees SET leave_balance=leave_balance-%s WHERE emp_id=%s",(r[0]["days"],r[0]["emp_id"]))
                    status="Approved"
                elif decision=="reject":
                    status="Rejected"
                else:
                    raise ValueError("Decision must be Approve or Reject.")
                execute("UPDATE leave_requests SET status=%s,hr_remark=%s WHERE request_id=%s",(status,v["remark"],rid))
                refresh()
                return True
            self.one_form("Review leave request",[("rid","Request ID","text"),
                ("decision","Decision (Approve / Reject)","text"),("remark","HR remark","text")],
                "Submit Decision",submit)
        ttk.Button(parent,text="Refresh leave requests",command=refresh).pack()
        ttk.Button(parent,text="Approve / Reject",command=decide).pack(pady=4)
        refresh()

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

    def hr_performance(self,parent):
        self.heading(parent,"Performance and Training")
        box=self.output_box(parent)
        def evaluate():
            factors=["Task Completion","Work Quality","Attendance","Teamwork","Skill Development","Manager Feedback"]
            fields=[("emp","Employee ID","text")]+[(f.lower().replace(" ","_"),f+" score (0-100)","text") for f in factors]
            def submit(v):
                vals=[float(v[f.lower().replace(" ","_")]) for f in factors]
                if any(x<0 or x>100 for x in vals): raise ValueError("Scores must be between 0 and 100.")
                overall=round(sum(x*w for x,w in zip(vals,[.30,.20,.15,.15,.10,.10])),2)
                emp=v["emp"].upper()
                execute("""INSERT INTO evaluations(emp_id,task_completion,work_quality,attendance,teamwork,skill_development,manager_feedback,overall)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",(emp,*vals,overall))
                weak=[f for f,x in zip(factors,vals) if x<80]
                mapping={"Task Completion":["Project Management"],"Work Quality":["Technical Skills","Python"],
                    "Teamwork":["Communication","Leadership"],"Skill Development":["Advanced CAD","Technical Skills"],
                    "Manager Feedback":["Communication","Leadership"]}
                courses=[]
                for f in weak:
                    for c in mapping.get(f,[]):
                        if c not in courses: courses.append(c)
                if courses:
                    execute("INSERT INTO training_requests(emp_id,course) VALUES(%s,%s)",(emp,courses[0]))
                box.insert("end",f"\\n{emp} overall performance: {overall}%\\nWeak areas: {', '.join(weak) if weak else 'None'}\\n")
                return True
            self.one_form("Evaluate employee",fields,"Save Evaluation",submit)
        def refresh():
            self.show_rows(box,"SELECT emp_id,overall,evaluation_id FROM evaluations ORDER BY evaluation_id DESC",(),
                ["emp_id","overall","evaluation_id"])
        ttk.Button(parent,text="Evaluate employee",command=evaluate).pack()
        ttk.Button(parent,text="View evaluations",command=refresh).pack(pady=4)
        def training():
            def submit(v):
                tid=int(v["rid"]); status=v["status"].title()
                if status not in ["In Progress","Completed"]:
                    raise ValueError("HR can set status to In Progress or Completed after employee acceptance.")
                rows=query("SELECT status FROM training_requests WHERE training_id=%s",(tid,))
                if not rows or rows[0]["status"]!="Accepted":
                    raise ValueError("Employee must accept the recommendation before HR updates progress.")
                execute("UPDATE training_requests SET status=%s WHERE training_id=%s",(status,tid))
                refresh_training(); return True
            self.one_form("Update accepted training progress",[("rid","Training request ID","text"),
                ("status","New status (In Progress / Completed)","text")],"Update Training",submit)
        def refresh_training():
            box.delete("1.0","end")
            box.insert("end","EVALUATIONS\\n")
            box.insert("end",rows_to_text(query("SELECT emp_id,overall,evaluation_id FROM evaluations ORDER BY evaluation_id DESC",()),
                ["emp_id","overall","evaluation_id"])+"\\n\\nTRAINING REQUESTS\\n")
            box.insert("end",rows_to_text(query("SELECT training_id,emp_id,course,status,employee_response_reason FROM training_requests ORDER BY training_id DESC",()),
                ["training_id","emp_id","course","status","employee_response_reason"])+"\\n")
        ttk.Button(parent,text="View / Refresh evaluations & training",command=refresh_training).pack(pady=4)
        ttk.Button(parent,text="Update training status",command=training).pack(pady=4)
        refresh_training()

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


    def hr_bonus_promotion(self, parent):
        self.heading(parent, "Bonus and Promotion Recommendations")
        box = self.output_box(parent)

        def recommend():
            emp = simpledialog.askstring("Employee", "Employee ID")
            if not emp:
                return
            emp = emp.upper()
            employee = query("SELECT * FROM employees WHERE emp_id=%s", (emp,))
            if not employee:
                messagebox.showerror("Error", "Employee not found.")
                return
            employee = employee[0]
            evaluation = query(
                "SELECT overall FROM evaluations WHERE emp_id=%s ORDER BY evaluation_id DESC LIMIT 1",
                (emp,)
            )
            if not evaluation:
                messagebox.showerror("Error", "Complete a performance evaluation first.")
                return
            performance = float(evaluation[0]["overall"])
            attendance_rows = query(
                "SELECT status FROM attendance WHERE emp_id=%s", (emp,)
            )
            if attendance_rows:
                working = sum(1 for r in attendance_rows
                              if r["status"].lower() in ["present", "late", "wfh"])
                attendance = working / len(attendance_rows) * 100
            else:
                attendance = 0
            experience = float(employee["experience"] or 0)

            if performance >= 90 and attendance >= 95:
                bonus = 15
            elif performance >= 80 and attendance >= 90:
                bonus = 10
            elif performance >= 70 and attendance >= 85:
                bonus = 5
            else:
                bonus = 0

            if performance >= 90 and attendance >= 90 and experience >= 3:
                promotion = "Strongly Recommended"
            elif performance >= 80 and attendance >= 85 and experience >= 2:
                promotion = "Recommended"
            else:
                promotion = "Not Recommended"

            box.insert("end",
                f"\nEmployee: {emp} - {employee['name']}\n"
                f"Performance: {performance:.2f}%\n"
                f"Attendance: {attendance:.2f}%\n"
                f"Experience: {experience} years\n"
                f"Suggested bonus: {bonus}% of basic salary\n"
                f"Promotion: {promotion}\n"
                "These are recommendations only. HR makes the final decision.\n"
                "----------------------------------------\n"
            )

        ttk.Button(parent, text="Calculate recommendations", command=recommend).pack()
        ttk.Button(parent, text="Clear / Refresh display", command=lambda: box.delete("1.0", "end")).pack(pady=4)
        ttk.Label(parent, text="Uses the latest performance evaluation and attendance records.").pack(pady=5)

    def hr_exit(self,parent):
        self.heading(parent,"Employee Exit")
        box=self.output_box(parent)
        def start():
            def submit(v):
                execute("INSERT INTO exits(emp_id,resignation_date,reason,last_working_day,final_dues) VALUES(%s,%s,%s,%s,%s)",
                        (v["emp"].upper(),v["date"],v["reason"],v["last"],float(v["dues"])))
                execute("UPDATE employees SET status='EXIT PROCESS' WHERE emp_id=%s",(v["emp"].upper(),))
                refresh()
                return True
            self.one_form("Start employee exit", [("emp","Employee ID","text"),("date","Resignation date","text"),
                ("reason","Reason","text"),("last","Last working day","text"),("dues","Final dues","text")],
                "Start Exit Process", submit)
        def complete():
            def submit(v):
                execute("UPDATE exits SET status='INACTIVE' WHERE emp_id=%s AND status='EXIT PROCESS'",(v["emp"].upper(),))
                execute("UPDATE employees SET status='INACTIVE' WHERE emp_id=%s",(v["emp"].upper(),))
                refresh()
                return True
            self.one_form("Complete employee exit", [("emp","Employee ID","text")], "Complete Exit", submit)
        def refresh():
            self.show_rows(box,"SELECT emp_id,resignation_date,last_working_day,final_dues,status FROM exits",(),
                ["emp_id","resignation_date","last_working_day","final_dues","status"])
        ttk.Button(parent,text="Start exit process",command=start).pack()
        ttk.Button(parent,text="Complete exit",command=complete).pack(pady=4)
        ttk.Button(parent,text="View exits",command=refresh).pack()
        refresh()

    def employee_dashboard(self, emp_id):
        tabs=self.make_tabs(["My Profile","Attendance","Leave","HR Requests","Performance & Training","Payroll"])
        p=tabs["My Profile"]; self.heading(p,"My Profile"); b=self.output_box(p)
        self.show_rows(b,"SELECT emp_id,name,phone,qualification,experience,skills,department,designation,salary,status FROM employees WHERE emp_id=%s",(emp_id,),
            ["emp_id","name","phone","qualification","experience","skills","department","designation","salary","status"])
        a=tabs["Attendance"]; self.heading(a,"My Attendance"); ab=self.output_box(a)
        self.show_rows(ab,"SELECT attendance_date,status FROM attendance WHERE emp_id=%s",(emp_id,),["attendance_date","status"])
        l=tabs["Leave"]; self.heading(l,"Leave")
        lb=self.output_box(l)
        def leave_refresh():
            e=query("SELECT leave_balance FROM employees WHERE emp_id=%s",(emp_id,))
            lb.delete("1.0","end"); lb.insert("end",f"Leave balance: {e[0]['leave_balance'] if e else 0} days\n")
            self.show_rows(lb,"SELECT request_id,reason,days,status,hr_remark FROM leave_requests WHERE emp_id=%s",(emp_id,),
                ["request_id","reason","days","status","hr_remark"])
        def apply_leave():
            def submit(v):
                days=int(v["days"]); e=query("SELECT leave_balance FROM employees WHERE emp_id=%s",(emp_id,))
                if not e or days<=0 or days>e[0]["leave_balance"]: raise ValueError("Invalid days or insufficient leave balance.")
                execute("INSERT INTO leave_requests(emp_id,reason,days) VALUES(%s,%s,%s)",(emp_id,v["reason"],days))
                leave_refresh(); return True
            self.one_form("Apply for leave",[("days","Number of days","text"),("reason","Reason","text")],
                "Submit Leave Request",submit)
        ttk.Button(l,text="Apply for leave",command=apply_leave).pack()
        ttk.Button(l,text="Refresh",command=leave_refresh).pack()
        leave_refresh()
        r=tabs["HR Requests"]; self.heading(r,"My HR Requests"); rb=self.output_box(r)
        def req_refresh():
            self.show_rows(rb,"SELECT request_id,request_type,details,reason,status,hr_remark FROM hr_requests WHERE emp_id=%s",(emp_id,),
                ["request_id","request_type","details","reason","status","hr_remark"])
        def submit_req():
            def submit(v):
                execute("INSERT INTO hr_requests(emp_id,request_type,details,reason) VALUES(%s,%s,%s,%s)",
                        (emp_id,v["typ"],v["details"],v["reason"]))
                req_refresh(); return True
            self.one_form("Submit HR request",[("typ","Request type (WFH / Transfer / Salary Revision / Other)","text"),
                ("details","Details","text"),("reason","Reason","text")],"Submit Request",submit)
        ttk.Button(r,text="Submit request",command=submit_req).pack()
        ttk.Button(r,text="Refresh",command=req_refresh).pack()
        req_refresh()
        perf=tabs["Performance & Training"]; self.heading(perf,"My Performance & Training"); pb=self.output_box(perf)
        self.show_rows(pb,"SELECT overall,evaluation_id FROM evaluations WHERE emp_id=%s ORDER BY evaluation_id DESC",(emp_id,),["overall","evaluation_id"])
        self.show_rows(pb,"SELECT course,status FROM training_requests WHERE emp_id=%s",(emp_id,),["course","status"])
        pay=tabs["Payroll"]; self.heading(pay,"My Payslips"); payb=self.output_box(pay)
        self.show_rows(payb,"SELECT month_name,basic_salary,allowances,deductions,bonus,net_salary FROM payroll WHERE emp_id=%s",(emp_id,),
            ["month_name","basic_salary","allowances","deductions","bonus","net_salary"])

    def jobseeker_dashboard(self):
        tabs=self.make_tabs(["Open Jobs","Apply"])
        j=tabs["Open Jobs"]; self.heading(j,"Available Jobs"); box=self.output_box(j)
        def refresh():
            self.show_rows(box,"SELECT job_id,title,department,qualification,experience,skills,vacancies FROM jobs WHERE status='Open'",(),
                ["job_id","title","department","qualification","experience","skills","vacancies"])
        ttk.Button(j,text="Refresh jobs",command=refresh).pack()
        a=tabs["Apply"]; self.heading(a,"Apply for a Job")
        fields=self.form(a,[("job_id","Job ID"),("name","Full name"),("phone","Phone"),("qualification","Qualification"),
            ("experience","Experience years"),("skills","Skills (comma separated)")])
        def apply():
            v=self.values(fields)
            try:
                jrow=query("SELECT * FROM jobs WHERE job_id=%s AND status='Open'",(int(v["job_id"]),))
                if not jrow: raise ValueError("Open job not found.")
                job=jrow[0]
                qscore=25 if v["qualification"].lower()==job["qualification"].lower() else 0
                req=float(job["experience"]); exp=float(v["experience"])
                escore=25 if req==0 or exp>=req else round(exp/req*25)
                reqs=[s.strip().lower() for s in (job["skills"] or "").split(",") if s.strip()]
                mine=[s.strip().lower() for s in v["skills"].split(",") if s.strip()]
                sscore=round(sum(1 for s in reqs if s in mine)/len(reqs)*25) if reqs else 0
                aid=execute("""INSERT INTO applicants(job_id,name,phone,qualification,experience,skills,
                    qualification_score,experience_score,skills_score,total_score)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (int(v["job_id"]),v["name"],v["phone"],v["qualification"],exp,v["skills"],qscore,escore,sscore,qscore+escore+sscore))
                messagebox.showinfo("Application received",f"Applicant ID: {aid}\nCurrent score: {qscore+escore+sscore}/100")
            except Exception as e: messagebox.showerror("Error",str(e))
        ttk.Button(a,text="Submit application",command=apply).pack(pady=8)

def main():
    try:
        setup_database()
        # Convert old shared employee passwords to a one-time temporary password.
        old_users = query("SELECT username,linked_id,password,must_change_password FROM users WHERE role='EMPLOYEE'")
        for account in old_users:
            if not account.get("must_change_password", 0):
                execute("UPDATE users SET password=%s,must_change_password=1 WHERE username=%s",
                        (hash_password("Welcome123"), account["username"]))
    except Exception as e:
        messagebox.showerror("MySQL setup error",
            "Could not connect to MySQL.\n\n1. Start MySQL Server.\n2. Edit DB_CONFIG in database.py and enter your MySQL password.\n3. Install mysql-connector-python.\n\nDetails: "+str(e))
        return
    root=tk.Tk()
    HRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
