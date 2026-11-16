# College Management API

FastAPI, SQLAlchemy 2.0, Pydantic v2, and SQLite. Requires Python 3.10+.
The scaffold lives directly in this workspace; the pre-existing `venv/` is untouched.

## Run on Linux

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI. Stop with Ctrl+C.
On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead.
Only if PowerShell blocks activation, use
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.
Activation is optional when using `.venv/bin/python` explicitly on Linux.

SQLite creates `college.db` in the working directory when the application starts.
Run from this directory so repeated launches use the same database.

## Manual End-to-End Validation

With a fresh database and the server running, execute in a second terminal:

```bash
curl -i http://127.0.0.1:8000/
curl -i http://127.0.0.1:8000/api/departments/
curl -i -X POST http://127.0.0.1:8000/api/departments/ -H 'Content-Type: application/json' -d '{"department_name":"Computer Science"}'
curl -i -X POST http://127.0.0.1:8000/api/departments/ -H 'Content-Type: application/json' -d '{"department_name":"Mechanical Engineering"}'
curl -i -X POST http://127.0.0.1:8000/api/students/ -H 'Content-Type: application/json' -d '{"student_name":"Asha Rao","department_id":1}'
curl -i -X POST http://127.0.0.1:8000/api/students/ -H 'Content-Type: application/json' -d '{"student_name":"Rahul Mehta","department_id":2}'
curl -i http://127.0.0.1:8000/api/students/
curl -i -X POST http://127.0.0.1:8000/api/students/ -H 'Content-Type: application/json' -d '{"student_name":"Ram","department_id":10}'
```

Both department POSTs return 201 with IDs 1 and 2 on a fresh database.
Both valid student POSTs return 201 with IDs, names, department IDs, and
`department_name`. The student GET returns both complete records.
The final POST returns 404 with `{"detail":"Department not found"}`.
For an existing database, use the actual IDs returned by the department POSTs.
Invalid names or nonpositive department IDs return FastAPI's 422 validation response.

## Line-by-Line Review

The following covers every nonblank scaffold line in file order. Blank lines
separate imports, definitions, and logical sections for readability; they do not
execute. Multi-line explanations below do not imply additional source lines.
This is the review content for the requested Ask-mode exercise, not a claim that
the editor was switched to Ask mode or that a human has approved the code.

### database.py

| Source line | What it does and why |
| --- | --- |
| `from collections.abc import Generator` | Imports the type describing a dependency that yields a session and receives/returns nothing. |
| `from sqlite3 import Connection` | Imports the SQLite connection type for the connection-hook annotation. |
| `from sqlalchemy import create_engine, event` | Imports the engine factory and event API needed to enable foreign keys on each connection. |
| `from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker` | Imports the model base class, session annotation, and session factory builder. |
| `from sqlalchemy.pool import ConnectionPoolEntry` | Types the event callback's required second argument. |
| `engine = create_engine("sqlite:///./college.db", connect_args={"check_same_thread": False})` | Configures the SQLite file and allows connections to be used across FastAPI worker threads; this does not make sessions safe to share concurrently. |
| `@event.listens_for(engine, "connect")` | Registers the following function for each new database connection. |
| `def enable_foreign_keys(connection: Connection, record: ConnectionPoolEntry) -> None:` | Receives the SQLite connection and pool record; `record` is unused but required by the callback signature. |
| `connection.execute("PRAGMA foreign_keys=ON")` | Enables SQLite's otherwise-disabled foreign-key enforcement. |
| `SessionLocal = sessionmaker(bind=engine)` | Builds a factory for separate ORM sessions using this engine. |
| `class Base(DeclarativeBase):` | Defines the shared registry and table metadata for both models. |
| `pass` | Supplies the required class body; inherited base functionality is sufficient. |
| `def get_db() -> Generator[Session, None, None]:` | Defines the yielding dependency used by request handlers. |
| `db = SessionLocal()` | Allocates a session for this dependency invocation. |
| `try:` | Ensures cleanup also runs if the handler raises an exception. |
| `yield db` | Gives the session to FastAPI's dependency consumer until cleanup. |
| `finally:` | Starts unconditional cleanup after dependency use. |
| `db.close()` | Releases session resources and rolls back any unfinished transaction. |

