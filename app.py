import os
import uuid
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
from flask import abort
from flask import send_file, flash
import threading, time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # ✅ Ensure uploads folder exists
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Firebase Admin
# cred = credentials.Certificate("/var/render/secrets/firebase_key_json")
cred = credentials.Certificate("/etc/secrets/firebase_key_json")
firebase_admin.initialize_app(cred, {
    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET", "flask-file-share.firebasestorage.app")
})
db = firestore.client()
bucket = storage.bucket()


# ---------------- ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/setuser', methods=['POST'])
def set_user():
    """Receive token from Firebase UI and store session"""
    id_token = request.json.get('token')
    try:
        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token['email']
        session['user_email'] = email
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 401


@app.route('/get_redirect')
def get_redirect():
    """Return the stored redirect URL after login"""
    next_url = session.pop('redirect_after_login', None)
    return jsonify({'next': next_url})


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_path)

            # Upload to Firebase Storage
            blob = bucket.blob(f'files/{uuid.uuid4()}_{filename}')
            blob.upload_from_filename(local_path)
            blob.make_public()
            file_url = blob.public_url

            # Save file info in Firestore
            file_id = str(uuid.uuid4())
            db.collection('files').document(file_id).set({
                'filename': filename,
                'url': file_url,
                'owner': session['user_email'],
                'uploadedAt': firestore.SERVER_TIMESTAMP
            })

            # Generate a shareable link
            link = url_for('download', file_id=file_id, _external=True)
            return render_template('dashboard.html', link=link)

    return render_template('dashboard.html')


@app.route('/download/<file_id>')
def download(file_id):
    if 'user_email' not in session:
        session['redirect_after_login'] = request.path  # store intended path
        return redirect(url_for('login'))

    # Fetch file info
    doc = db.collection('files').document(file_id).get()
    if doc.exists:
        file_data = doc.to_dict()

        # Log viewer info
        db.collection('downloads').add({
            'file_id': file_id,
            'viewer': session['user_email'],
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return redirect(file_data['url'])
    else:
        return render_template('404.html'), 404


@app.route('/admin/uploads')
def view_uploads():
    admin_email = "markpollycarp@gmail.com"
    if session.get('user_email') != admin_email:
        abort(403)

    uploads = db.collection('files').order_by('uploadedAt', direction=firestore.Query.DESCENDING).stream()

    history = []
    for entry in uploads:
        data = entry.to_dict()
        history.append({
            'filename': data.get('filename'),
            'owner': data.get('owner'),
            'timestamp': data.get('uploadedAt'),
            'url': data.get('url')
        })

    return render_template('uploads.html', history=history)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------------- MAIN ----------------

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
