# Smart Student Portal — Updated Edition

A beginner-friendly Flask + SQLite school portal with role-based student, teacher and administrator logins.

## Features
- Separate student, teacher and admin accounts. Accounts are created by authorised staff from the terminal; there is no public sign-up.
- Students can only see the student record linked to their own login.
- Teachers/admins can add and edit student records.
- Student fields: name, standard, section, admission number, address, phone number, weekly test, monthly test, quarterly exam, half-yearly exam, annual exam and attendance percentage.
- Marks and attendance accept values from 0 to 100; blank means not entered yet.
- Teachers/admins can publish school notices. Students see published changes after refreshing their dashboard.
- Passwords are stored as hashes, not plain text.
- Existing `school.db` student records are preserved; the app adds missing columns when it starts.

## Setup on Windows / VS Code
1. Extract this ZIP.
2. In VS Code choose **File → Open Folder** and select the extracted `smart_student_portal_updated` folder (the folder containing `app.py`).
3. Open **Terminal → New Terminal**.
4. Create a virtual environment if you do not already have one:
   ```powershell
   python -m venv .venv
   ```
5. Activate it in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.
6. Install packages:
   ```powershell
   python -m pip install -r requirements.txt
   ```
7. Create the first administrator account:
   ```powershell
   python -m flask --app app create-user
   ```
   Enter a username, choose role `admin`, then enter and confirm a password of at least 10 characters. Password typing is hidden. Do not type credentials as a PowerShell command.
8. Start the site:
   ```powershell
   python -m flask --app app run --debug
   ```
9. Open `http://127.0.0.1:5000` in your browser and sign in.

## Create staff and student accounts
Run `python -m flask --app app create-user` again for each account. Choose `teacher` for a teacher login and `student` for a student login. Then sign in as admin or teacher, open **Manage student records**, add the student's information, and select/link that student's login account in the form. A student login without a linked record will show a message asking staff to link it.

## Automatic updates
When a teacher/admin saves a student record or publishes a notice, the data is saved in the SQLite database. Students see the latest saved information when they refresh their dashboard. This starter does not send push notifications, SMS or email.

## Important privacy and safety notes
This is a local learning prototype, not a production-ready school information system. Get permission from school management and an adult/qualified IT administrator before using it with real student data. Address, phone numbers, marks and attendance are private information. Use test data while learning. Do not expose the local development server to the internet, do not publish `school.db`, passwords or secret keys to GitHub, and do not use Flask debug mode on a public server. A real deployment needs HTTPS, secure secret management, backups, access controls, audit logs and school-approved hosting. The example marks fields are out of 100; change validation and labels if your school uses different maximum marks.
