import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal
from routers import (
    auth_router,
    dashboard_router,
    exercises_router,
    workouts_router,
    templates_router,
    measurements_router,
    progress_router,
    profile_router,
    admin_router,
)
from utils.dependencies import get_optional_user, get_current_user_from_cookie


app = FastAPI(title="FitLog", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(exercises_router)
app.include_router(workouts_router)
app.include_router(templates_router)
app.include_router(measurements_router)
app.include_router(progress_router)
app.include_router(profile_router)
app.include_router(admin_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    try:
        from seed import seed_database
        seed_database()
    except Exception as e:
        print(f"Seed warning: {e}")


@app.get("/")
def root(request: Request):
    payload = get_current_user_from_cookie(request)
    if payload is not None:
        user_id_str = payload.get("sub")
        if user_id_str is not None:
            try:
                user_id = int(user_id_str)
                db = SessionLocal()
                try:
                    from models.user import User
                    user = db.query(User).filter(User.id == user_id).first()
                    if user is not None:
                        if user.role == "admin":
                            return RedirectResponse(url="/admin/dashboard", status_code=302)
                        return RedirectResponse(url="/dashboard", status_code=302)
                finally:
                    db.close()
            except (ValueError, TypeError):
                pass

    return RedirectResponse(url="/auth/login", status_code=302)


@app.get("/health")
def health_check():
    return {"status": "ok"}