"""
Dependency Domino - Demo Repository Data

A realistic "Developer Portal" application used for hackathon demos.
This dataset works without external credentials.

Structure mimics a real monorepo:
  frontend/ - React frontend
  backend/  - Python FastAPI backend
  shared/   - Shared utilities
  tests/    - Test suite
"""
from models import (
    Component, ComponentMetadata, Dependency,
    Language, NodeType, RiskLevel,
    RelationshipType, DependencyType
)
import uuid

DEMO_REPO_ID = "demo-developer-portal"
DEMO_REPO_NAME = "Developer Portal"


def _comp(
    path: str,
    lang: Language,
    node_type: NodeType,
    lines: int,
    functions: list,
    imports: list,
    exports: list,
    is_test: bool = False,
) -> Component:
    return Component(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo:{path}")),
        repository_id=DEMO_REPO_ID,
        name=path.split("/")[-1],
        path=path,
        type=node_type,
        language=lang,
        metadata=ComponentMetadata(
            lines=lines,
            functions=functions,
            imports=imports,
            exports=exports,
            is_test=is_test,
        ),
        risk=RiskLevel.UNKNOWN,
        risk_score=0.0,
    )


# ─── Define all demo components ───────────────────────────────────────────────

DEMO_COMPONENTS = [
    # ── Frontend: Core ────────────────────────────────────────────────────────
    _comp("frontend/src/index.jsx", Language.JSX, NodeType.FILE, 32, ["renderApp"], ["./App", "react-dom"], ["renderApp"]),
    _comp("frontend/src/App.jsx", Language.JSX, NodeType.FILE, 85, ["App", "Router"], ["./components/Layout", "./routes/AppRouter", "./contexts/AuthContext"], ["App"]),
    _comp("frontend/src/routes/AppRouter.jsx", Language.JSX, NodeType.FILE, 64, ["AppRouter"], ["../components/pages/Dashboard", "../components/pages/Login", "../components/pages/Profile", "../components/pages/NotFound"], ["AppRouter"]),

    # ── Frontend: Components ──────────────────────────────────────────────────
    _comp("frontend/src/components/Layout.jsx", Language.JSX, NodeType.FILE, 72, ["Layout", "Sidebar", "Header"], ["./Sidebar", "./Header", "../contexts/AuthContext"], ["Layout"]),
    _comp("frontend/src/components/Sidebar.jsx", Language.JSX, NodeType.FILE, 58, ["Sidebar"], ["../contexts/AuthContext", "../hooks/useNavigation"], ["Sidebar"]),
    _comp("frontend/src/components/Header.jsx", Language.JSX, NodeType.FILE, 45, ["Header"], ["../contexts/AuthContext", "../hooks/useUser"], ["Header"]),

    # ── Frontend: Pages ───────────────────────────────────────────────────────
    _comp("frontend/src/components/pages/Login.jsx", Language.JSX, NodeType.FILE, 112, ["Login", "LoginForm", "handleSubmit"], ["../../services/authService", "../../utils/validation", "../../contexts/AuthContext"], ["Login"]),
    _comp("frontend/src/components/pages/Dashboard.jsx", Language.JSX, NodeType.FILE, 148, ["Dashboard", "StatsCard", "RecentActivity"], ["../../services/apiService", "../../services/userService", "../../hooks/useData"], ["Dashboard"]),
    _comp("frontend/src/components/pages/Profile.jsx", Language.JSX, NodeType.FILE, 96, ["Profile", "ProfileForm", "handleUpdate"], ["../../services/userService", "../../services/apiService", "../../utils/validation"], ["Profile"]),
    _comp("frontend/src/components/pages/NotFound.jsx", Language.JSX, NodeType.FILE, 22, ["NotFound"], [], ["NotFound"]),

    # ── Frontend: Services ────────────────────────────────────────────────────
    _comp("frontend/src/services/authService.js", Language.JAVASCRIPT, NodeType.SERVICE, 134, ["login", "logout", "refreshToken", "validateToken", "getAuthHeaders"], ["./apiService", "../utils/tokenStorage", "../utils/validation"], ["login", "logout", "refreshToken", "validateToken"]),
    _comp("frontend/src/services/apiService.js", Language.JAVASCRIPT, NodeType.SERVICE, 98, ["get", "post", "put", "delete", "handleError"], ["../utils/tokenStorage", "../config/apiConfig"], ["get", "post", "put", "delete"]),
    _comp("frontend/src/services/userService.js", Language.JAVASCRIPT, NodeType.SERVICE, 76, ["getUser", "updateUser", "deleteUser"], ["./apiService", "../utils/validation"], ["getUser", "updateUser", "deleteUser"]),
    _comp("frontend/src/services/dashboardService.js", Language.JAVASCRIPT, NodeType.SERVICE, 52, ["getStats", "getActivity"], ["./apiService"], ["getStats", "getActivity"]),

    # ── Frontend: Contexts ────────────────────────────────────────────────────
    _comp("frontend/src/contexts/AuthContext.jsx", Language.JSX, NodeType.FILE, 88, ["AuthProvider", "useAuth"], ["../services/authService"], ["AuthProvider", "useAuth"]),

    # ── Frontend: Hooks ───────────────────────────────────────────────────────
    _comp("frontend/src/hooks/useUser.js", Language.JAVASCRIPT, NodeType.FILE, 34, ["useUser"], ["../services/userService", "../contexts/AuthContext"], ["useUser"]),
    _comp("frontend/src/hooks/useNavigation.js", Language.JAVASCRIPT, NodeType.FILE, 28, ["useNavigation"], [], ["useNavigation"]),
    _comp("frontend/src/hooks/useData.js", Language.JAVASCRIPT, NodeType.FILE, 42, ["useData"], ["../services/apiService"], ["useData"]),

    # ── Frontend: Utils ───────────────────────────────────────────────────────
    _comp("frontend/src/utils/validation.js", Language.JAVASCRIPT, NodeType.FILE, 68, ["validateEmail", "validatePassword", "validateForm", "sanitizeInput"], [], ["validateEmail", "validatePassword", "validateForm", "sanitizeInput"]),
    _comp("frontend/src/utils/tokenStorage.js", Language.JAVASCRIPT, NodeType.FILE, 44, ["getToken", "setToken", "removeToken"], [], ["getToken", "setToken", "removeToken"]),

    # ── Frontend: Config ──────────────────────────────────────────────────────
    _comp("frontend/src/config/apiConfig.js", Language.JAVASCRIPT, NodeType.FILE, 18, [], [], ["API_BASE_URL", "API_TIMEOUT"]),

    # ── Backend: Main ─────────────────────────────────────────────────────────
    _comp("backend/main.py", Language.PYTHON, NodeType.API, 62, ["create_app", "startup"], ["fastapi", "backend.routers.auth", "backend.routers.users", "backend.routers.dashboard", "backend.middleware.auth"], ["app"]),
    _comp("backend/routers/auth.py", Language.PYTHON, NodeType.API, 118, ["login", "logout", "refresh_token", "me"], ["fastapi", "backend.services.auth_service", "backend.models.user", "backend.utils.security"], ["router"]),
    _comp("backend/routers/users.py", Language.PYTHON, NodeType.API, 96, ["get_user", "update_user", "delete_user", "list_users"], ["fastapi", "backend.services.user_service", "backend.models.user", "backend.utils.security"], ["router"]),
    _comp("backend/routers/dashboard.py", Language.PYTHON, NodeType.API, 72, ["get_stats", "get_activity"], ["fastapi", "backend.services.dashboard_service", "backend.utils.security"], ["router"]),

    # ── Backend: Services ─────────────────────────────────────────────────────
    _comp("backend/services/auth_service.py", Language.PYTHON, NodeType.SERVICE, 156, ["authenticate_user", "create_access_token", "validate_token", "revoke_token"], ["backend.database.db", "backend.models.user", "backend.utils.security", "backend.utils.password"], ["authenticate_user", "create_access_token", "validate_token"]),
    _comp("backend/services/user_service.py", Language.PYTHON, NodeType.SERVICE, 104, ["get_user_by_id", "update_user", "delete_user", "list_users"], ["backend.database.db", "backend.models.user"], ["get_user_by_id", "update_user", "delete_user"]),
    _comp("backend/services/dashboard_service.py", Language.PYTHON, NodeType.SERVICE, 78, ["get_stats", "get_recent_activity"], ["backend.database.db", "backend.models.user"], ["get_stats", "get_recent_activity"]),

    # ── Backend: Models ───────────────────────────────────────────────────────
    _comp("backend/models/user.py", Language.PYTHON, NodeType.FILE, 48, ["User", "UserCreate", "UserUpdate", "UserResponse"], ["pydantic"], ["User", "UserCreate", "UserUpdate"]),

    # ── Backend: Utils ────────────────────────────────────────────────────────
    _comp("backend/utils/security.py", Language.PYTHON, NodeType.FILE, 82, ["get_current_user", "require_auth", "create_jwt", "decode_jwt"], ["fastapi", "jose", "backend.models.user"], ["get_current_user", "require_auth", "create_jwt"]),
    _comp("backend/utils/password.py", Language.PYTHON, NodeType.FILE, 32, ["hash_password", "verify_password"], ["passlib"], ["hash_password", "verify_password"]),

    # ── Backend: Database ─────────────────────────────────────────────────────
    _comp("backend/database/db.py", Language.PYTHON, NodeType.FILE, 56, ["get_db", "init_db", "close_db"], ["sqlalchemy"], ["get_db", "init_db"]),

    # ── Backend: Middleware ───────────────────────────────────────────────────
    _comp("backend/middleware/auth.py", Language.PYTHON, NodeType.FILE, 44, ["AuthMiddleware"], ["fastapi", "backend.utils.security"], ["AuthMiddleware"]),

    # ── Shared ────────────────────────────────────────────────────────────────
    _comp("shared/constants.js", Language.JAVASCRIPT, NodeType.FILE, 24, [], [], ["ROLES", "STATUS_CODES", "EVENT_TYPES"]),
    _comp("shared/types.ts", Language.TYPESCRIPT, NodeType.FILE, 66, [], [], ["User", "AuthToken", "DashboardStats"]),

    # ── Tests: Frontend ───────────────────────────────────────────────────────
    _comp("tests/frontend/auth.test.js", Language.JAVASCRIPT, NodeType.TEST, 88, ["describe", "it"], ["../../frontend/src/services/authService", "../../frontend/src/utils/validation"], [], True),
    _comp("tests/frontend/login.test.jsx", Language.JSX, NodeType.TEST, 72, ["describe", "it"], ["../../frontend/src/components/pages/Login", "../../frontend/src/services/authService"], [], True),
    _comp("tests/frontend/profile.test.jsx", Language.JSX, NodeType.TEST, 64, ["describe", "it"], ["../../frontend/src/components/pages/Profile", "../../frontend/src/services/userService"], [], True),
    _comp("tests/frontend/dashboard.test.jsx", Language.JSX, NodeType.TEST, 56, ["describe", "it"], ["../../frontend/src/components/pages/Dashboard", "../../frontend/src/services/dashboardService"], [], True),
    _comp("tests/frontend/validation.test.js", Language.JAVASCRIPT, NodeType.TEST, 44, ["describe", "it"], ["../../frontend/src/utils/validation"], [], True),

    # ── Tests: Backend ────────────────────────────────────────────────────────
    _comp("tests/backend/test_auth.py", Language.PYTHON, NodeType.TEST, 112, ["test_login", "test_logout", "test_refresh", "test_invalid_token"], ["backend.services.auth_service", "backend.utils.security"], [], True),
    _comp("tests/backend/test_users.py", Language.PYTHON, NodeType.TEST, 88, ["test_get_user", "test_update_user", "test_delete_user"], ["backend.services.user_service", "backend.models.user"], [], True),
    _comp("tests/backend/test_dashboard.py", Language.PYTHON, NodeType.TEST, 52, ["test_get_stats"], ["backend.services.dashboard_service"], [], True),
]

