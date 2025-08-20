import threading
import requests
from flask import Blueprint, request, jsonify
# from services.encryption_service import decrypt_file
from services.gemini_service import process_with_gemini
import uuid

# from services.firebase_service import log_to_firebase

upload_blueprint = Blueprint("upload", __name__)

def process(unique_id, response_uri, invoice, order, extra_files=[]):
    import json
    gemini_result = process_with_gemini(invoice, order, {}, extra_files)
    gemini_result['reasons'] = gemini_result.get('reasons', [])
    gemini_result['approved'] = gemini_result.get('approved', len(gemini_result['reasons']) == 0)
    conf = requests.post(response_uri, json={**gemini_result, "unique_id":str(unique_id)})
    ans = conf.json()
    if ans.get('status', None) != 'received':
        conf = requests.post(response_uri, json={**gemini_result, "unique_id":str(unique_id)})

    print(conf.json())

@upload_blueprint.route("/upload", methods=["POST"])
def upload_files():
    data = request.json
    response_uri = data.get("response_uri")
    invoice = data.get("files").get("invoice")
    order = data.get("files").get("order")
    extra_file_names = data.get("extra_charges", [])
    extra_files = [data.get("files").get(fname) for fname in extra_file_names]
    
    # if not response_uri:
    #     return jsonify({"error": "Missing response URI"}), 400

    # decrypted_files = {fname: decrypt_file(bytes.fromhex(enc)) for fname, enc in data.get("files", {}).items()}
    
    # log_to_firebase({"files_received": list(decrypted_files.keys()), "response_uri": response_uri})
    unique_id = uuid.uuid4()
    
    threading.Thread(target=process, args=(unique_id, response_uri, invoice, order, extra_files )).start()
    print({"status": "processing", "uuid": unique_id})
    return jsonify({"status": "processing", "uuid": unique_id}), 200