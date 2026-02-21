# Base = @Entity
# Column = @Column
# Enum = Java enum

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# Java의 enum RobotStatus { IDLE, WORKING, CHARGING, ERROR }
class RobotStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    CHARGING = "charging"
    ERROR = "error"

# @Entity @Table(name="robots")
class Robot(Base):
    __tablename__ = "robots"

    # @Id @GeneratedValue
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # @Column(nullable=false)
    name = Column(String, nullable=False)
    status = Column(SQLEnum(RobotStatus), default=RobotStatus.IDLE)
    battery = Column(Float, default=100.0)   # 배터리 % (0~100)
    x = Column(Float, default=0.0)           # 현재 x 좌표
    y = Column(Float, default=0.0)           # 현재 y 좌표
    current_task_id = Column(String, nullable=True)  # 현재 작업 ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)