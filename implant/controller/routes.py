from uuid import UUID
from flask import Blueprint, render_template


frontend_bp = Blueprint("frontend", __name__)


@frontend_bp.route("/")
def index():
    return render_template("dashboard.html")


@frontend_bp.route("/contracts")
def contracts():
    return render_template("contracts.html")


@frontend_bp.route("/manage/<uuid:agent_id>")
def manage(agent_id: UUID):
    return render_template("manage.html", agent_id=agent_id)


if __name__ == "__main__":
    pass
