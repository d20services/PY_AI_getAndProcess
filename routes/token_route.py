import jwt
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from config import JWT_SECRET

token_blueprint = Blueprint("token", __name__)

@token_blueprint.route("/token", methods=["GET"])
def get_token():
    payload = {"exp":datetime.now(timezone.utc) + timedelta(hours=2)}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return jsonify({"token": token}), 200