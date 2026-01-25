from app.db.base import Base


class Projects(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": "app"}



if __name__ == "__main__":
    pass
