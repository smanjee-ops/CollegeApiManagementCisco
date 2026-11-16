from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Department
from schemas import DepartmentCreate, DepartmentOut

router = APIRouter(prefix="/api/departments", tags=["Departments"])


@router.get("/", response_model=list[DepartmentOut])
def list_departments(db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(Department).order_by(Department.department_id)).all()


@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Annotated[Session, Depends(get_db)]):
    department = Department(**payload.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department