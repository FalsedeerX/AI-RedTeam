from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.targets import TargetCreate, TargetDetail, TargetPatch
from app.db.broker import TargetsBroker


router = APIRouter("/targets", tags=["targets"])


class TargetsRouter:
    def __init__(self):
        self.router = router
        self.broker = TargetsBroker()

    def list_targets(self):
        pass

    def create_target(self):
        pass

    def delete_target(self):
        pass

    def update_target(self):
        pass