### models.py

| Source line | What it does and why |
| --- | --- |
| `from sqlalchemy import ForeignKey, String` | Imports foreign-key declarations and bounded SQL string types. |
| `from sqlalchemy.orm import Mapped, mapped_column, relationship` | Imports SQLAlchemy 2.0 typed attributes, column declarations, and object relationships. |
| `from database import Base` | Places both tables in the shared metadata. |
| `class Department(Base):` | Declares the department ORM model. |
| `__tablename__ = "departments"` | Names the physical SQL table used by the foreign key. |
| `department_id: Mapped[int] = mapped_column(primary_key=True)` | Defines the integer primary key; SQLite assigns an ID on insert. |
| `department_name: Mapped[str] = mapped_column(String(100))` | Defines a nonnullable name; Pydantic enforces the length because SQLite does not enforce VARCHAR length. |
| `students: Mapped[list["Student"]] = relationship(back_populates="department")` | Defines the department's student collection with a forward reference and bidirectional synchronization. |
| `class Student(Base):` | Declares the student ORM model. |
| `__tablename__ = "students"` | Names its physical SQL table. |
| `student_id: Mapped[int] = mapped_column(primary_key=True)` | Defines the student integer primary key. |
| `student_name: Mapped[str] = mapped_column(String(100))` | Defines the nonnullable student name. |
| `department_id: Mapped[int] = mapped_column(ForeignKey("departments.department_id"))` | Defines the required department foreign key with the exact requested target. |
| `department: Mapped[Department] = relationship(back_populates="students")` | Defines the related department and pairs it with the department's collection. |
| `@property` | Exposes a computed attribute instead of duplicating a department name in storage. |
| `def department_name(self) -> str:` | Names and types the attribute consumed by the output schema. |
| `return self.department.department_name` | Reads the current name from the related Department. |

### schemas.py

| Source line | What it does and why |
| --- | --- |
| `from pydantic import BaseModel, ConfigDict, Field` | Imports schema models, v2 configuration, and validation constraints. |
| `class DepartmentCreate(BaseModel):` | Defines the accepted department request body. |
| `department_name: str = Field(min_length=1, max_length=100)` | Requires a nonempty name no longer than 100 characters. |
| `class DepartmentOut(DepartmentCreate):` | Reuses the name field for department responses. |
| `model_config = ConfigDict(from_attributes=True)` | Allows response validation to read ORM attributes rather than only dictionaries. |
| `department_id: int` | Adds the generated department ID to responses. |
| `class StudentCreate(BaseModel):` | Defines the accepted student request body. |
| `student_name: str = Field(min_length=1, max_length=100)` | Applies the same name-length bounds to students. |
| `department_id: int = Field(gt=0)` | Requires a positive department ID; existence is checked by the router. |
| `class StudentOut(StudentCreate):` | Reuses student name and department ID for responses. |
| `model_config = ConfigDict(from_attributes=True)` | Enables ORM serialization, including the computed property. |
| `student_id: int` | Adds the generated student ID. |
| `department_name: str` | Includes the related department name in every student response. |

### routers/__init__.py

| Source line | What it does and why |
| --- | --- |
| `"""HTTP routers for the college management API."""` | Documents the package purpose; the initializer marks routers as a regular Python package. |

### routers/departments.py

