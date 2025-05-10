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


# @app.route('/dashboard', methods=['GET', 'POST'])
# def dashboard():
#     if 'user_email' not in session:
#         return redirect(url_for('login'))
#
#     if request.method == 'POST':
#         file = request.files['file']
#         if file:
#             filename = secure_filename(file.filename)
#             local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(local_path)
#
#             # Upload to Firebase Storage
#             blob = bucket.blob(f'files/{uuid.uuid4()}_{filename}')
#             blob.upload_from_filename(local_path)
#             blob.make_public()
#             file_url = blob.public_url
#
#             # Save file info in Firestore
#             file_id = str(uuid.uuid4())
#             db.collection('files').document(file_id).set({
#                 'filename': filename,
#                 'url': file_url,
#                 'owner': session['user_email'],
#                 'uploadedAt': firestore.SERVER_TIMESTAMP
#             })
#
#             # Generate a shareable link
#             link = url_for('download', file_id=file_id, _external=True)
#             return render_template('dashboard.html', link=link)
#
#     return render_template('dashboard.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            file = request.files['file']
            if file:
                # Ensure safe file name
                filename = secure_filename(file.filename)

                # Use /tmp folder for file saving in Render
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(local_path)

                # Generate unique blob name
                blob_name = f"{uuid.uuid4()}_{filename}"

                # Upload to Firebase Storage
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_path)

                # Save metadata to Firestore
                file_id = str(uuid.uuid4())
                db.collection('files').document(file_id).set({
                    'file_id': file_id,
                    'original_name': filename,
                    'blob_name': blob_name,
                    'owner': session['user_email'],
                    'uploadedAt': firestore.SERVER_TIMESTAMP
                })

                flash("✅ File uploaded successfully.")
                return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            flash("❌ Upload failed. Please try again.")

    return render_template('dashboard.html')


# @app.route('/download/<file_id>')
# def download(file_id):
#     if 'user_email' not in session:
#         session['redirect_after_login'] = request.path  # store intended path
#         return redirect(url_for('login'))
#
#     # Fetch file info
#     doc = db.collection('files').document(file_id).get()
#     if doc.exists:
#         file_data = doc.to_dict()
#
#         # Log viewer info
#         db.collection('downloads').add({
#             'file_id': file_id,
#             'viewer': session['user_email'],
#             'timestamp': firestore.SERVER_TIMESTAMP
#         })
#
#         return redirect(file_data['url'])
#     else:
#         return render_template('404.html'), 404
@app.route('/download/<file_id>', methods=['GET', 'POST'])
def download(file_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    # Fetch file info
    doc = db.collection('files').document(file_id).get()
    if not doc.exists:
        flash("File not found.")
        return redirect(url_for('dashboard'))

    file_data = doc.to_dict()
    blob_name = file_data.get('blob_name')
    original_name = file_data.get('original_name')

    # Download blob to temp file
    blob = bucket.blob(blob_name)
    temp_path = os.path.join('/tmp', original_name)
    blob.download_to_filename(temp_path)

    # Clean up temp file in background after download
    def cleanup(path):
        time.sleep(5)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=cleanup, args=(temp_path,)).start()

    return send_file(temp_path, as_attachment=True, download_name=original_name)

# @app.route('/downloads')
# def downloads():
#     if 'user_email' not in session:
#         return redirect(url_for('login'))
#
#     docs = db.collection('files').order_by('uploadedAt', direction=firestore.Query.DESCENDING).stream()
#     files = []
#     for doc in docs:
#         data = doc.to_dict()
#         files.append({
#             'original_name': data['original_name'],
#             'blob_name': data['blob_name']
#         })
#     return render_template('downloads.html', files=files)


# @app.route('/download/<blob_name>', methods=['POST'])
# def download_file(blob_name):
#     if 'user_email' not in session:
#         return redirect(url_for('login'))
#
#     original_name = blob_name.split("_", 1)[-1]
#     local_path = os.path.join(app.config['UPLOAD_FOLDER'], original_name)
#
#     # Download from Firebase
#     blob = bucket.blob(blob_name)
#     blob.download_to_filename(local_path)
#
#     flash(f"Download successful! File: {original_name}")
#
#     # Send the file, then delete the temp file in background
#     def cleanup():
#         time.sleep(5)
#         if os.path.exists(local_path):
#             os.remove(local_path)
#
#     threading.Thread(target=cleanup).start()
#
#     return send_file(local_path, as_attachment=True, download_name=original_name)


# @app.route('/admin/downloads')
# def view_downloads():
#     admin_email = "markpollycarp@gmail.com"
#     if session.get('user_email') != admin_email:
#         abort(403)
#
#     downloads = db.collection('downloads').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
#
#     history = []
#     for entry in downloads:
#         data = entry.to_dict()
#         file_id = data.get('file_id')
#         viewer = data.get('viewer')
#         timestamp = data.get('timestamp')
#
#         file_doc = db.collection('files').document(file_id).get()
#         filename = file_doc.to_dict().get('filename') if file_doc.exists else '[Deleted]'
#
#         history.append({
#             'filename': filename,
#             'viewer': viewer,
#             'timestamp': timestamp
#         })
#
#     return render_template('downloads.html', history=history)


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
