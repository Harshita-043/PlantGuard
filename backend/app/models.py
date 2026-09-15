"""
SQLAlchemy Database Models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    User model for authentication (simplified for now)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plant_scans = relationship("PlantScan", back_populates="user")


class PlantScan(Base):
    """
    Plant scan metadata and results
    """
    __tablename__ = "plant_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(String(255), nullable=False)  # Path or URL to stored image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Scan metadata
    plant_name = Column(String(100), nullable=True)  # User-assigned or detected
    scan_type = Column(String(20), default="image")  # image, video, live
    status = Column(String(20), default="completed")  # pending, processing, completed, failed

    # Overall results (denormalized for quick access)
    overall_health_score = Column(Float, nullable=True)
    risk_assessment = Column(String(10), nullable=True)  # low, medium, high

    # Relationships
    user = relationship("User", back_populates="plant_scans")
    leaf_results = relationship("LeafResult", back_populates="scan", cascade="all, delete-orphan")
    health_report = relationship("HealthReport", back_populates="scan", uselist=False, cascade="all, delete-orphan")


class LeafResult(Base):
    """
    Per-leaf analysis results
    """
    __tablename__ = "leaf_results"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("plant_scans.id"), nullable=False)
    leaf_index = Column(Integer, nullable=False)  # Index of leaf in this scan

    # Leaf detection
    bounding_box = Column(JSON)  # [x_min, y_min, width, height] normalized 0-1
    detection_confidence = Column(Float, nullable=True)

    # Disease classification
    disease_class = Column(String(50), nullable=False)
    classification_confidence = Column(Float, nullable=False)

    # Disease segmentation
    diseased_area_ratio = Column(Float, nullable=False)  # 0-1
    disease_bounding_box = Column(JSON)  # [x_min, y_min, width, height] normalized

    # Severity calculation
    severity_score = Column(Float, nullable=False)  # 0-1
    severity_level = Column(String(10), nullable=False)  # low, medium, high
    affected_percentage = Column(Float, nullable=False)  # 0-100

    # Explainability (we won't store the actual heatmap images, just metadata)
    explainability_generated = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    scan = relationship("PlantScan", back_populates="leaf_results")


class HealthReport(Base):
    """
    Plant-level aggregated health report
    """
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("plant_scans.id"), nullable=False, unique=True)

    # Overall assessment
    overall_health_score = Column(Float, nullable=False)  # 0-100
    risk_assessment = Column(String(10), nullable=False)  # low, medium, high

    # Disease summary
    healthy_leaf_count = Column(Integer, default=0)
    total_leaf_count = Column(Integer, default=0)
    disease_summary = Column(JSON)  # Dictionary of disease counts

    # Recommendations
    recommendations = Column(JSON)  # Array of recommendation strings

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    scan = relationship("PlantScan", back_populates="health_report")