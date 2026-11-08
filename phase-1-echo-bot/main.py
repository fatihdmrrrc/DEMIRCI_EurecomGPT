import functions_framework
from flask import jsonify
from app import extract_message, build_echo

@functions_framework.http
def echo(request):
    query_params = request.args.to_dict() if request.args else None
    body = request.get_json(silent=True) if request.is_json else None

    msg = extract_message(query_params, body)
    if msg is None:
        return jsonify({"error": "Missing message parameter"}), 400
    return jsonify(build_echo(msg)), 200
