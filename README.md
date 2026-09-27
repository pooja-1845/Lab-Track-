# LabTrack 🧪

LabTrack is a lightweight web-based lab management platform built for teachers and students to manage, submit, and grade programming and practical lab assignments — all in one place.

Teachers can create labs, organize students into batches, track live submission progress, grade work, and communicate through a built-in class chat. Students can join labs via class codes or invitations, write and run code directly in the browser, track their scores, and revisit their past work anytime.

---

## ✨ Features

### For Teachers
- Create and manage labs (Programming, Data Science, DBMS, Networking)
- Organize students into batches
- Invite specific students to labs, or share a join code
- Live dashboard with stats: total students, active labs, pending grading, average score
- Weekly submission activity chart
- Review student code, output, and uploaded report files
- Download any student's submitted code directly
- Grade submissions and control when marks are visible to students
- Live progress tracking per lab (who has started, how far along)
- Batch-wise and lab-wise class performance reports
- Real-time class chat with unread message badges and sound alerts

### For Students
- Join labs via class code or teacher invite
- Get notified of new lab invitations with an in-app banner
- Write code directly in-browser (Python, Java, C, C++, SQL) with a built-in editor
- Run code instantly and see real output before submitting
- Auto-save while typing — no need to manually save constantly
- Non-programming labs (Data Science / DBMS / Networking) supported via protected answer boxes (copy-paste disabled to encourage original work)
- Upload a final report file per lab
- View personal score history with saved code, output, and a personal download option
- Real-time class chat with unread message badges and sound alerts
- See assigned batch on the dashboard

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Database:** SQLite
- **Frontend:** HTML, CSS (custom, no framework), Vanilla JavaScript
- **Code Editor:** CodeMirror
- **In-browser SQL execution:** sql.js (SQLite compiled to WebAssembly)
- **Code Execution:** Wandbox API (Python / Java / C / C++)
- **Auth:** Session-based login with hashed passwords (Werkzeug)

---

## 📂 Project Structure

labtrack/
├── app.py # Main Flask application & all routes
├── models.py # Database models (User, Lab, Submission, Invitation, Message, Batch)
├── templates/ # Jinja2 HTML templates
│ ├── index.html
│ ├── login.html
│ ├── signup.html
│ ├── teacher_dashboard.html
│ ├── student_dashboard.html
│ ├── create_lab.html
│ ├── edit_lab.html
│ ├── manage_labs.html
│ ├── manage_batches.html
│ ├── grade_labs.html
│ ├── view_submissions.html
│ ├── live_progress.html
│ ├── invite_student.html
│ ├── class_report.html
│ ├── class_chat.html
│ ├── my_scores.html
│ └── lab_created.html
├── uploads/ # Uploaded student report files (auto-created)
├── lab.db # SQLite database (auto-created)
└── requirements.txt


---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/pooja-1845/lab-Track-.git
   cd lab-Track-
```

2. **Create a virtual environment (recommended)**
```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Run the app**
```bash
   python app.py
```

5. **Open your browser**

http://localhost:5000


The SQLite database (`lab.db`) and `uploads/` folder are created automatically on first run.

---

## 📋 requirements.txt

Flask
Flask-SQLAlchemy
requests
Werkzeug
---

## 🔑 Usage

1. **Sign up** as either a **Teacher** or a **Student**.
2. **Teachers** can create labs, generate a join code, invite students, assign batches, and grade submissions from the dashboard.
3. **Students** can join a lab using the class code (or accept a teacher invite), write/run code, and submit their work — progress auto-saves as they type.
4. Both roles have access to a shared **Class Chat** with real-time unread-message notifications.

---

## ⚠️ Notes & Limitations

- Code execution relies on the free public [Wandbox](https://wandbox.org) API — as a shared community service, it may occasionally be slow or briefly unavailable. No API key is required.
- Client-side copy-paste restrictions on code/answer boxes are a soft deterrent (JavaScript-based) and not a substitute for full academic-integrity enforcement.
- This project uses SQLite for simplicity — for production/multi-user deployment at scale, consider migrating to PostgreSQL or MySQL.

---

## 🙌 Acknowledgements

- [CodeMirror](https://codemirror.net/) — in-browser code editor
- [sql.js](https://sql.js.org/) — SQLite compiled to WebAssembly for in-browser SQL execution
- [Wandbox](https://wandbox.org/) — free online compiler service
