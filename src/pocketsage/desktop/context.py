"""Application context for dependency injection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

import flet as ft
from sqlmodel import Session

from ..config import BaseConfig
from ..infra.database import create_db_engine, create_session_factory, init_database
from ..infra.repositories import (
    SQLModelAccountRepository,
    SQLModelBudgetRepository,
    SQLModelCategoryRepository,
    SQLModelHabitRepository,
    SQLModelHoldingRepository,
    SQLModelLiabilityRepository,
    SQLModelTransactionRepository,
)
from ..models.user import User


@dataclass
class AppContext:
    """Centralized application context with services and state."""

    # Configuration
    config: BaseConfig

    # Session factory
    session_factory: Callable[[], Session]

    # Repositories
    transaction_repo: SQLModelTransactionRepository
    account_repo: SQLModelAccountRepository
    category_repo: SQLModelCategoryRepository
    budget_repo: SQLModelBudgetRepository
    habit_repo: SQLModelHabitRepository
    liability_repo: SQLModelLiabilityRepository
    holding_repo: SQLModelHoldingRepository

    # UI State
    theme_mode: ft.ThemeMode
    current_account_id: Optional[int]
    current_month: date

    # Page reference (set after initialization)
    page: Optional[ft.Page] = None
    file_picker: Optional[ft.FilePicker] = None
    file_picker_mode: Optional[str] = None

    current_user: Optional[User] = None

    def require_user_id(self) -> int:
        """Return the current user id or raise if not set."""

        if self.current_user is None or self.current_user.id is None:
            raise RuntimeError("User is not authenticated")
        return self.current_user.id


def create_app_context(config: Optional[BaseConfig] = None) -> AppContext:
    """Create and initialize the application context."""

    if config is None:
        config = BaseConfig()

    # Create database engine
    engine = create_db_engine(config)

    # Initialize schema
    init_database(engine)

    # Create session factory
    session_factory = create_session_factory(engine)

    # Initialize repositories
    transaction_repo = SQLModelTransactionRepository(session_factory)
    account_repo = SQLModelAccountRepository(session_factory)
    category_repo = SQLModelCategoryRepository(session_factory)
    budget_repo = SQLModelBudgetRepository(session_factory)
    habit_repo = SQLModelHabitRepository(session_factory)
    liability_repo = SQLModelLiabilityRepository(session_factory)
    holding_repo = SQLModelHoldingRepository(session_factory)

    # Initialize UI state
    current_date = date.today()

    return AppContext(
        config=config,
        session_factory=session_factory,
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        category_repo=category_repo,
        budget_repo=budget_repo,
        habit_repo=habit_repo,
        liability_repo=liability_repo,
        holding_repo=holding_repo,
        theme_mode=ft.ThemeMode.DARK,
        current_account_id=None,
        current_month=current_date.replace(day=1),
    )
