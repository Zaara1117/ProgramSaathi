"""Phase 3: SQL Repository tests using SQLite in-memory (no Azure credentials needed).

Tests cover:
- Database schema creation and seeding
- CRUD operations via SQL repositories
- Transaction rollback on error
- Foreign-key constraints
- Approval/mutation/audit patterns
- AzureSQLService health / availability when unconfigured
"""

import json
import uuid
from datetime import date, datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from programsaathi.database.tables import (
    BaseTable,
    ProjectModel,
    StakeholderModel,
    MilestoneModel,
    RequirementModel,
    TaskModel,
    ApprovalRequestModel,
    ProjectEventModel,
    BlockerModel,
    RiskModel,
)
from programsaathi.database.connection import DatabaseSessionManager, create_db_engine
from programsaathi.database.init_db import init_database, seed_database
from programsaathi.models.project import Project, Stakeholder, Milestone
from programsaathi.models.work_items import Requirement, Task
from programsaathi.models.governance import ApprovalRequest, ProjectEvent
from programsaathi.models.base import (
    ApprovalStatus,
    ProjectStatus,
    Priority,
    ItemStatus,
)
from programsaathi.repositories.sql_repo import (
    SQLProjectRepository,
    SQLMilestoneRepository,
    SQLStakeholderRepository,
    SQLRequirementRepository,
    SQLTaskRepository,
    SQLApprovalRequestRepository,
    SQLProjectEventRepository,
    SQLRiskRepository,
    SQLBlockerRepository,
)
from programsaathi.services.database import AzureSQLService, MockDatabaseService
from programsaathi.exceptions import DatabaseServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_sqlite_engine():
    """Return a SQLite in-memory engine with FK enforcement enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _enforce_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@pytest.fixture(scope="function")
def engine():
    """Fresh SQLite engine with schema for each test."""
    eng = make_sqlite_engine()
    init_database(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    """Session with auto-rollback for test isolation."""
    Session_ = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = Session_()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture(scope="function")
def session_manager(engine) -> DatabaseSessionManager:
    """DatabaseSessionManager backed by in-memory SQLite."""
    return DatabaseSessionManager(engine)


# ---------------------------------------------------------------------------
# Helper builders — use minimal required fields
# ---------------------------------------------------------------------------

def _project(key="TST", name="Test Project", desc="A test project") -> Project:
    return Project(
        key=key,
        name=name,
        description=desc,
        status=ProjectStatus.PLANNING,
        priority=Priority.HIGH,
    )


def _stakeholder(email="test@example.com", name="Test User", role="Lead") -> Stakeholder:
    return Stakeholder(
        name=name,
        email=email,
        role=role,
        is_approver=True,
    )


def _milestone(project_id: str) -> Milestone:
    return Milestone(
        project_id=project_id,
        title="M1 Delivery",
        target_date=date(2026, 12, 31),
        status=ItemStatus.TODO,
    )


def _requirement(project_id: str, code="REQ-001") -> Requirement:
    return Requirement(
        project_id=project_id,
        code=code,
        title="User Authentication",
        description="System must support SSO and MFA.",
        category="Functional",
        priority=Priority.HIGH,
    )


def _task(project_id: str, code="TASK-001") -> Task:
    return Task(
        project_id=project_id,
        code=code,
        title="Implement Login",
        description="Build OIDC login flow.",
        priority=Priority.HIGH,
        status=ItemStatus.TODO,
    )


def _approval(project_id: str, entity_id: str) -> ApprovalRequest:
    return ApprovalRequest(
        project_id=project_id,
        entity_type="Requirement",
        entity_id=entity_id,
        action_type="CREATE",
        requested_by="AI_AGENT",
        summary="Agent requests creation of new requirement.",
        proposed_diff={"code": "REQ-001", "title": "SSO requirement"},
        status=ApprovalStatus.PENDING,
    )


def _event(project_id: str) -> ProjectEvent:
    return ProjectEvent(
        project_id=project_id,
        event_type="REQUIREMENT_CREATED",
        actor_type="AGENT",
        actor_id="AI_AGENT",
        entity_type="Requirement",
        entity_id=str(uuid.uuid4()),
        summary="Requirement REQ-001 created by agent.",
        payload={"code": "REQ-001"},
    )


# ===========================================================================
# 1. Schema initialisation
# ===========================================================================

class TestDatabaseInit:
    def test_init_database_creates_all_tables(self, engine):
        """init_database must create all 17 expected tables."""
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {
            "projects", "stakeholders", "milestones", "requirements",
            "user_stories", "tasks", "dependencies", "risks", "blockers",
            "meetings", "action_items", "decisions", "scope_changes",
            "approval_requests", "project_events", "documents", "document_versions",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_seed_database_inserts_baseline_data(self, engine, session):
        """seed_database must insert seed project, stakeholder and milestone."""
        result = seed_database(session)
        assert "project_id" in result
        assert "stakeholder_id" in result
        assert "milestone_id" in result

        project = session.query(ProjectModel).filter_by(project_key="PRGMS").first()
        assert project is not None
        assert project.name == "ProgramSaathi Core Engine"

    def test_seed_database_idempotent(self, engine, session):
        """Calling seed_database twice must not raise or duplicate data."""
        seed_database(session)
        result2 = seed_database(session)
        assert "project_id" in result2
        count = session.query(ProjectModel).filter_by(project_key="PRGMS").count()
        assert count == 1


# ===========================================================================
# 2. Project Repository CRUD
# ===========================================================================

class TestSQLProjectRepository:
    def test_create_and_get_by_id(self, session):
        repo = SQLProjectRepository(session)
        proj = _project()
        created = repo.create(proj)
        session.commit()

        fetched = repo.get_by_id(proj.id)
        assert fetched is not None
        assert fetched.key == "TST"
        assert fetched.name == "Test Project"

    def test_get_by_key(self, session):
        repo = SQLProjectRepository(session)
        proj = _project(key="MYPRJ")
        repo.create(proj)
        session.commit()

        fetched = repo.get_by_key("MYPRJ")
        assert fetched is not None
        assert fetched.key == "MYPRJ"

    def test_get_by_key_case_insensitive(self, session):
        repo = SQLProjectRepository(session)
        proj = _project(key="UPPER")
        repo.create(proj)
        session.commit()

        fetched = repo.get_by_key("upper")
        assert fetched is not None

    def test_get_by_id_not_found_returns_none(self, session):
        repo = SQLProjectRepository(session)
        assert repo.get_by_id(str(uuid.uuid4())) is None

    def test_update_project(self, session):
        repo = SQLProjectRepository(session)
        proj = _project()
        repo.create(proj)
        session.commit()

        proj.name = "Updated Project Name"
        repo.update(proj)
        session.commit()

        fetched = repo.get_by_id(proj.id)
        assert fetched.name == "Updated Project Name"

    def test_delete_project(self, session):
        repo = SQLProjectRepository(session)
        proj = _project()
        repo.create(proj)
        session.commit()

        deleted = repo.delete(proj.id)
        session.commit()
        assert deleted is True
        assert repo.get_by_id(proj.id) is None

    def test_delete_nonexistent_returns_false(self, session):
        repo = SQLProjectRepository(session)
        assert repo.delete(str(uuid.uuid4())) is False

    def test_list_by_project_on_project_repo_returns_empty(self, session):
        """Project repo has no project_id column — list_by_project returns []."""
        repo = SQLProjectRepository(session)
        assert repo.list_by_project("any-id") == []


# ===========================================================================
# 3. Stakeholder Repository
# ===========================================================================

class TestSQLStakeholderRepository:
    def test_create_and_get_by_email(self, session):
        repo = SQLStakeholderRepository(session)
        sh = _stakeholder(email="alice@example.com")
        repo.create(sh)
        session.commit()

        found = repo.get_by_email("alice@example.com")
        assert found is not None
        assert found.name == "Test User"

    def test_get_by_email_not_found_returns_none(self, session):
        repo = SQLStakeholderRepository(session)
        assert repo.get_by_email("nobody@nowhere.com") is None


# ===========================================================================
# 4. Milestone Repository (with FK to project)
# ===========================================================================

class TestSQLMilestoneRepository:
    def _create_project(self, session) -> Project:
        repo = SQLProjectRepository(session)
        proj = _project()
        repo.create(proj)
        session.flush()
        return proj

    def test_create_milestone(self, session):
        proj = self._create_project(session)
        m_repo = SQLMilestoneRepository(session)
        ms = _milestone(proj.id)
        m_repo.create(ms)
        session.commit()

        fetched = m_repo.get_by_id(ms.id)
        assert fetched is not None
        assert fetched.project_id == proj.id

    def test_list_by_project(self, session):
        proj = self._create_project(session)
        m_repo = SQLMilestoneRepository(session)

        ms1 = _milestone(proj.id)
        ms2 = Milestone(
            project_id=proj.id,
            title="M2 Release",
            target_date=date(2027, 3, 31),
        )
        m_repo.create(ms1)
        m_repo.create(ms2)
        session.commit()

        items = m_repo.list_by_project(proj.id)
        assert len(items) == 2

    def test_milestone_cascade_delete_with_project(self, session):
        """Deleting a project should cascade-delete its milestones."""
        proj = self._create_project(session)
        m_repo = SQLMilestoneRepository(session)
        ms = _milestone(proj.id)
        m_repo.create(ms)
        session.commit()

        ms_id = ms.id
        proj_repo = SQLProjectRepository(session)
        proj_repo.delete(proj.id)
        session.commit()

        assert m_repo.get_by_id(ms_id) is None


# ===========================================================================
# 5. Requirement Repository
# ===========================================================================

class TestSQLRequirementRepository:
    def _project_in_db(self, session) -> Project:
        repo = SQLProjectRepository(session)
        p = _project()
        repo.create(p)
        session.flush()
        return p

    def test_create_and_list(self, session):
        p = self._project_in_db(session)
        r_repo = SQLRequirementRepository(session)
        req = _requirement(p.id)
        r_repo.create(req)
        session.commit()

        items = r_repo.list_by_project(p.id)
        assert len(items) == 1
        assert items[0].code == "REQ-001"

    def test_acceptance_criteria_roundtrip(self, session):
        """acceptance_criteria list must survive JSON serialization roundtrip."""
        p = self._project_in_db(session)
        r_repo = SQLRequirementRepository(session)
        req = _requirement(p.id)
        req.acceptance_criteria = ["Must support SSO", "Must support MFA"]
        r_repo.create(req)
        session.commit()

        fetched = r_repo.get_by_id(req.id)
        assert isinstance(fetched.acceptance_criteria, list)
        assert "Must support SSO" in fetched.acceptance_criteria


# ===========================================================================
# 6. Task Repository
# ===========================================================================

class TestSQLTaskRepository:
    def _project_in_db(self, session) -> Project:
        repo = SQLProjectRepository(session)
        p = _project()
        repo.create(p)
        session.flush()
        return p

    def test_create_and_update_task(self, session):
        p = self._project_in_db(session)
        t_repo = SQLTaskRepository(session)
        task = _task(p.id)
        t_repo.create(task)
        session.commit()

        task.status = ItemStatus.IN_PROGRESS
        t_repo.update(task)
        session.commit()

        fetched = t_repo.get_by_id(task.id)
        assert fetched.status == ItemStatus.IN_PROGRESS

    def test_list_tasks_by_project(self, session):
        p = self._project_in_db(session)
        t_repo = SQLTaskRepository(session)
        t_repo.create(_task(p.id, "TASK-001"))
        t_repo.create(_task(p.id, "TASK-002"))
        session.commit()

        items = t_repo.list_by_project(p.id)
        assert len(items) == 2


# ===========================================================================
# 7. Approval Request Repository (human-in-the-loop)
# ===========================================================================

class TestSQLApprovalRequestRepository:
    def _project_in_db(self, session) -> Project:
        repo = SQLProjectRepository(session)
        p = _project()
        repo.create(p)
        session.flush()
        return p

    def test_create_pending_approval(self, session):
        p = self._project_in_db(session)
        a_repo = SQLApprovalRequestRepository(session)
        entity_id = str(uuid.uuid4())
        ar = _approval(p.id, entity_id)
        a_repo.create(ar)
        session.commit()

        fetched = a_repo.get_by_id(ar.id)
        assert fetched is not None
        assert fetched.status == ApprovalStatus.PENDING

    def test_list_pending_approvals(self, session):
        p = self._project_in_db(session)
        a_repo = SQLApprovalRequestRepository(session)

        # Create two pending
        ar1 = _approval(p.id, str(uuid.uuid4()))
        ar2 = _approval(p.id, str(uuid.uuid4()))
        a_repo.create(ar1)
        a_repo.create(ar2)
        session.commit()

        pending = a_repo.list_pending(p.id)
        assert len(pending) == 2

    def test_approved_approval_not_in_pending(self, session):
        p = self._project_in_db(session)
        a_repo = SQLApprovalRequestRepository(session)

        ar = _approval(p.id, str(uuid.uuid4()))
        a_repo.create(ar)
        session.commit()

        # Approve it
        ar.status = ApprovalStatus.APPROVED
        a_repo.update(ar)
        session.commit()

        pending = a_repo.list_pending(p.id)
        assert len(pending) == 0

    def test_proposed_diff_roundtrip(self, session):
        """proposed_diff dict must survive JSON serialization roundtrip."""
        p = self._project_in_db(session)
        a_repo = SQLApprovalRequestRepository(session)
        entity_id = str(uuid.uuid4())
        ar = _approval(p.id, entity_id)
        a_repo.create(ar)
        session.commit()

        fetched = a_repo.get_by_id(ar.id)
        assert isinstance(fetched.proposed_diff, dict)
        assert fetched.proposed_diff["code"] == "REQ-001"


# ===========================================================================
# 8. Project Event (audit log)
# ===========================================================================

class TestSQLProjectEventRepository:
    def _project_in_db(self, session) -> Project:
        repo = SQLProjectRepository(session)
        p = _project()
        repo.create(p)
        session.flush()
        return p

    def test_create_audit_event(self, session):
        p = self._project_in_db(session)
        e_repo = SQLProjectEventRepository(session)
        ev = _event(p.id)
        e_repo.create(ev)
        session.commit()

        items = e_repo.list_by_project(p.id)
        assert len(items) == 1
        assert items[0].event_type == "REQUIREMENT_CREATED"

    def test_payload_roundtrip(self, session):
        p = self._project_in_db(session)
        e_repo = SQLProjectEventRepository(session)
        ev = _event(p.id)
        ev.payload = {"before": {"status": "TODO"}, "after": {"status": "DONE"}}
        e_repo.create(ev)
        session.commit()

        fetched = e_repo.get_by_id(ev.id)
        assert isinstance(fetched.payload, dict)
        assert fetched.payload["before"]["status"] == "TODO"


# ===========================================================================
# 9. Transaction rollback
# ===========================================================================

class TestTransactionRollback:
    def test_rollback_on_session_manager_exception(self, session_manager):
        """Session manager must roll back and not persist data on exception."""
        project_id = None

        with pytest.raises(RuntimeError):
            with session_manager.session() as sess:
                proj = _project(key="ROLL")
                p_repo = SQLProjectRepository(sess)
                p_repo.create(proj)
                project_id = proj.id
                sess.flush()
                raise RuntimeError("Simulated failure — rollback required")

        # Open a fresh session and confirm nothing was saved
        with session_manager.session() as check_sess:
            r = SQLProjectRepository(check_sess)
            assert r.get_by_id(project_id) is None

    def test_successful_transaction_is_committed(self, session_manager):
        """Session manager commits data when no exception occurs."""
        proj = _project(key="COMMT")
        proj_id = proj.id

        with session_manager.session() as sess:
            SQLProjectRepository(sess).create(proj)

        with session_manager.session() as check_sess:
            fetched = SQLProjectRepository(check_sess).get_by_id(proj_id)
            assert fetched is not None
            assert fetched.key == "COMMT"


# ===========================================================================
# 10. Foreign-key enforcement
# ===========================================================================

class TestForeignKeyConstraints:
    def test_milestone_invalid_project_fk_raises(self, session):
        """Creating a milestone referencing a non-existent project must fail."""
        bad_project_id = str(uuid.uuid4())
        m_row = MilestoneModel(
            id=str(uuid.uuid4()),
            project_id=bad_project_id,
            title="Orphan Milestone",
            target_date=date(2027, 1, 1),
            status="TODO",
        )
        session.add(m_row)
        with pytest.raises(Exception):  # IntegrityError for FK violation
            session.flush()

    def test_delete_project_cascades_to_milestones(self, engine):
        """Deleting project row must remove its milestones (CASCADE)."""
        sm = DatabaseSessionManager(engine)
        proj = _project(key="CASC")
        with sm.session() as sess:
            p_repo = SQLProjectRepository(sess)
            p_repo.create(proj)
            m_repo = SQLMilestoneRepository(sess)
            ms = _milestone(proj.id)
            m_repo.create(ms)
        ms_id = ms.id

        with sm.session() as sess:
            SQLProjectRepository(sess).delete(proj.id)

        with sm.session() as sess:
            assert SQLMilestoneRepository(sess).get_by_id(ms_id) is None


# ===========================================================================
# 11. AzureSQLService behaviour when unconfigured
# ===========================================================================

class TestAzureSQLServiceUnconfigured:
    def test_is_healthy_returns_false_when_unconfigured(self):
        """AzureSQLService with no config must report unhealthy, not raise."""
        from programsaathi.config import Settings
        settings = Settings(
            azure_sql_server=None,
            azure_sql_database=None,
        )
        svc = AzureSQLService(settings=settings)
        assert svc.is_healthy() is False

    def test_is_available_returns_false_when_unconfigured(self):
        from programsaathi.config import Settings
        settings = Settings(azure_sql_server=None, azure_sql_database=None)
        svc = AzureSQLService(settings=settings)
        assert svc.is_available() is False

    def test_execute_query_raises_when_unconfigured(self):
        from programsaathi.config import Settings
        settings = Settings(azure_sql_server=None, azure_sql_database=None)
        svc = AzureSQLService(settings=settings)
        with pytest.raises(DatabaseServiceError):
            svc.execute_query("SELECT 1")

    def test_execute_statement_raises_when_unconfigured(self):
        from programsaathi.config import Settings
        settings = Settings(azure_sql_server=None, azure_sql_database=None)
        svc = AzureSQLService(settings=settings)
        with pytest.raises(DatabaseServiceError):
            svc.execute_statement("UPDATE projects SET name='x' WHERE 1=0")

    def test_azure_sql_service_with_injected_sqlite_engine(self, engine):
        """AzureSQLService with injected SQLite engine must be healthy."""
        svc = AzureSQLService(engine=engine)
        assert svc.is_healthy() is True

    def test_execute_query_via_injected_engine(self, engine):
        svc = AzureSQLService(engine=engine)
        result = svc.execute_query("SELECT 1 AS value")
        assert isinstance(result, list)


# ===========================================================================
# 12. MockDatabaseService
# ===========================================================================

class TestMockDatabaseService:
    def test_mock_is_healthy(self):
        svc = MockDatabaseService()
        assert svc.is_healthy() is True

    def test_mock_logs_queries(self):
        svc = MockDatabaseService()
        svc.execute_query("SELECT * FROM projects", ())
        svc.execute_query("SELECT * FROM milestones", ())
        assert len(svc.query_log) == 2

    def test_mock_logs_statements(self):
        svc = MockDatabaseService()
        rowcount = svc.execute_statement("UPDATE projects SET name='x' WHERE id=?", ("123",))
        assert rowcount == 1
        assert len(svc.query_log) == 1


# ===========================================================================
# 13. create_db_engine fallback to SQLite
# ===========================================================================

class TestCreateDbEngine:
    def test_create_db_engine_fallback_sqlite(self):
        """Without Azure SQL config, engine must fall back to SQLite in-memory."""
        from programsaathi.config import Settings
        settings = Settings(azure_sql_server=None, azure_sql_database=None)
        eng = create_db_engine(settings=settings, echo=False)
        assert "sqlite" in str(eng.url)
        eng.dispose()

    def test_create_db_engine_custom_url(self):
        eng = create_db_engine(custom_url="sqlite:///:memory:", echo=False)
        assert "sqlite" in str(eng.url)
        eng.dispose()
