# AI-Powered Smart Gate & Security Command Center

A unified security platform combining visitor management, facial recognition, watchlist alerts, and incident tracking.

## Features

- **Visitor Pre-Approval**: Digital visitor registration with photo capture
- **Gate Entry Verification**: Face-based identity verification using AWS Rekognition
- **Watchlist Alerts**: Real-time threat detection and alerts
- **Incident Management**: Log, track, and resolve security incidents
- **Security Dashboard**: Centralized command center view

## Tech Stack

- **Frontend**: Streamlit (responsive web UI)
- **Backend**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Face Recognition**: AWS Rekognition
- **Storage**: AWS S3 for images
- **Real-time**: WebSocket for live alerts

## Project Structure

```
smart-gate-security/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── visitor.py
│   │   │   ├── entry_log.py
│   │   │   ├── watchlist.py
│   │   │   └── incident.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── face_recognition.py
│   │   │   ├── visitor_service.py
│   │   │   ├── watchlist_service.py
│   │   │   └── incident_service.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── visitors.py
│   │       ├── gate.py
│   │       ├── watchlist.py
│   │       ├── incidents.py
│   │       └── dashboard.py
│   └── requirements.txt
├── frontend/
│   ├── app.py
│   ├── pages/
│   │   ├── 1_🏠_Dashboard.py
│   │   ├── 2_👤_Visitor_Approval.py
│   │   ├── 3_🚪_Gate_Verification.py
│   │   ├── 4_⚠️_Watchlist.py
│   │   └── 5_📋_Incidents.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py
│   │   ├── metrics.py
│   │   └── charts.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── api_client.py
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### 1. Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your AWS credentials and database settings
```

### 3. Setup Database

```bash
# Start PostgreSQL (or use Docker)
docker-compose up -d postgres

# Run migrations
cd backend
alembic upgrade head
```

### 4. Start Services

```bash
# Terminal 1: Start Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Frontend
cd frontend
streamlit run app.py --server.port 8501
```

### 5. Access Application

- **Frontend Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

## AWS Setup

1. Create an S3 bucket for face images
2. Create a Rekognition collection for face indexing
3. Configure IAM credentials with appropriate permissions

## Database Schema

See `docs/database_schema.md` for detailed schema documentation.

## API Endpoints

See `docs/api_endpoints.md` or visit `/docs` when running the backend.

## License

MIT License


git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin git@github.com:antinozorionktr/gaurd_ai.git
git push -u origin main