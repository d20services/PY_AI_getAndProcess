import threading
import requests
from flask import Blueprint, request, jsonify
# from services.encryption_service import decrypt_file
from services.gemini_service import process_with_gemini
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime, timedelta
import os
import json
# from services.firebase_service import log_to_firebase

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

creds = service_account.Credentials.from_service_account_info(json.loads(os.environ['SHEETS_KEY']), scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)
folder_id = '1XGZJUbpNZk4OSW09puPCcdHtaeLFgmji'

upload_blueprint = Blueprint("upload", __name__)

def process(unique_id, consecutivo, sheet_id, invoice, order, extra_files=[]):
    import json
    gemini_result = process_with_gemini(invoice, order, {}, extra_files)
    gemini_result['reasons'] = gemini_result.get('reasons', [])
    gemini_result['approved'] = gemini_result.get('approved', len(gemini_result['reasons']) == 0)

  
    unique_id = gemini_result.get("unique_id")
    status_ok = gemini_result.get("approved")
    status = "aprobado" if status_ok else "rechazado"
    reasons = ""
    for r in gemini_result.get('reasons'):
        reasons += f"\n {r}: {gemini_result.get(r).get('detail')}"
    from services.log_utility import mark_response
    mark_response(int(consecutivo), unique_id, status,
                    f"{reasons}", f"{gemini_result}")

@upload_blueprint.route("/upload", methods=["POST"])
def upload_files():

    data = request.json
    today = (datetime.now() - timedelta(days=0)).strftime("%Y-%m-%d")
    today = data.get("ref_date", today)
    sheet_title = f"{today}_results.xlsx"

    from services.log_utility import init_log
    sheet_id = init_log(sheet_title, folder_id)
    from services.log_utility import log_writer
    threading.Thread(target=log_writer, daemon=True).start()
    consecutivo = data.get("consecutivo")
    invoice = data.get("files").get("invoice")
    order = data.get("files").get("order")
    extra_file_names = data.get("extra_charges", [])
    extra_files = [data.get("files").get(fname) for fname in extra_file_names]
    
    # if not response_uri:
    #     return jsonify({"error": "Missing response URI"}), 400

    # decrypted_files = {fname: decrypt_file(bytes.fromhex(enc)) for fname, enc in data.get("files", {}).items()}
    
    # log_to_firebase({"files_received": list(decrypted_files.keys()), "response_uri": response_uri})
    unique_id = uuid.uuid4()
    
    threading.Thread(target=process, args=(unique_id, consecutivo, sheet_id, invoice, order, extra_files )).start()
    print({"status": "processing", "uuid": unique_id})
    return jsonify({"status": "processing", "uuid": unique_id}), 200