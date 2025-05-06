# 📁 FileShare – A Secure File Sharing Web App

**FileShare** is a Flask-based web application designed for secure file sharing using Firebase Authentication and Cloud Storage. It allows users to upload files, generate shareable download links, and logs who accesses those files. Built with education and security in mind.

---

## 🚀 Features

- 🔐 Google & Email/Password login (via Firebase)
- ☁️ Upload files to Firebase Cloud Storage
- 🔗 Generate public download links
- 🧾 Track all downloads with user email & timestamp
- 🧑‍💼 Admin-only dashboard for uploads & downloads
- 🧱 Built with Flask + Firebase + Bootstrap

---

## 🧰 Tech Stack

- **Backend**: Python (Flask)
- **Frontend**: HTML, Bootstrap 5, Jinja2
- **Auth & Storage**: Firebase Authentication & Firebase Storage
- **Database**: Firebase Firestore

---

## 🛠️ Setup Instructions

### 🔧 Prerequisites

- Python 3.7+
- Firebase project with Authentication + Storage enabled
- Firebase Admin SDK JSON key

---

### 📦 Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/pollycarp/flask-file-share.git
   cd flask-file-share
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your `.env` file:**
   ```env
   SECRET_KEY=your_flask_secret_key
   FIREBASE_STORAGE_BUCKET=your-bucket-name.appspot.com
   ```

5. **Add your Firebase Admin SDK key:**
   - Rename the file to `firebase_key.json` and place it in the project root.

6. **Run the app:**
   ```bash
   flask run; python app.py
   ```

7. **Visit in browser:**
   ```
   http://localhost:5000
   ```

---

## 🔑 Admin Panel

To access admin-only routes:

- Log in using your authorized admin email (`markpollycarp@gmail.com`)
- You will see:
  - `/admin/uploads` – all file uploads
  - `/admin/downloads` – all file access logs

---

## 📂 Project Structure

```
flask-file-share/
│
├── app.py
├── firebase_key.json
├── .env
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── downloads.html
│   ├── uploads.html
│   └── components/
│       └── navbar.html
├── static/
│   └── style.css
├── uploads/ (temp storage)
```

---

## 🔒 Security Notes

- All downloads require login
- Only the admin email can view download/upload history
- `firebase_key.json` and `.env` are excluded via `.gitignore`

---

## 👨‍💻 Contact

**Mark Pollycarp**  
📧 Email: [markpollycarp@gmail.com](mailto:markpollycarp@gmail.com)  
📱 Phone/Whatsapp: +44 7429 144739  

---

## 📜 License

This project is for educational use only. Use at your own discretion.