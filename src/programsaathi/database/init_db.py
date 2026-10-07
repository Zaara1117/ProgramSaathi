"""Database schema initialization and seed runner for Azure SQL and local stores."""

from datetime import date
from typing import Optional
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from programsaathi.database.tables import (
    BaseTable,
    ProjectModel,
    MilestoneModel,
    StakeholderModel,
)
from programsaathi.logging import get_logger

logger = get_logger(__name__)


def init_database(engine: Engine) -> None:
    """Creates all 17 tables matching database/schema.sql on the target database engine."""
    logger.info("Initializing database schema from metadata models...")
    BaseTable.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")


def seed_database(session: Session) -> dict[str, str]:
    """Applies initial baseline seed data if not already present."""
    logger.info("Executing database seed...")

    # Check if seed project already exists
    existing = session.query(ProjectModel).filter_by(project_key="PRGMS").first()
    if existing:
        logger.info("Seed project 'PRGMS' already present; skipping seed insert.")
        return {"project_id": existing.id}

    project = ProjectModel(
        id="a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        project_key="PRGMS",
        name="ProgramSaathi Core Engine",
        description="AI-powered Program & Project Management agent built on Microsoft Azure and Python.",
        status="PLANNING",
        priority="HIGH",
    )
    session.add(project)

    stakeholder = StakeholderModel(
        id="b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
        name="Dev Lead",
        email="devlead@example.com",
        role="Principal Software Architect",
        is_approver=True,
        organization="Core Engineering",
    )
    session.add(stakeholder)

    milestone = MilestoneModel(
        id="c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
        project_id=project.id,
        title="Phase 1 Architecture Baseline",
        description="Python foundational models, configuration, tool boundaries and tests sign-off.",
        target_date=date(2026, 10, 15),
        status="IN_PROGRESS",
    )
    session.add(milestone)

    session.commit()
    logger.info(f"Database seeded successfully with project '{project.project_key}' ({project.id}).")
    return {"project_id": project.id, "stakeholder_id": stakeholder.id, "milestone_id": milestone.id}