| Source line | What it does and why |
| --- | --- |
| `from typing import Annotated` | Allows dependency metadata alongside a Python type. |
| `from fastapi import APIRouter, Depends, status` | Imports routing, dependency injection, and named HTTP status constants. |
| `from sqlalchemy import select` | Imports SQLAlchemy 2.0's query builder. |
| `from sqlalchemy.orm import Session` | Types the injected ORM session. |
| `from database import get_db` | Imports the session lifecycle dependency. |
| `from models import Department` | Imports the table-mapped department class. |
| `from schemas import DepartmentCreate, DepartmentOut` | Imports request and response contracts. |
| `router = APIRouter(prefix="/api/departments", tags=["Departments"])` | Groups department endpoints under the required prefix and Swagger tag. |
| `@router.get("/", response_model=list[DepartmentOut])` | Registers GET with a validated list response. |
| `def list_departments(db: Annotated[Session, Depends(get_db)]):` | Declares a synchronous handler with a request-scoped session. |
| `return db.scalars(select(Department).order_by(Department.department_id)).all()` | Fetches ORM departments in predictable ID order; an empty table returns `[]`. |
| `@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)` | Registers creation with the required 201 status and output schema. |
| `def create_department(payload: DepartmentCreate, db: Annotated[Session, Depends(get_db)]):` | Receives validated JSON and an injected session. |
| `department = Department(**payload.model_dump())` | Constructs an ORM object from the permitted input fields. |
| `db.add(department)` | Stages the new row for insertion. |
| `db.commit()` | Inserts and commits the row. |
| `db.refresh(department)` | Reloads generated values such as the primary key. |
| `return department` | Lets FastAPI serialize the object through DepartmentOut. |

### routers/students.py

| Source line | What it does and why |
| --- | --- |
| `from typing import Annotated` | Imports the type-plus-dependency annotation wrapper. |
| `from fastapi import APIRouter, Depends, HTTPException, status` | Imports routing, injection, explicit HTTP errors, and status constants. |
| `from sqlalchemy import select` | Imports the ORM query builder. |
| `from sqlalchemy.orm import Session, joinedload` | Imports the session type and eager relationship-loading option. |
| `from database import get_db` | Reuses the closing request-scoped session dependency. |
| `from models import Department, Student` | Imports the existence-check and student ORM models. |
| `from schemas import StudentCreate, StudentOut` | Imports student input and output contracts. |
| `router = APIRouter(prefix="/api/students", tags=["Students"])` | Sets the required route prefix and Swagger group. |
| `@router.get("/", response_model=list[StudentOut])` | Registers the student list endpoint and response contract. |
| `def list_students(db: Annotated[Session, Depends(get_db)]):` | Receives the injected database session. |
| `query = select(Student).options(joinedload(Student.department)).order_by(Student.student_id)` | Fetches students and departments together in stable order, avoiding one department query per student. |
| `return db.scalars(query).all()` | Returns all student ORM objects for schema serialization. |
| `@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)` | Registers student creation with status 201. |
| `def create_student(payload: StudentCreate, db: Annotated[Session, Depends(get_db)]):` | Receives validated student data and a session. |
| `department = db.get(Department, payload.department_id)` | Looks up the referenced department by primary key before insertion. |
| `if department is None:` | Detects a department that does not exist. |
| `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")` | Stops creation with the exact required 404 JSON detail. |
| `student = Student(student_name=payload.student_name, department=department)` | Builds the student using the verified relationship; SQLAlchemy fills the foreign key on flush. |
| `db.add(student)` | Stages the student row. |
| `db.commit()` | Persists the student and generated ID. |
| `db.refresh(student)` | Reloads the persisted column values. |
| `return student` | Serializes through StudentOut, reading department_name from the relationship property. |

### main.py

| Source line | What it does and why |
| --- | --- |
| `from contextlib import asynccontextmanager` | Imports the adapter for FastAPI's lifespan context. |
| `from fastapi import FastAPI` | Imports the application class. |
| `from database import Base, engine` | Imports table metadata and the database engine. |
| `from routers import departments, students` | Loads both routers and their models, registering tables before startup. |
| `@asynccontextmanager` | Converts the following async generator into a lifespan context manager. |
| `async def lifespan(app: FastAPI):` | Receives the application as required by FastAPI's lifespan interface; the parameter is unused. |
| `Base.metadata.create_all(bind=engine)` | Creates missing tables during startup, not during module import. |
| `yield` | Hands control to the running application; no special shutdown work is required here. |
| `app = FastAPI(title="College Management API", lifespan=lifespan)` | Creates the ASGI application and registers its startup lifecycle. |
| `app.include_router(departments.router)` | Publishes department routes. |
| `app.include_router(students.router)` | Publishes student routes. |
| `@app.get("/")` | Registers the root health/status endpoint. |
| `def root() -> dict[str, str]:` | Declares the status response's Python type. |
| `return {"status": "College Management API is running"}` | Returns a JSON status message. |

