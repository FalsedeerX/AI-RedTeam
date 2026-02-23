from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.sql.functions import user
from app.schema.targets import TargetCreate, TargetDetail, TargetScope, TargetPatch
from app.api.deps import get_current_user_id
from app.db.broker import TargetsBroker
from app.db.models import Targets


router = APIRouter(prefix="/targets", tags=["targets"])


class TargetsRouter:
    def __init__(self):
        self.router = router
        self.broker = TargetsBroker()
        self.router.get("", response_model=list[TargetDetail])(self.list_targets)
        self.router.post("", status_code=201, response_model=TargetDetail)(self.create_target)
        self.router.get("/{target_id}", response_model=TargetDetail)(self.get_target)
        self.router.delete("/{target_id}", status_code=204)(self.delete_target)
        self.router.patch("/{target_id}", response_model=TargetDetail)(self.update_target)

    def list_targets(self, payload: TargetScope, user_id: UUID = Depends(get_current_user_id)):
        """
        Receive a list of targets the specified project owns,
        Authentication of project ownership disabled for simplicity, will add dependency for checking in future.
        """
        return self.broker.list_by_project(payload.project_id)

    def create_target(self, payload: TargetCreate, user_id: UUID = Depends(get_current_user_id)):
        """
        Create a new target for the specified project 
        Authentication of project ownership disabled for simplicity, will add dependency for checking in future.
        """
        target_entry = self.broker.create(payload.model_dump())
        return target_entry

    def get_target(self, target_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """ Receive details for a specifed target id """
        # verify ownership
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        # retreive entry
        target_entry = self.broker.get(target_id)
        if not target_entry: raise HTTPException(status_code=404, detail="Target not found")
        return target_entry

    def delete_target(self, target_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """ Remove specified target from project """
        # verify ownership
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        # perform deletion
        deleted = self.broker.purge(target_id)
        if not deleted: raise HTTPException(status_code=404, detail="Target not found")

    def update_target(self, target_id: UUID, payload: TargetPatch, user_id: UUID = Depends(get_current_user_id)):
        """ Update information for a target """
        # verify ownership
        if self.broker.get_owner_id(target_id) != user_id:
            raise HTTPException(status_code=404, detail="Target not found")

        # verify the update data
        data = payload.model_dump(exclude_unset=True)
        if not data: raise HTTPException(status_code=400, detail="Incomplete patch payload")

        # preventing the value and project_type be none
        for key, value in data.items():
            if value is None and key != "label":
                raise HTTPException(status_code=400, detail=f"{key} can't be null")

        # path target
        patched_entry = self.broker.apply(target_id, data)
        if not patched_entry: raise HTTPException(status_code=404, detail="Target not found")


if __name__ == "__main__":
    pass
