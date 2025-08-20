import firebase_admin
from firebase_admin import credentials, firestore
from config import FIREBASE_CREDENTIALS

cred = credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred)
db = firestore.client()

def log_to_firebase(data):
    db.collection("file_logs").add(data)