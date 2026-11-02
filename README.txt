INTEGRATED RECRUITMENT AND HR MANAGEMENT SYSTEM
Simple Python + Tkinter + MySQL version

REQUIREMENTS
- Python 3.10 or later
- MySQL Server running on your computer
- MySQL Workbench (optional, useful for viewing tables)

SETUP
1. Install MySQL Server and make sure the MySQL service is running.
2. Open database.py.
3. In DB_CONFIG, replace YOUR_MYSQL_PASSWORD with your MySQL root password.
   If your MySQL root account has no password, use an empty string: "".
4. Open Command Prompt / VS Code terminal in this project folder.
5. Install the connector:
      py -m pip install mysql-connector-python
6. Run:
      py main.py

The program creates the integrated_hr database and its tables automatically.

DEMO LOGIN
HR:
  Username: hr
  Password: hr123

When HR hires an applicant or adds an employee, an employee login is created:
  Username: employee ID in lowercase (example: emp001)
  Password: emp123

IMPORTANT
- This is a simple academic prototype, not a production HR/payroll system.
- Demo passwords are stored plainly to keep the first version easy to understand.
  Do not use real employee information or real passwords.
- Applicant ranking currently uses qualification (25), experience (25), and skills (25).
  The remaining 25 points can be added as the interview score by HR.
- Attendance can currently be entered as individual records. Excel import is a later enhancement.
- The project uses shared MySQL tables so that employee records are not separately duplicated
  across modules.
- Use test data first. Back up the database before making changes.

CURRENT BASIC MODULES
- HR login and dashboard
- Job openings and job applications
- Candidate suitability score and ranking
- Applicant status update and hiring
- Employee profile and departments
- Attendance records
- Employee leave application and HR approval/rejection
- Employee HR requests and HR decision
- Performance evaluation and training request workflow
- Payroll calculation
- Bonus/promotion logic can be connected after the shared employee performance data is finalized
- Employee exit process

NEXT IMPROVEMENTS
- Import attendance directly from Excel
- Add interview score field and candidate tracking login
- Add bonus/promotion recommendations using actual employee evaluation data
- Add stronger password security and role permissions
- Add employee profile editing and reports


UPDATED LOGIN AND FORM BEHAVIOUR
- Employee username is the employee ID in lowercase (example: emp004).
- Temporary first-login password: Welcome123
- On first employee login, the employee must create and confirm a personal password (minimum 8 characters).
- Employee passwords are stored using PBKDF2-HMAC-SHA256 hashing.
- Existing employee accounts are migrated at startup to the temporary password Welcome123 and must change it at first login.
- HR login remains: hr / hr123.
- Employee search is by Employee ID only.
- Hiring an applicant uses one combined form.
- Employee exit start/complete operations use one combined form.
- Attendance entry and department creation use one combined form.

IMPORTANT:
- Keep your existing MySQL database; the update does not drop tables.
- Your MySQL password in database.py has been preserved from the files you supplied.
- This remains an academic prototype. Back up your database before testing.


LATEST ATTENDANCE AND TRAINING UPDATES
- Employees can mark today's attendance as Present or WFH. The system records the date and timestamp.
- Employees cannot mark attendance twice for the same date.
- Employees can submit attendance correction requests with a reason.
- HR can view attendance records and approve/reject correction requests. Approved corrections update the attendance record.
- Employee dashboard shows current-month attendance counts and percentage.
- Employees can accept or reject pending training recommendations. A rejection reason is required.
- HR can view employee responses and move accepted training to In Progress or Completed.
- Existing databases are upgraded automatically with the additional columns and attendance_corrections table.
- Salary/payroll behaviour has not been changed in this update.

Please back up the database before using the updated version. Test using dummy employee records first.
