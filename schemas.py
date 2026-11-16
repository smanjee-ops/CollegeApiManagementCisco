from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    department_name: str = Field(min_length=1, max_length=100)


class DepartmentOut(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    department_id: int


class StudentCreate(BaseModel):
    student_name: str = Field(min_length=1, max_length=100)
    department_id: int = Field(gt=0)


class StudentOut(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    department_name: str