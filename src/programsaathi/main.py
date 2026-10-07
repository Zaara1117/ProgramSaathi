"""Main entry point for ProgramSaathi."""

import sys
from programsaathi.config import get_settings
from programsaathi.logging import configure_logging, get_logger
from programsaathi.orchestrator.orchestrator import ProgramSaathiOrchestrator
from programsaathi.tools.registry import ToolRegistry
from programsaathi.tools.read_only import GetProjectOverviewTool
from programsaathi.repositories.project import InMemoryProjectRepository
from programsaathi.models.project import Project, ProjectStatus, Priority

logger = get_logger(__name__)


def create_app() -> ProgramSaathiOrchestrator:
    """Bootstraps configuration, repositories, tools, and the orchestrator."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    logger.info("Initializing ProgramSaathi application bootstrap...")

    # Wire repositories
    project_repo = InMemoryProjectRepository()

    # Seed sample project for exploration
    sample_proj = Project(
        key="PS01",
        name="Enterprise Cloud Migration",
        description="Core program to migrate on-premises workloads to Microsoft Azure.",
        status=ProjectStatus.PLANNING,
        priority=Priority.HIGH,
    )
    project_repo.create(sample_proj)

    # Wire tool registry
    registry = ToolRegistry()
    registry.register(GetProjectOverviewTool(project_repo=project_repo))

    # Initialize orchestrator
    orchestrator = ProgramSaathiOrchestrator(
        settings=settings,
        tool_registry=registry,
    )

    logger.info(f"ProgramSaathi ready. Sample project registered: {sample_proj.key} (ID: {sample_proj.id})")
    return orchestrator


def main() -> int:
    """Command-line runner."""
    orchestrator = create_app()
    tools = orchestrator.tool_registry.list_tools()
    print("=" * 70)
    print("ProgramSaathi — AI Program & Project Management Agent (Phase 1)")
    print("=" * 70)
    print(f"Environment:       {orchestrator.settings.environment}")
    print(f"Foundry Model:     {orchestrator.settings.foundry_model}")
    print(f"Registered Tools:  {len(tools)} {[t.name for t in tools]}")
    print("Architecture:      Orchestrator -> Capability Modules -> Authoritative SQL")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
