"""Behave environment configuration and hooks.

This module contains hooks that run before and after various stages of
the BDD test execution lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from behave.runner import Context


def before_all(context: Context) -> None:
    """Run before all tests.

    Args:
        context: The behave context object.
    """
    # Add any global setup here
    context.config.setup_logging()


def before_feature(context: Context, feature: object) -> None:
    """Run before each feature.

    Args:
        context: The behave context object.
        feature: The feature being executed.
    """
    pass


def before_scenario(context: Context, scenario: object) -> None:
    """Run before each scenario.

    Args:
        context: The behave context object.
        scenario: The scenario being executed.
    """
    pass


def after_scenario(context: Context, scenario: object) -> None:
    """Run after each scenario.

    Args:
        context: The behave context object.
        scenario: The scenario that was executed.
    """
    pass


def after_feature(context: Context, feature: object) -> None:
    """Run after each feature.

    Args:
        context: The behave context object.
        feature: The feature that was executed.
    """
    pass


def after_all(context: Context) -> None:
    """Run after all tests.

    Args:
        context: The behave context object.
    """
    pass