# ─── Build component lookup map ───────────────────────────────────────────────
DEMO_PATH_MAP = {c.path: c for c in DEMO_COMPONENTS}
DEMO_ID_MAP = {c.id: c for c in DEMO_COMPONENTS}


def _dep(source_path: str, target_path: str, rel: RelationshipType = RelationshipType.IMPORT, conf: float = 0.95) -> Dependency:
    src = DEMO_PATH_MAP.get(source_path)
    tgt = DEMO_PATH_MAP.get(target_path)
    if not src or not tgt:
        return None
    return Dependency(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo:{source_path}->{target_path}")),
        source=src.id,
        target=tgt.id,
        source_path=source_path,
        target_path=target_path,
        relationship=rel,
        dependency_type=DependencyType.DIRECT,
        confidence=conf,
        raw_import=target_path,
    )


# ─── Define all demo dependencies ─────────────────────────────────────────────

_raw_deps = [
    # App structure
    ("frontend/src/index.jsx", "frontend/src/App.jsx"),
    ("frontend/src/App.jsx", "frontend/src/components/Layout.jsx"),
    ("frontend/src/App.jsx", "frontend/src/routes/AppRouter.jsx"),
    ("frontend/src/App.jsx", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/routes/AppRouter.jsx", "frontend/src/components/pages/Dashboard.jsx"),
    ("frontend/src/routes/AppRouter.jsx", "frontend/src/components/pages/Login.jsx"),
    ("frontend/src/routes/AppRouter.jsx", "frontend/src/components/pages/Profile.jsx"),
    ("frontend/src/routes/AppRouter.jsx", "frontend/src/components/pages/NotFound.jsx"),

    # Layout
    ("frontend/src/components/Layout.jsx", "frontend/src/components/Sidebar.jsx"),
    ("frontend/src/components/Layout.jsx", "frontend/src/components/Header.jsx"),
    ("frontend/src/components/Layout.jsx", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/components/Sidebar.jsx", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/components/Sidebar.jsx", "frontend/src/hooks/useNavigation.js"),
    ("frontend/src/components/Header.jsx", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/components/Header.jsx", "frontend/src/hooks/useUser.js"),

    # Pages → services
    ("frontend/src/components/pages/Login.jsx", "frontend/src/services/authService.js"),
    ("frontend/src/components/pages/Login.jsx", "frontend/src/utils/validation.js"),
    ("frontend/src/components/pages/Login.jsx", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/components/pages/Dashboard.jsx", "frontend/src/services/apiService.js"),
    ("frontend/src/components/pages/Dashboard.jsx", "frontend/src/services/userService.js"),
    ("frontend/src/components/pages/Dashboard.jsx", "frontend/src/hooks/useData.js"),
    ("frontend/src/components/pages/Profile.jsx", "frontend/src/services/userService.js"),
    ("frontend/src/components/pages/Profile.jsx", "frontend/src/services/apiService.js"),
    ("frontend/src/components/pages/Profile.jsx", "frontend/src/utils/validation.js"),

    # Services → services/utils
    ("frontend/src/services/authService.js", "frontend/src/services/apiService.js"),
    ("frontend/src/services/authService.js", "frontend/src/utils/tokenStorage.js"),
    ("frontend/src/services/authService.js", "frontend/src/utils/validation.js"),
    ("frontend/src/services/apiService.js", "frontend/src/utils/tokenStorage.js"),
    ("frontend/src/services/apiService.js", "frontend/src/config/apiConfig.js"),
    ("frontend/src/services/userService.js", "frontend/src/services/apiService.js"),
    ("frontend/src/services/userService.js", "frontend/src/utils/validation.js"),
    ("frontend/src/services/dashboardService.js", "frontend/src/services/apiService.js"),

    # Auth context
    ("frontend/src/contexts/AuthContext.jsx", "frontend/src/services/authService.js"),

    # Hooks
    ("frontend/src/hooks/useUser.js", "frontend/src/services/userService.js"),
    ("frontend/src/hooks/useUser.js", "frontend/src/contexts/AuthContext.jsx"),
    ("frontend/src/hooks/useData.js", "frontend/src/services/apiService.js"),

    # Backend: main → routers
    ("backend/main.py", "backend/routers/auth.py"),
    ("backend/main.py", "backend/routers/users.py"),
    ("backend/main.py", "backend/routers/dashboard.py"),
    ("backend/main.py", "backend/middleware/auth.py"),

    # Backend: routers → services
    ("backend/routers/auth.py", "backend/services/auth_service.py"),
    ("backend/routers/auth.py", "backend/models/user.py"),
    ("backend/routers/auth.py", "backend/utils/security.py"),
    ("backend/routers/users.py", "backend/services/user_service.py"),
    ("backend/routers/users.py", "backend/models/user.py"),
    ("backend/routers/users.py", "backend/utils/security.py"),
    ("backend/routers/dashboard.py", "backend/services/dashboard_service.py"),
    ("backend/routers/dashboard.py", "backend/utils/security.py"),

    # Backend: services → db/utils
    ("backend/services/auth_service.py", "backend/database/db.py"),
    ("backend/services/auth_service.py", "backend/models/user.py"),
    ("backend/services/auth_service.py", "backend/utils/security.py"),
    ("backend/services/auth_service.py", "backend/utils/password.py"),
    ("backend/services/user_service.py", "backend/database/db.py"),
    ("backend/services/user_service.py", "backend/models/user.py"),
    ("backend/services/dashboard_service.py", "backend/database/db.py"),
    ("backend/services/dashboard_service.py", "backend/models/user.py"),

    # Backend: utils
    ("backend/utils/security.py", "backend/models/user.py"),
    ("backend/middleware/auth.py", "backend/utils/security.py"),

    # Tests
    ("tests/frontend/auth.test.js", "frontend/src/services/authService.js"),
    ("tests/frontend/auth.test.js", "frontend/src/utils/validation.js"),
    ("tests/frontend/login.test.jsx", "frontend/src/components/pages/Login.jsx"),
    ("tests/frontend/login.test.jsx", "frontend/src/services/authService.js"),
    ("tests/frontend/profile.test.jsx", "frontend/src/components/pages/Profile.jsx"),
    ("tests/frontend/profile.test.jsx", "frontend/src/services/userService.js"),
    ("tests/frontend/dashboard.test.jsx", "frontend/src/components/pages/Dashboard.jsx"),
    ("tests/frontend/dashboard.test.jsx", "frontend/src/services/dashboardService.js"),
    ("tests/frontend/validation.test.js", "frontend/src/utils/validation.js"),
    ("tests/backend/test_auth.py", "backend/services/auth_service.py"),
    ("tests/backend/test_auth.py", "backend/utils/security.py"),
    ("tests/backend/test_users.py", "backend/services/user_service.py"),
    ("tests/backend/test_users.py", "backend/models/user.py"),
    ("tests/backend/test_dashboard.py", "backend/services/dashboard_service.py"),
]

DEMO_DEPENDENCIES = [d for d in [_dep(s, t) for s, t in _raw_deps] if d is not None]
