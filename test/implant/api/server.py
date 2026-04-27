from flask import Flask, request, jsonify

app = Flask(__name__)

registered_agents = {}
reports = []


@app.route("/beacon", methods=["POST"])
def beacon():
    data = request.get_json()

    agent_id = data.get("agent_id")

    registered_agents[agent_id] = {
        "status": "alive",
        "ip": request.remote_addr
    }

    return jsonify({
        "status": "ok",
        "message": "agent registered"
    })


@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()

    reports.append(data)

    return jsonify({
        "status": "received"
    })


if __name__ == "__main__":
    app.run(port=8000)
