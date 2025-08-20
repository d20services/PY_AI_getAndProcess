import json
from datetime import datetime
import threading
from queue import Queue
from googleapiclient.discovery import build
from google.oauth2 import service_account

log_queue = Queue()


def get_services():
    creds = service_account.Credentials.from_service_account_file(os.environ['SHEETS_KEY'], scopes=SCOPES)
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    folder_id = '1XGZJUbpNZk4OSW09puPCcdHtaeLFgmji'
    return sheets_service, drive_service

def init_log(sheet_title, folder_id):
    sheets_service, drive_service = get_services()

    # Check if sheet exists
    query = f"name='{sheet_title}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    if results['files']:
        return results['files'][0]['id']

    # Create new sheet
    spreadsheet = {
        'properties': {'title': sheet_title}
    }
    sheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    sheet_id = sheet['spreadsheetId']

    # Move to folder
    drive_service.files().update(
        fileId=sheet_id,
        addParents=folder_id,
        removeParents='root',
        fields='id, parents'
    ).execute()

    # Add headers
    headers = [["Rev_UUID", "Contrato", "Archivos Revisados", "Estado", "Detalle", "Días de crédito", "Response JSON", "Timestamp respuesta"]]
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="A1:H1",
        valueInputOption="RAW",
        body={"values": headers}
    ).execute()

    return sheet_id


def update_log_entry(row, uuid, contract_id, file_count, status, details, credit_days, response_dict, is_result=False):
    log_queue.put({'row': row, 'entry': {
        'uuid': uuid,
        'contract_id': contract_id,
        'file_count': file_count,
        'status': status,
        'details': details,
        'credit_days': credit_days,
        'response_dict': response_dict,
        'is_result': is_result
    }})


def mark_response(rownum, uuid, status, details, response_dict):    
    contract_id = None
    file_count = None
    credit_days = None
    is_result=True
    update_log_entry(rownum, uuid, contract_id, file_count, status, details, credit_days, response_dict, is_result=is_result)
    

def mark_timeouts(sheet_id):
    sheets_service, _ = get_services()
    result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A2:H").execute()
    rows = result.get('values', [])
    for i, row in enumerate(rows, start=2):
        status = row[3] if len(row) > 3 else ''
        if status in ['', 'pending', 'processing']:
            update_log_entry(i, row[0], row[1], row[2], "Timed Out", '', row[5], {}, is_result=True)

def write_to_sheet(sheet_id, row, entry):
    sheets_service, _ = get_services()
    values = [[
        entry['uuid'],
        entry.get('contract_id', ''),
        entry.get('file_count', ''),
        entry.get('status', ''),
        entry.get('details', ''),
        entry.get('credit_days', ''),
        json.dumps(entry.get('response_dict', {})),
        datetime.now().isoformat() if entry.get('is_result', False) else ''
    ]]
    range_str = f"A{row}:H{row}"
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_str,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

def log_writer(sheet_id):
    while True:
        item = log_queue.get()
        if item is None:
            break
        write_to_sheet(sheet_id, item['row'], item['entry'])
        log_queue.task_done()
