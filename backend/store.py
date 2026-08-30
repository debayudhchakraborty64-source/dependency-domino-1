"""
Dependency Domino - In-Memory Store
Simple in-memory data store for repositories, components, and analysis results.
For production, this would be replaced by a real database (SQLite/PostgreSQL).
"""
from typing import Dict, List, Optional
from models import Repository, Component, Dependency, ImpactAnalysis, Report


class Store:
    """Thread-safe in-memory store. Initialized once per process."""

    def __init__(self):
        self.repositories: Dict[str, Repository] = {}
        self.components: Dict[str, Component] = {}          # id -> Component
        self.repo_components: Dict[str, List[str]] = {}     # repo_id -> [component_id]
        self.dependencies: Dict[str, List[Dependency]] = {} # repo_id -> [Dependency]
        self.impact_cache: Dict[str, ImpactAnalysis] = {}   # component_id -> ImpactAnalysis
        self.reports: Dict[str, Report] = {}

    # ── Repositories ──────────────────────────────────────────────────────────

    def save_repository(self, repo: Repository) -> Repository:
        self.repositories[repo.id] = repo
        if repo.id not in self.repo_components:
            self.repo_components[repo.id] = []
        return repo

    def get_repository(self, repo_id: str) -> Optional[Repository]:
        return self.repositories.get(repo_id)

    def list_repositories(self) -> List[Repository]:
        return list(self.repositories.values())

    # ── Components ────────────────────────────────────────────────────────────

    def save_component(self, component: Component) -> Component:
        self.components[component.id] = component
        rid = component.repository_id
        if rid not in self.repo_components:
            self.repo_components[rid] = []
        if component.id not in self.repo_components[rid]:
            self.repo_components[rid].append(component.id)
        return component

    def get_component(self, component_id: str) -> Optional[Component]:
        return self.components.get(component_id)

    def get_components_for_repo(self, repo_id: str) -> List[Component]:
        ids = self.repo_components.get(repo_id, [])
        return [self.components[i] for i in ids if i in self.components]

    def clear_repo_components(self, repo_id: str):
        ids = self.repo_components.get(repo_id, [])
        for cid in ids:
            self.components.pop(cid, None)
            self.impact_cache.pop(cid, None)
        self.repo_components[repo_id] = []

    # ── Dependencies ──────────────────────────────────────────────────────────

    def save_dependencies(self, repo_id: str, deps: List[Dependency]):
        self.dependencies[repo_id] = deps

    def get_dependencies(self, repo_id: str) -> List[Dependency]:
        return self.dependencies.get(repo_id, [])

    # ── Impact cache ──────────────────────────────────────────────────────────

    def save_impact(self, impact: ImpactAnalysis):
        self.impact_cache[impact.component_id] = impact

    def get_impact(self, component_id: str) -> Optional[ImpactAnalysis]:
        return self.impact_cache.get(component_id)

    # ── Reports ───────────────────────────────────────────────────────────────

    def save_report(self, report: Report) -> Report:
        self.reports[report.id] = report
        return report

    def get_report(self, report_id: str) -> Optional[Report]:
        return self.reports.get(report_id)

    def list_reports(self) -> List[Report]:
        return list(self.reports.values())


# Singleton store instance
store = Store()
