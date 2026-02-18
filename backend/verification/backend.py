from flask import Flask, request, jsonify
from .services.auth_service import login
from .services.scan_service import start_scan
from .services.report_service import generate_report

app = Flask(__name__)


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    token = login(data["username"], data["password"])
    if not token:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"token": token})


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.json
    scan_id = start_scan(data["target_id"])
    return jsonify({
        "message": "Scan completed",
        "scan_id": scan_id,
    })


@app.route("/api/report/<scan_id>", methods=["GET"])
def api_report(scan_id):
    report = generate_report(scan_id)
    return jsonify(report)


@app.route("/api/health")
def health():
    return jsonify({
        "service": "RedTeam AI Agent Backend",
        "status": "operational",
        "mode": "simulation",
    })


if __name__ == "__main__":
    app.run(debug=True)

