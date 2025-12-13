from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import init_db
from .services.face_recognition import face_service
from .routers import (
    auth_router,
    visitors_router,
    gate_router,
    watchlist_router,
    incidents_router,
    dashboard_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Smart Gate Security API...")
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Check face recognition service
    logger.info("Checking face recognition service...")
    stats = face_service.get_stats()
    logger.info(f"Face database: {stats['total_faces']} faces registered")
    
    logger.info("Application startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart Gate Security API...")


# Create FastAPI app
app = FastAPI(
    title="Smart Gate Security API",
    description="""
    AI-Powered Smart Gate & Security Command Center API
    
    ## Features
    - **Authentication**: JWT-based auth with Role-Based Access Control (RBAC)
    - **Visitor Management**: Pre-approve visitors with face registration
    - **Gate Verification**: Face-based identity verification at entry points
    - **Watchlist Alerts**: Real-time threat detection and alerts
    - **Incident Management**: Log, track, and resolve security incidents
    - **Dashboard**: Centralized security command center data
    
    ## Roles
    - **Super Admin**: Full system access
    - **Admin**: Manage users, settings, view all
    - **Security Manager**: Manage security staff, view reports
    - **Security Guard**: Gate operations, basic incident reporting
    - **Resident**: Pre-approve visitors, view own data
    - **Receptionist**: Visitor management
    
    ## Authentication
    Use `/api/auth/login` to get JWT tokens. Include in header: `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(visitors_router, prefix="/api")
app.include_router(gate_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Smart Gate Security API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "face_recognition": "DeepFace with FaceNet512"
    }


@app.get("/api/test-face-service")
async def test_face_service():
    """Test face recognition service connectivity"""
    try:
        stats = face_service.get_stats()
        return {
            "status": "ok",
            "model": "FaceNet512",
            "detector": "RetinaFace",
            "storage": "local",
            "total_faces": stats['total_faces'],
            "faces_by_type": stats['by_type']
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
