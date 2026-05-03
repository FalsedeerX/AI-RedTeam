import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.targets import TargetCreate, TargetDetail, TargetPatch
from app.domain.target import TargetType
from app.api.deps import get_current_user_id, require_project_owner
from app.core.deployment import enforce_approved_target
from app.db.broker import TargetsBroker
from app.db.models import Targets


# Nested under projects so URLs match the frontend:
#   GET  /projects/{project_id}/targets
#   POST /projects/{project_id}/targets
#   GET  /projects/{project_id}/targets/{target_id}
#   DELETE /projects/{project_id}/targets/{target_id}
#   PATCH  /projects/{project_id}/targets/{target_id}
router = APIRouter(prefix="/projects/{project_id}/targets", tags=["targets"])

_CIDR_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def infer_target_type(value: str) -> TargetType:
    """Infer TargetType from the value string so the frontend doesn't need to send it."""
    v = value.strip()
    if _URL_RE.match(v):
        return TargetType.URL
    if _CIDR_RE.match(v):
        return TargetType.CIDR
    if _IP_RE.match(v):
        return TargetType.IP
    return TargetType.DOMAIN


class TargetCreateRequest(TargetCreate):
    """
    Frontend-facing create schema — project_id and target_type are optional
    because they come from the URL path and auto-inference respectively.
    """
    project_id: UUID | None = None
    target_type: TargetType | None = None


class TargetsRouter:
    def __init__(self):
        self.router = router
        self.broker = TargetsBroker()
        self.router.get("", response_model=list[TargetDetail])(self.list_targets)
        self.router.post("", status_code=201, response_model=TargetDetail)(self.create_target)
        self.router.get("/{target_id}", response_model=TargetDetail)(self.get_target)
        self.router.delete("/{target_id}", status_code=204)(self.delete_target)
        self.router.patch("/{target_id}", response_model=TargetDetail)(self.update_target)

    def list_targets(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """List all targets belonging to a project owned by the caller."""
        require_project_owner(project_id, user_id)
        return self.broker.list_by_project(project_id)

    def create_target(self, project_id: UUID, payload: TargetCreateRequest, user_id: UUID = Depends(get_current_user_id)):
        """
        Create a new target for the project in the URL path.
        target_type is inferred from the value if not supplied by the caller.
        """
        require_project_owner(project_id, user_id)
        approved_value = enforce_approved_target(payload.value)
        resolved_type = payload.target_type or infer_target_type(approved_value)
        data = {
            "project_id": project_id,
            "value": approved_value,
            "label": payload.label,
            "target_type": resolved_type,
        }
        return self.broker.create(data)

    def get_target(self, project_id: UUID, target_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """Retrieve details for a specific target."""
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        target_entry = self.broker.get(target_id)
        if not target_entry:
            raise HTTPException(status_code=404, detail="Target not found")
        return target_entry

    def delete_target(self, project_id: UUID, target_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """Remove a target from the project."""
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        deleted = self.broker.purge(target_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Target not found")

    def update_target(self, project_id: UUID, target_id: UUID, payload: TargetPatch, user_id: UUID = Depends(get_current_user_id)):
        """Update one or more fields on a target."""
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="Incomplete patch payload")

        for key, value in data.items():
            if value is None and key != "label":
                raise HTTPException(status_code=400, detail=f"{key} can't be null")
        if "value" in data:
            data["value"] = enforce_approved_target(data["value"])
            data["target_type"] = TargetType.URL

        patched_entry = self.broker.apply(target_id, data)
        if not patched_entry:
            raise HTTPException(status_code=404, detail="Target not found")
        return patched_entry


if __name__ == "__main__":
    pass
