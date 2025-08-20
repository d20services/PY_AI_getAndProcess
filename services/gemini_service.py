from google import genai
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    GoogleSearch,
    HarmBlockThreshold,
    HarmCategory,
    Part,
    SafetySetting,
    ThinkingConfig,
    Tool,
    ToolCodeExecution,
)
import json
import os
# from database import store_processed_data


def process_with_gemini(invoice_file, order_file, reservation_dict, extra_charges_files=[], retry = False):
    prompt = """
        Analyze the attached PDF and extract the required data as a JSON object. Return only the final JSON with the following structure:

            {
              driver_name: [Driver's name from the 'Conductor' section - avoid using 'Razon Social'],
              car: [Car model and type - ignore the color],
              start_date: [Value from 'Fecha salida'],
              end_date: [Value from 'Fecha entrada'],
              payment_method: [Text within parentheses in the top payment method header - exclude values like 'paid form'],
              invoice_data: {
                name: [From 'Cliente'],
                RFC: [From 'Cliente'],
                address: [From 'Cliente']
              },
              rental_length: [From 'Cargos renta'],
              cost_per_day: [From 'Cargos renta'],
              coverages: [
                { coverage: string, length: number, cost_per_day: number, total: number }
                // Include only if length and cost are present
              ],
              extra_services: [
                { service: string, length: number, cost_per_day: number, total: number }
                // Include only if length and cost are present
              ],
              extra_charges: [
                { charge_description: string, total: number }
                // Include only if cost is present
              ],
              total_cost: [Found at the very bottom of 'Cargos extra' section - includes all charges],
              payment_guarantee: [Text from the 'Garantia de pago' box in bottom-left - e.g. 'Green Credit - Corp']
            }

            Invoice Structure Notes:
            - Skip the logo and top-right metadata.
            - 'Conductor' section contains the driver's name.
            - 'Datos de renta' provides car info and rental dates.
            - Rental location and legal entity are not needed.
            - 'Cliente' section (right side) gives name, RFC, and address for invoicing.
            - 'Cargos renta': rows for each car with duration, cost/day, and totals; late delivery and mileage charges if present.
            - Include fuel costs if listed (e.g., 'Auto uno', 'Auto dos').
            - 'Coberturas' and 'Servicios extras': include only populated rows with numeric values.
            - 'Cargos extras': description and totals only.
            - 'Garantia de pago' (bottom-left): extract exact match for the guarantee entity name.
            - Ignore 'Descuentos' entirely.
            - If end_date < start_date, they might be inverted - handle carefully.

            Return only the structured JSON, no extra text or explanation.
"""
    API_KEY = os.environ['GEMINI_API_KEY']
    client = genai.Client( api_key=API_KEY)
    MODEL_ID = "gemini-2.5-flash"
    response = client.models.generate_content(
        model=MODEL_ID, contents=[
            Part.from_bytes(data=invoice_file, mime_type="application/pdf"),
            prompt
            ]
    )
    
    try:

        invoice_dict = json.loads(response.text.replace('```', '')[4:])

    except:
        if retry:
            return {'approved': False, 'reasons': ['Comparison error']}
        return process_with_gemini(invoice_file, order_file, reservation_dict, extra_charges_files)

    
    prompt = """
        Compare the information in this file - call it 'garantia' - and this object - call it 'factura'.

            Create a JSON using the ID of each item with the format: {id: {status, detail}}, indicating either 'ok' or an inconsistency.

            Items to check:
            - driver_name: Should be the similar in both documents, allow a fuzzy match and some incompleteness, but it must not be totally different. Even with one name and one lastname match we can be ok.
            - car: Should match in type, or be at least similar in both documents.
            - start_date: Start date (sometimes 'inicio renta' or 'fecha salida') should match within a 12-hour window. 
            - end_date: Return date (sometimes 'fin renta' or 'fecha entrada') should match within a 12-hour window.
            - payment method: Must be 'Green Credit', 'Green Credit CORP' or similar in 'factura'. If 'garantia' clearly states something else than a credit or something like it, alert but do not consider as incosistency.
            - invoice_data:
              - If data is missing in 'garantia', do not compare or consider inconsistent. If data is different then it is incosistent.
              - Legal name should be similar (ignore suffixes).
              - RFC must match exactly (or be absent in 'garantia').
              - Zipcodes must match (or be absent in 'garantia').
              - Address may partially match city/state if not contradictory (or be absent).
            - rental length: Should align with both documents' dates. Count full days from first hour and round appropriately.
            - cost: Must match in both, or be absent in 'garantia'. If absent in 'garantia' consider as ok.
            - extra services: Services and coverages should be similar. Only consider items with price and length. Length must match rental period.
              - Ignore 'cargo por uso de sistema' if absent in 'garantia'.
              - 'Basic insurance' refers to CDW-if 'basic' is selected in 'garantia', it may refer to CDW.

            If no inconsistencies are found, add:
              approved: true

            If any inconsistencies are found:
              approved: false
              reasons: [list of item keys that failed]

            Final JSON structure:
            {
              driver_name: {status, detail},
              car: {status, detail},
              start_date: {status, detail},
              end_date: {status, detail},
              payment method: {status, detail},
              invoice_data: {status, detail},
              rental length: {status, detail},
              cost: {status, detail},
              extra sevices: {status, detail},
              approved: true or false depending on inconsistencies,
              reasons: [list of item keys that failed],
              otros detalles: [list of inconsistencies found outside defined items]
            }

            Return only the JSON with this structure. All 'detail' fields must explain the reasoning in Mexican Spanish.
            """
    response = client.models.generate_content(
        model=MODEL_ID, contents=[
            Part.from_bytes(data=order_file, mime_type="application/pdf"),
            Part.from_text(text=f'{invoice_dict}'),
            prompt
            ]
    )
    try:

        comparison_dict = json.loads(response.text.replace('```', '')[4:])

    except:
        if retry:
            return {'approved': False, 'reasons': ['Comparison error']}
        return process_with_gemini(invoice_file, order_file, reservation_dict, extra_charges_files)

    return comparison_dict

