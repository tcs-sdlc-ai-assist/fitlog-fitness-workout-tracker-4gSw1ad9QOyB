# FitLog

A comprehensive fitness tracking API built with Python and FastAPI. Track workouts, exercises, sets, and monitor your fitness progress over time.

## Features

- **User Authentication** — Register, login, and manage user accounts with JWT-based authentication
- **Workout Management** — Create, read, update, and delete workout sessions
- **Exercise Library** — Browse and manage a library of exercises with muscle group categorization
- **Set Tracking** — Log individual sets with weight, reps, duration, and distance metrics
- **Progress Analytics** — View workout history, personal records, and progress over time
- **RESTful API** — Clean, well-documented API endpoints following REST conventions

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (via aiosqlite for async) / PostgreSQL (production)
- **ORM:** SQLAlchemy 2.0 (async)
- **Authentication:** JWT (python-jose) + bcrypt password hashing
- **Validation:** Pydantic v2
- **Migrations:** Alembic
- **Server:** Uvicorn (ASGI)
- **Testing:** pytest + httpx (async)

## Folder Structure

```
fitlog/
├── app/
│   ├── core/
│   │   ├── config.py          # Application settings (BaseSettings)
│   │   ├── database.py        # Async SQLAlchemy engine & session
│   │   ├── security.py        # JWT creation/verification, password hashing
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── exercise.py        # Exercise model
│   │   ├── workout.py         # Workout model
│   │   ├── workout_set.py     # WorkoutSet model
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py            # User request/response schemas
│   │   ├── exercise.py        # Exercise request/response schemas
│   │   ├── workout.py         # Workout request/response schemas
│   │   ├── workout_set.py     # WorkoutSet request/response schemas
│   │   └── __init__.py
│   ├── services/
│   │   ├── user.py            # User business logic
│   │   ├── exercise.py        # Exercise business logic
│   │   ├── workout.py         # Workout business logic
│   │   ├── workout_set.py     # WorkoutSet business logic
│   │   └── __init__.py
│   ├── routers/
│   │   ├── auth.py            # Authentication routes (register, login)
│   │   ├── users.py           # User profile routes
│   │   ├── exercises.py       # Exercise CRUD routes
│   │   ├── workouts.py        # Workout CRUD routes
│   │   ├── workout_sets.py    # WorkoutSet CRUD routes
│   │   └── __init__.py
│   ├── dependencies/
│   │   ├── auth.py            # get_current_user dependency
│   │   └── __init__.py
│   ├── main.py                # FastAPI app entry point
│   └── __init__.py
├── alembic/
│   ├── versions/              # Migration scripts
│   ├── env.py                 # Alembic environment config
│   └── script.py.mako         # Migration template
├── tests/
│   ├── conftest.py            # Shared fixtures (async client, test DB)
│   ├── test_auth.py           # Authentication endpoint tests
│   ├── test_exercises.py      # Exercise endpoint tests
│   ├── test_workouts.py       # Workout endpoint tests
│   └── test_workout_sets.py   # WorkoutSet endpoint tests
├── alembic.ini                # Alembic configuration
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fitlog
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update the values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application
APP_NAME=FitLog
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./fitlog.db

# Authentication
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

> **Important:** Generate a strong `SECRET_KEY` for production:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

### 5. Run Database Migrations

```bash
alembic upgrade head
```

To create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe your changes"
alembic upgrade head
```

### 6. Seed the Database (Optional)

If a seed script is provided:

```bash
python -m app.seed
```

### 7. Start the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive Docs (Swagger):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Route Reference

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/register` | Register a new user | No |
| `POST` | `/api/auth/login` | Login and receive JWT token | No |

### Users

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/users/me` | Get current user profile | Yes |
| `PUT` | `/api/users/me` | Update current user profile | Yes |
| `DELETE` | `/api/users/me` | Delete current user account | Yes |

### Exercises

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/exercises` | List all exercises (with filters) | Yes |
| `POST` | `/api/exercises` | Create a new exercise | Yes |
| `GET` | `/api/exercises/{id}` | Get exercise by ID | Yes |
| `PUT` | `/api/exercises/{id}` | Update an exercise | Yes |
| `DELETE` | `/api/exercises/{id}` | Delete an exercise | Yes |

### Workouts

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/workouts` | List user's workouts (paginated) | Yes |
| `POST` | `/api/workouts` | Create a new workout | Yes |
| `GET` | `/api/workouts/{id}` | Get workout details with sets | Yes |
| `PUT` | `/api/workouts/{id}` | Update a workout | Yes |
| `DELETE` | `/api/workouts/{id}` | Delete a workout | Yes |

### Workout Sets

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/workouts/{workout_id}/sets` | List sets for a workout | Yes |
| `POST` | `/api/workouts/{workout_id}/sets` | Add a set to a workout | Yes |
| `PUT` | `/api/workouts/{workout_id}/sets/{id}` | Update a set | Yes |
| `DELETE` | `/api/workouts/{workout_id}/sets/{id}` | Delete a set | Yes |

### Common Query Parameters

- `skip` (int, default: 0) — Number of records to skip (pagination offset)
- `limit` (int, default: 20) — Maximum number of records to return
- `muscle_group` (str, optional) — Filter exercises by muscle group
- `date_from` / `date_to` (date, optional) — Filter workouts by date range

### Authentication

All authenticated endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Obtain a token by calling `POST /api/auth/login` with valid credentials.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

## Deployment to Vercel

### 1. Install the Vercel CLI

```bash
npm install -g vercel
```

### 2. Create `vercel.json`

Add a `vercel.json` file to the project root:

```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### 3. Configure Environment Variables on Vercel

Set the following environment variables in your Vercel project settings:

- `SECRET_KEY` — A strong random secret key
- `DATABASE_URL` — Your production database connection string (e.g., PostgreSQL)
- `ALGORITHM` — `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — `1440`
- `CORS_ORIGINS` — JSON array of allowed origins
- `DEBUG` — `false`

> **Note:** For production, use a hosted PostgreSQL database (e.g., Neon, Supabase, Railway) instead of SQLite. Update `DATABASE_URL` accordingly:
> ```
> DATABASE_URL=postgresql+asyncpg://user:password@host:5432/fitlog
> ```
> Ensure `asyncpg` is included in `requirements.txt` when using PostgreSQL.

### 4. Deploy

```bash
vercel --prod
```

### Production Considerations

- Set `DEBUG=false` in production environment variables
- Use a strong, unique `SECRET_KEY` (minimum 64 characters)
- Configure `CORS_ORIGINS` to only allow your frontend domain(s)
- Use PostgreSQL with connection pooling for production workloads
- Enable HTTPS (handled automatically by Vercel)
- Set appropriate `ACCESS_TOKEN_EXPIRE_MINUTES` for your security requirements

## License

Private — All rights reserved.