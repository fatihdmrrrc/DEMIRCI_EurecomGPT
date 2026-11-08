import os
from flask import Flask, request, jsonify

app = Flask(__name__)


def build_echo(msg: str) -> dict:
    """Build the dictionary response with the echo string and its length."""
    return {
        "echo": msg,
        "length": len(msg)
    }


def extract_message(query_params: dict | None, body: dict | None) -> str | None:
    """Extract message string from query dict (key 'msg') or JSON body dict (key 'message')."""
    if query_params and "msg" in query_params:
        return query_params.get("msg")
    if body and isinstance(body, dict) and "message" in body:
        return body.get("message")
    return None


@app.route("/echo", methods=["GET", "POST"])
def echo_route():
    query_params = request.args.to_dict() if request.args else None
    body = request.get_json(silent=True) if request.is_json else None

    msg = extract_message(query_params, body)
    if msg is None:
        return jsonify({"error": "Missing message parameter"}), 400
    return jsonify(build_echo(msg)), 200


@app.route("/health", methods=["GET"])
@app.route("/", methods=["GET"])
def health():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
