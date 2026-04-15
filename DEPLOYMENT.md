# Deployment Guide — FitLog on Vercel

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Vercel Configuration](#vercel-configuration)
4. [Build and Deploy Steps](#build-and-deploy-steps)
5. [SQLite Considerations on Serverless](#sqlite-considerations-on-serverless)
6. [Database Seeding](#database-seeding)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## Prerequisites

- Python 3.11 or higher
- A [Vercel](https://vercel.com) account
- [Vercel CLI](https://vercel.com/docs/cli) installed (`npm i -g vercel`)
- Git repository connected to Vercel (GitHub, GitLab, or Bitbucket)

---

## Environment Variables

Configure the following environment variables in your Vercel project dashboard under **Settings → Environment Variables**. All variables must be set for **Production**, **Preview**, and **Development** environments unless noted otherwise.

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | Secret key for JWT signing and session security. Must be a strong random string (min 32 chars). | `openssl rand -hex 32` |
| `DATABASE_URL` | No | SQLAlchemy-compatible database URL. Defaults to local SQLite if not set. | `sqlite+aiosqlite:///./fitlog.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT access token lifetime in minutes. Defaults to `30`. | `60` |
| `CORS_ORIGINS` | No | Comma-separated list of allowed CORS origins. Defaults to `*` in dev. | `https://fitlog.vercel.app,https://custom-domain.com` |
| `ENVIRONMENT` | No | Deployment environment identifier. | `production` |
| `LOG_LEVEL` | No | Python logging level. Defaults to `INFO`. | `WARNING` |

### Setting Environment Variables via Vercel CLI

```bash
# Set a single variable
vercel env add SECRET_KEY production

# Or set from a local .env file (for development)
vercel env pull .env.local
```

### Generating a Secure SECRET_KEY

```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

> **⚠️ Security Warning:** Never commit your `.env` file or secret keys to version control. The `.gitignore` file should already include `.env*` patterns.

---

## Vercel Configuration

Create or verify the `vercel.json` file in the project root:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ],
  "env": {
    "ENVIRONMENT": "production"
  }
}
```

### Key Configuration Details

- **`builds`**: Uses the `@vercel/python` runtime to serve the FastAPI application via the ASGI handler in `app/main.py`.
- **`routes`**: The first route serves static files directly. The catch-all route forwards all other requests to the FastAPI app.
- **`env`**: Inline environment variables that are safe to commit (non-secret values only).

### Required File: `requirements.txt`

Vercel's Python runtime installs dependencies from `requirements.txt` at the project root. Ensure this file is present and up to date:

```bash
pip freeze > requirements.txt
```

Or maintain it manually to keep only direct dependencies (recommended).

---

## Build and Deploy Steps

### First-Time Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd fitlog

# 2. Install Vercel CLI if not already installed
npm install -g vercel

# 3. Link to your Vercel project
vercel link

# 4. Set environment variables
vercel env add SECRET_KEY production
# (repeat for other required variables)

# 5. Deploy to preview
vercel

# 6. Deploy to production
vercel --prod
```

### Subsequent Deployments

Vercel automatically deploys on every push to the connected Git repository:

- **Push to `main` branch** → Production deployment
- **Push to any other branch** → Preview deployment
- **Pull requests** → Preview deployment with unique URL

### Manual Deployment

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

### Local Development

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env
# Edit .env with your local values

# 4. Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` and the interactive docs at `http://localhost:8000/docs`.

---

## SQLite Considerations on Serverless

### The Ephemeral Filesystem Problem

Vercel serverless functions run on **read-only, ephemeral filesystems**. This has critical implications for SQLite:

1. **The filesystem is read-only** — SQLite cannot create or write to database files in the deployment bundle.
2. **No persistent storage** — Even if writes were possible, each function invocation may run on a different container, so data would not persist between requests.
3. **The `/tmp` directory is writable but ephemeral** — Data written to `/tmp` is lost when the container is recycled (typically after a few minutes of inactivity).

### Recommended Approaches

#### Option 1: Use `/tmp` for SQLite (Development/Demo Only)

Configure the database URL to use the `/tmp` directory:

```python
# In app/core/config.py or via environment variable
DATABASE_URL = "sqlite+aiosqlite:////tmp/fitlog.db"
```

**Pros:** Simple, no external services needed.
**Cons:** Data is lost on every cold start. Only suitable for demos or testing.

#### Option 2: Use a Managed Database (Production Recommended)

For production deployments, use an external database service:

| Service | DATABASE_URL Format |
|---|---|
| **Vercel Postgres** | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| **Neon** | `postgresql+asyncpg://user:pass@host/dbname?sslmode=require` |
| **PlanetScale** | Use `aiomysql` driver with PlanetScale connection string |
| **Turso (libSQL)** | `sqlite+aiosqlite:///` with Turso HTTP sync |
| **Supabase** | `postgresql+asyncpg://user:pass@host:5432/dbname` |

To switch to PostgreSQL:

```bash
# 1. Add asyncpg to requirements.txt
echo "asyncpg>=0.29.0" >> requirements.txt

# 2. Set the DATABASE_URL environment variable
vercel env add DATABASE_URL production
# Enter: postgresql+asyncpg://user:password@host:5432/fitlog
```

The application's SQLAlchemy async engine will automatically use the correct driver based on the URL scheme.

#### Option 3: Pre-seeded Read-Only SQLite

If your use case is read-heavy with infrequent writes:

1. Seed the SQLite database locally.
2. Include the `.db` file in the deployment bundle.
3. Configure SQLAlchemy with `connect_args={"check_same_thread": False}` (already set for SQLite).
4. Accept that writes will fail or be lost.

### Database Initialization on Serverless

The application uses a lifespan handler to create tables on startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```

On Vercel, this runs on every cold start. For `/tmp`-based SQLite, this means the database is recreated fresh each time the container spins up.

---

## Database Seeding

### Local Seeding

Run the seed script to populate the database with initial data:

```bash
# Activate your virtual environment
source venv/bin/activate

# Run the seed script
python -m app.seed

# Or if a seed endpoint exists:
curl -X POST http://localhost:8000/api/seed
```

### Seeding on Vercel

For serverless deployments with an external database:

```bash
# 1. Set DATABASE_URL to your production database locally
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/fitlog"

# 2. Run the seed script
python -m app.seed
```

Alternatively, if the application exposes a seed endpoint (protected by admin authentication):

```bash
curl -X POST https://your-app.vercel.app/api/seed \
  -H "Authorization: Bearer <admin-token>"
```

### Seed Data Contents

The seed script typically creates:

- Default admin user account
- Sample exercise categories
- Example workout templates
- Demo data for testing (if `ENVIRONMENT != production`)

---

## Troubleshooting Common Issues

### 1. `ModuleNotFoundError: No module named 'xyz'`

**Cause:** Missing dependency in `requirements.txt`.

**Fix:**
```bash
# Add the missing package
echo "xyz>=1.0.0" >> requirements.txt

# Redeploy
vercel --prod
```

### 2. `500 Internal Server Error` on All Routes

**Cause:** Application fails to start. Usually a configuration or import error.

**Fix:**
```bash
# Check Vercel function logs
vercel logs <deployment-url>

# Common causes:
# - Missing SECRET_KEY environment variable
# - Invalid DATABASE_URL format
# - Import error in a Python module
```

### 3. `sqlite3.OperationalError: attempt to write a readonly database`

**Cause:** SQLite trying to write to the read-only deployment filesystem.

**Fix:** Set `DATABASE_URL` to use `/tmp` or switch to an external database:
```bash
vercel env add DATABASE_URL production
# Enter: sqlite+aiosqlite:////tmp/fitlog.db
```

### 4. `422 Unprocessable Entity` on Form Submissions

**Cause:** Form field names don't match FastAPI `Form()` parameter names, or `python-multipart` is missing.

**Fix:**
- Verify `python-multipart` is in `requirements.txt`
- Check that HTML form `name=` attributes match the endpoint's parameter names exactly

### 5. CORS Errors in Browser Console

**Cause:** Frontend origin not in the allowed CORS origins list.

**Fix:**
```bash
vercel env add CORS_ORIGINS production
# Enter: https://your-frontend.vercel.app,https://your-domain.com
```

### 6. `MissingGreenlet: greenlet_spawn has not been called`

**Cause:** Lazy loading triggered in an async context. A SQLAlchemy relationship is being accessed without eager loading.

**Fix:** Add `selectinload()` to the query that fetches the object:
```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Workout).options(selectinload(Workout.exercises))
)
```

### 7. Cold Start Timeouts

**Cause:** Vercel serverless functions have a 10-second (Hobby) or 60-second (Pro) execution limit. Cold starts with heavy imports can be slow.

**Fix:**
- Minimize top-level imports in route files
- Use lazy imports for heavy libraries where possible
- Upgrade to Vercel Pro for longer timeouts
- Consider using Vercel's Edge Functions for lightweight endpoints

### 8. `TemplateNotFound` Error

**Cause:** Jinja2 template directory path is relative and doesn't resolve correctly on Vercel.

**Fix:** Ensure template directory uses an absolute path:
```python
from pathlib import Path
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
```

### 9. Static Files Not Loading (404)

**Cause:** Static file route not configured in `vercel.json`, or path mismatch.

**Fix:** Verify the `vercel.json` routes section includes a static file rule:
```json
{
  "src": "/static/(.*)",
  "dest": "/app/static/$1"
}
```

### 10. Database Connection Pool Exhaustion

**Cause:** Serverless functions open new connections on every cold start without closing them.

**Fix:** Configure conservative pool settings for serverless:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=1,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=300,
)
```

---

## Vercel Deployment Checklist

Before deploying to production, verify:

- [ ] `SECRET_KEY` is set and is a strong random value (≥32 characters)
- [ ] `DATABASE_URL` is configured for a persistent database (not `/tmp` SQLite)
- [ ] `CORS_ORIGINS` is set to your actual frontend domain(s)
- [ ] `requirements.txt` includes all dependencies with pinned versions
- [ ] `vercel.json` is present with correct build and route configuration
- [ ] All database migrations have been applied to the production database
- [ ] Seed data has been loaded if needed
- [ ] Static files are accessible via the configured route
- [ ] Health check endpoint (`/health` or `/`) returns 200
- [ ] Authentication flow works end-to-end (register → login → access protected route)
- [ ] Vercel function logs show no startup errors