### requirements.txt

| Source line | What it does and why |
| --- | --- |
| `fastapi>=0.115,<1` | Installs a Pydantic-v2-compatible FastAPI release below the next major version. |
| `uvicorn[standard]>=0.30,<1` | Installs the ASGI server plus standard reload/performance dependencies. |
| `sqlalchemy>=2.0,<2.1` | Keeps SQLAlchemy within the requested 2.0 release series. |
| `pydantic>=2.0,<3` | Requires Pydantic v2 schema behavior. |

### .gitignore

| Source line | What it does and why |
| --- | --- |
| `.venv/` | Excludes the requested virtual environment. |
| `venv/` | Excludes the environment already present before scaffolding. |
| `__pycache__/` | Excludes generated Python cache directories at any depth. |
| `*.py[cod]` | Excludes compiled Python artifacts. |
| `college.db` | Excludes runtime data. |
| `college.db-*` | Excludes SQLite journal, WAL, and shared-memory sidecar files. |

## Review Findings and Limits

- The five requested code checks are satisfied: the exact foreign-key target,
  relationship-derived department_name, explicit missing-department 404,
  both 201 decorators, and session closure in finally.
- No known blocker was found in the initial import/schema check. HTTP validation
  is a separate step; source review alone does not establish runtime correctness.
- This is a local demonstration, not an authenticated or authorized production API.
- List routes are unpaginated and names need not be unique. Whitespace-only names
  pass length validation, and Pydantic's default coercion/extra-field behavior applies.
- Unexpected database errors are not translated into custom HTTP responses.
  Closing a failed session rolls back unfinished work; successful commits persist.
- SQLite suits this demo, not high-concurrency writes. Never share a Session
  concurrently. There is no delete route, so the department check has no competing
  in-API deletion path; external writers can still cause integrity failures.
- create_all creates missing tables but does not migrate existing ones. Use a
  migration tool such as Alembic when the schema needs to evolve.
- Dependency ranges are not a lockfile; record exact versions for reproducible
  deployment. The database location depends on the working directory.

## Validation Results

Verified locally with Python 3.12.3 using a fresh SQLite database and Uvicorn
at http://127.0.0.1:8000. Requests were checked with Python's standard-library
HTTP client, and Swagger UI was opened and inspected in the browser.

| Check | Result |
| --- | --- |
| Required scaffold and package initializer | PASS |
| Every nonblank scaffold line covered by review | PASS |
| All five requested source checks | PASS |
| Imports, relationship serialization, SQLite foreign-key enforcement | PASS |
| GET / and initially empty collection GETs | PASS: 200 |
| GET /docs and rendered Swagger operations | PASS |
| POST both example departments | PASS: 201, IDs 1 and 2, exact names |
| POST both example students | PASS: 201, all four required fields |
| GET both collections after creation | PASS: exact persisted records |
| POST Ram with department_id 10 | PASS: 404, exact Department not found detail |
| Rejected student is not persisted | PASS |
| Empty name, nonpositive department ID, missing student name | PASS: 422 |
| Server shutdown after validation | PASS: clean application shutdown |
| Commit | Review approved; use git log -1 --stat to inspect the commit record |

The ignored local database retains the two example departments and students.
Restart the server to inspect them; the fresh-database ID expectations do not
apply to repeated POSTs against that same database.

## Commit After Review

Read the review above and ask about any unclear line before approving a commit.
The editor's Ask/Agent mode selector is a manual UI action.

```bash
git init
git add .gitignore database.py models.py schemas.py main.py requirements.txt routers README.md
git status
git diff --cached --check
git commit -m "Scaffold College Management API with FastAPI"
git log -1 --stat
```

Git requires your real author identity. If absent, configure it locally using
`git config user.name "Your Name"` and
`git config user.email "you@example.com"` before committing.
Do not invent an identity or commit environments, caches, or database files.