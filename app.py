import os
import uuid
import threading
import time
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file, flash, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['UPLOAD_FOLDER'] = '/tmp'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Firebase Admin
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
    id_token = request.json.get('token')
    try:
        decoded_token = auth.verify_id_token(id_token)
        session['user_email'] = decoded_token['email']
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 401


@app.route('/get_redirect')
def get_redirect():
    next_url = session.pop('redirect_after_login', None)
    return jsonify({'next': next_url})


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    # Show success message after redirect
    if session.pop('after_download_redirect', False):
        flash('✅ Download successful!')

    if request.method == 'POST':
        try:
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(local_path)

                blob_name = f"{uuid.uuid4()}_{filename}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_path)

                file_id = str(uuid.uuid4())
                db.collection('files').document(file_id).set({
                    'file_id': file_id,
                    'filename': filename,
                    'blob_name': blob_name,
                    'owner': session['user_email'],
                    'uploadedAt': firestore.SERVER_TIMESTAMP
                })

                link = url_for('download_confirm', file_id=file_id, _external=True)
                return render_template('dashboard.html', link=link)
        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            flash("Upload failed. Please try again.")

    return render_template('dashboard.html')


@app.route('/download/<file_id>', methods=['GET'])
def download_confirm(file_id):
    if 'user_email' not in session:
        session['redirect_after_login'] = request.path
        return redirect(url_for('login'))

    doc = db.collection('files').document(file_id).get()
    if not doc.exists:
        return render_template('404.html'), 404

    file_data = doc.to_dict()
    return render_template('download_confirm.html', file_id=file_id, filename=file_data.get('filename'))


@app.route('/download/<file_id>', methods=['POST'])
def download_file(file_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    doc = db.collection('files').document(file_id).get()
    if not doc.exists:
        return render_template('404.html'), 404

    file_data = doc.to_dict()
    blob_name = file_data.get('blob_name')
    original_name = file_data.get('filename')

    # Log download
    db.collection('downloads').add({
        'file_id': file_id,
        'viewer': session['user_email'],
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    blob = bucket.blob(blob_name)
    temp_path = os.path.join('/tmp', original_name)
    blob.download_to_filename(temp_path)

    # Cleanup after sending
    def cleanup(path):
        time.sleep(5)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=cleanup, args=(temp_path,)).start()

    # Flash message to show on dashboard after redirect
    session['after_download_redirect'] = True

    return send_file(temp_path, as_attachment=True, download_name=original_name)


@app.route('/admin/uploads')
def view_uploads():
    if session.get('user_email') != "markpollycarp@gmail.com":
        abort(403)

    uploads = db.collection('files').order_by('uploadedAt', direction=firestore.Query.DESCENDING).stream()
    history = []
    for entry in uploads:
        data = entry.to_dict()
        file_id = entry.id
        history.append({
            'filename': data.get('filename'),
            'owner': data.get('owner'),
            'timestamp': data.get('uploadedAt'),
            'link': url_for('download_confirm', file_id=file_id, _external=True)
        })

    return render_template('admin_uploads.html', history=history)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------------- MAIN ----------------

if __name__ == '__main__':
    app.run(debug=True)