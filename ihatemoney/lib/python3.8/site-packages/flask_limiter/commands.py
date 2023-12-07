import time
from functools import partial
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Union
from urllib.parse import urlparse

import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from limits.strategies import RateLimiter
from rich.console import Console, group
from rich.live import Live
from rich.pretty import Pretty
from rich.prompt import Confirm
from rich.table import Table
from rich.theme import Theme
from rich.tree import Tree
from typing_extensions import TypedDict
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import Rule

from flask_limiter import Limiter
from flask_limiter.constants import ConfigVars, ExemptionScope, HeaderNames
from flask_limiter.util import get_qualified_name
from flask_limiter.wrappers import Limit

limiter_theme = Theme(
    {
        "success": "bold green",
        "danger": "bold red",
        "error": "bold red",
        "blueprint": "bold red",
        "default": "magenta",
        "callable": "cyan",
        "entity": "magenta",
        "exempt": "bold red",
        "route": "yellow",
        "http": "bold green",
        "option": "bold yellow",
    }
)


def render_func(func: Any) -> Union[str, Pretty]:
    if callable(func):
        if func.__name__ == "<lambda>":
            return f"[callable]<lambda>({func.__module__})[/callable]"
        return f"[callable]{func.__module__}.{func.__name__}()[/callable]"
    return Pretty(func)


def render_storage(ext: Limiter) -> Tree:
    render = Tree(ext._storage_uri or "N/A")
    if ext.storage:
        render.add(f"[entity]{ext.storage.__class__.__name__}[/entity]")
        render.add(f"[entity]{ext.storage.storage}[/entity]")  # type: ignore
        render.add(Pretty(ext._storage_options or {}))
        health = ext.storage.check()
        if health:
            render.add("[success]OK[/success]")
        else:
            render.add("[error]Error[/error]")
    return render


def render_strategy(strategy: RateLimiter) -> str:
    return f"[entity]{strategy.__class__.__name__}[/entity]"


def render_limit_state(
    limiter: Limiter, endpoint: str, limit: Limit, key: str, method: str
) -> str:
    args = limit.args_for(endpoint, key, method)
    if not limiter.storage or (limiter.storage and not limiter.storage.check()):
        return ": [error]Storage not available[/error]"
    test = limiter.limiter.test(limit.limit, *args)
    stats = limiter.limiter.get_window_stats(limit.limit, *args)
    if not test:
        return (
            f": [error]Fail[/error] ({stats[1]} out of {limit.limit.amount} remaining)"
        )
    else:
        return f": [success]Pass[/success] ({stats[1]} out of {limit.limit.amount} remaining)"


def render_limit(limit: Limit, simple: bool = True) -> str:
    render = str(limit.limit)
    if simple:
        return render
    options = []
    if limit.deduct_when:
        options.append(f"deduct_when: {render_func(limit.deduct_when)}")
    if limit.exempt_when:
        options.append(f"exempt_when: {render_func(limit.exempt_when)}")
    if options:
        render = f"{render} [option]{{{', '.join(options)}}}[/option]"
    return render


def render_limits(
    app: Flask,
    limiter: Limiter,
    limits: List[Limit],
    endpoint: Optional[str] = None,
    blueprint: Optional[str] = None,
    rule: Optional[Rule] = None,
    exemption_scope: ExemptionScope = ExemptionScope.NONE,
    test: Optional[str] = None,
    method: str = "GET",
    label: Optional[str] = "",
) -> Tree:
    _label = None
    if rule and endpoint:
        _label = f"{endpoint}: {rule}"
    label = _label or label or ""

    renderable = Tree(label)
    entries = []

    for limit in limits:
        if endpoint:
            view_func = app.view_functions.get(endpoint, None)
            source = (
                "blueprint"
                if blueprint
                and limit in limiter.limit_manager.blueprint_limits(app, blueprint)
                else "route"
                if limit
                in limiter.limit_manager.route_limits(
                    get_qualified_name(view_func) if view_func else ""
                )
                else "default"
            )
        else:
            source = "default"
        if limit.per_method and rule and rule.methods:
            for method in rule.methods:
                rendered = render_limit(limit, False)
                entry = f"[{source}]{rendered} [http]({method})[/http][/{source}]"
                if test:
                    entry += render_limit_state(
                        limiter, endpoint or "", limit, test, method
                    )
                entries.append(entry)
        else:
            rendered = render_limit(limit, False)
            entry = f"[{source}]{rendered}[/{source}]"
            if test:
                entry += render_limit_state(
                    limiter, endpoint or "", limit, test, method
                )
            entries.append(entry)
    if not entries and exemption_scope:
        renderable.add("[exempt]Exempt[/exempt]")
    else:
        [renderable.add(entry) for entry in entries]
    return renderable


def get_filtered_endpoint(
    app: Flask,
    console: Console,
    endpoint: Optional[str],
    path: Optional[str],
    method: Optional[str] = None,
) -> Optional[str]:
    if not (endpoint or path):
        return None
    if endpoint:
        if endpoint in current_app.view_functions:
            return endpoint
        else:
            console.print(f"[red]Error: {endpoint} not found")
    elif path:
        adapter = app.url_map.bind("dev.null")
        parsed = urlparse(path)
        try:
            filter_endpoint, _ = adapter.match(
                parsed.path, method=method, query_args=parsed.query
            )
            return filter_endpoint
        except NotFound:
            console.print(
                f"[error]Error: {path} could not be matched to an endpoint[/error]"
            )
        except MethodNotAllowed:
            assert method
            console.print(
                f"[error]Error: {method.upper()}: {path}"
                " could not be matched to an endpoint[/error]"
            )
    raise SystemExit


@click.group(help="Flask-Limiter maintenance & utility commmands")
def cli() -> None:
    pass


@cli.command(help="View the extension configuration")
@with_appcontext  # type: ignore
def config() -> None:
    with current_app.test_request_context():
        console = Console(theme=limiter_theme)
        limiters = list(current_app.extensions.get("limiter", set()))
        limiter = limiters and list(limiters)[0]
        if limiter:
            extension_details = Table(title="Flask-Limiter Config")
            extension_details.add_column("Notes")
            extension_details.add_column("Configuration")
            extension_details.add_column("Value")
            extension_details.add_row(
                "Enabled", ConfigVars.ENABLED, Pretty(limiter.enabled)
            )
            extension_details.add_row(
                "Key Function", ConfigVars.KEY_FUNC, render_func(limiter._key_func)
            )
            extension_details.add_row(
                "Key Prefix", ConfigVars.KEY_PREFIX, Pretty(limiter._key_prefix)
            )
            limiter_config = Tree(ConfigVars.STRATEGY)
            limiter_config_values = Tree(render_strategy(limiter.limiter))
            node = limiter_config.add(ConfigVars.STORAGE_URI)
            node.add("Instance")
            node.add("Backend")
            limiter_config.add(ConfigVars.STORAGE_OPTIONS)
            limiter_config.add("Status")
            limiter_config_values.add(render_storage(limiter))
            extension_details.add_row(
                "Rate Limiting Config", limiter_config, limiter_config_values
            )
            if limiter.limit_manager.application_limits:
                extension_details.add_row(
                    "Application Limits",
                    ConfigVars.APPLICATION_LIMITS,
                    Pretty(
                        [
                            render_limit(limit)
                            for limit in limiter.limit_manager.application_limits
                        ]
                    ),
                )
                extension_details.add_row(
                    None,
                    ConfigVars.APPLICATION_LIMITS_COST,
                    Pretty(limiter._application_limits_cost),
                )
            else:
                extension_details.add_row(
                    "ApplicationLimits Limits",
                    ConfigVars.APPLICATION_LIMITS,
                    Pretty([]),
                )
            if limiter.limit_manager.default_limits:
                extension_details.add_row(
                    "Default Limits",
                    ConfigVars.DEFAULT_LIMITS,
                    Pretty(
                        [
                            render_limit(limit)
                            for limit in limiter.limit_manager.default_limits
                        ]
                    ),
                )
                extension_details.add_row(
                    None,
                    ConfigVars.DEFAULT_LIMITS_PER_METHOD,
                    Pretty(limiter._default_limits_per_method),
                )
                extension_details.add_row(
                    None,
                    ConfigVars.DEFAULT_LIMITS_EXEMPT_WHEN,
                    render_func(limiter._default_limits_exempt_when),
                )
                extension_details.add_row(
                    None,
                    ConfigVars.DEFAULT_LIMITS_DEDUCT_WHEN,
                    render_func(limiter._default_limits_deduct_when),
                )
                extension_details.add_row(
                    None,
                    ConfigVars.DEFAULT_LIMITS_COST,
                    render_func(limiter._default_limits_cost),
                )
            else:
                extension_details.add_row(
                    "Default Limits", ConfigVars.DEFAULT_LIMITS, Pretty([])
                )

            if limiter._headers_enabled:
                header_configs = Tree(ConfigVars.HEADERS_ENABLED)
                header_configs.add(ConfigVars.HEADER_RESET)
                header_configs.add(ConfigVars.HEADER_REMAINING)
                header_configs.add(ConfigVars.HEADER_RETRY_AFTER)
                header_configs.add(ConfigVars.HEADER_RETRY_AFTER_VALUE)

                header_values = Tree(Pretty(limiter._headers_enabled))
                header_values.add(Pretty(limiter._header_mapping[HeaderNames.RESET]))
                header_values.add(
                    Pretty(limiter._header_mapping[HeaderNames.REMAINING])
                )
                header_values.add(
                    Pretty(limiter._header_mapping[HeaderNames.RETRY_AFTER])
                )
                header_values.add(Pretty(limiter._retry_after))
                extension_details.add_row(
                    "Header configuration",
                    header_configs,
                    header_values,
                )
            else:
                extension_details.add_row(
                    "Header configuration", ConfigVars.HEADERS_ENABLED, Pretty(False)
                )

            extension_details.add_row(
                "Fail on first breach",
                ConfigVars.FAIL_ON_FIRST_BREACH,
                Pretty(limiter._fail_on_first_breach),
            )
            extension_details.add_row(
                "On breach callback",
                ConfigVars.ON_BREACH,
                render_func(limiter._on_breach),
            )

            console.print(extension_details)
        else:
            console.print(
                f"No Flask-Limiter extension installed on {current_app}",
                style="bold red",
            )


@cli.command(help="Enumerate details about all routes with rate limits")
@click.option("--endpoint", default=None, help="Endpoint to filter by")
@click.option("--path", default=None, help="Path to filter by")
@click.option("--method", default=None, help="HTTP Method to filter by")
@click.option("--key", default=None, help="Test the limit")
@click.option("--watch/--no-watch", default=False, help="Create a live dashboard")
@with_appcontext  # type: ignore
def limits(
    endpoint: Optional[str] = None,
    path: Optional[str] = None,
    method: str = "GET",
    key: Optional[str] = None,
    watch: bool = False,
) -> None:
    with current_app.test_request_context():
        limiters: Set[Limiter] = current_app.extensions.get("limiter", set())
        limiter: Optional[Limiter] = list(limiters)[0] if limiters else None
        console = Console(theme=limiter_theme)
        if limiter:
            manager = limiter.limit_manager
            groups: Dict[str, List[Callable[..., Tree]]] = {}

            filter_endpoint = get_filtered_endpoint(
                current_app, console, endpoint, path, method
            )
            for rule in sorted(
                current_app.url_map.iter_rules(filter_endpoint), key=lambda r: str(r)
            ):
                rule_endpoint = rule.endpoint
                if rule_endpoint == "static":
                    continue
                if len(rule_endpoint.split(".")) > 1:
                    bp_fullname = ".".join(rule_endpoint.split(".")[:-1])
                    groups.setdefault(bp_fullname, []).append(
                        partial(
                            render_limits,
                            current_app,
                            limiter,
                            manager.resolve_limits(
                                current_app, rule_endpoint, bp_fullname
                            ),
                            rule_endpoint,
                            bp_fullname,
                            rule,
                            exemption_scope=manager.exemption_scope(
                                current_app, rule_endpoint, bp_fullname
                            ),
                            method=method,
                            test=key,
                        )
                    )
                else:
                    groups.setdefault("root", []).append(
                        partial(
                            render_limits,
                            current_app,
                            limiter,
                            manager.resolve_limits(current_app, rule_endpoint, ""),
                            rule_endpoint,
                            None,
                            rule,
                            exemption_scope=manager.exemption_scope(
                                current_app, rule_endpoint, None
                            ),
                            method=method,
                            test=key,
                        )
                    )

            @group()
            def console_renderable() -> Generator:  # type: ignore
                if (
                    limiter
                    and limiter.limit_manager.application_limits
                    and not (endpoint or path)
                ):
                    yield render_limits(
                        current_app,
                        limiter,
                        limiter.limit_manager.application_limits,
                        test=key,
                        method=method,
                        label="[gold3]Application Limits[/gold3]",
                    )
                for name in groups:
                    if name == "root":
                        group_tree = Tree(f"[gold3]{current_app.name}[/gold3]")
                    else:
                        group_tree = Tree(f"[blue]{name}[/blue]")
                    [group_tree.add(renderable()) for renderable in groups[name]]
                    yield group_tree

            if not watch:
                console.print(console_renderable())
            else:  # noqa
                with Live(
                    console_renderable(),
                    console=console,
                    refresh_per_second=0.4,
                    screen=True,
                ) as live:
                    while True:
                        try:
                            live.update(console_renderable())
                            time.sleep(0.4)
                        except KeyboardInterrupt:
                            break
        else:
            console.print(
                f"No Flask-Limiter extension installed on {current_app}",
                style="bold red",
            )


@cli.command(help="Clear limits for a specific key")
@click.option("--endpoint", default=None, help="Endpoint to filter by")
@click.option("--path", default=None, help="Path to filter by")
@click.option("--method", default=None, help="HTTP Method to filter by")
@click.option("--key", default=None, required=True, help="Key to reset the limits for")
@click.option("-y", is_flag=True, help="Skip prompt for confirmation")
@with_appcontext  # type: ignore
def clear(
    key: str,
    endpoint: Optional[str] = None,
    path: Optional[str] = None,
    method: str = "GET",
    y: bool = False,
) -> None:
    with current_app.test_request_context():
        limiters = list(current_app.extensions.get("limiter", set()))
        limiter: Optional[Limiter] = limiters[0] if limiters else None
        console = Console(theme=limiter_theme)
        if limiter:
            manager = limiter.limit_manager
            filter_endpoint = get_filtered_endpoint(
                current_app, console, endpoint, path, method
            )
            Details = TypedDict(
                "Details",
                {
                    "rule": Rule,
                    "limits": List[Limit],
                },
            )
            rule_limits: Dict[str, Details] = {}
            for rule in sorted(
                current_app.url_map.iter_rules(filter_endpoint), key=lambda r: str(r)
            ):
                rule_endpoint = rule.endpoint
                if rule_endpoint == "static":
                    continue
                if len(rule_endpoint.split(".")) > 1:
                    bp_fullname = ".".join(rule_endpoint.split(".")[:-1])
                    rule_limits[rule_endpoint] = Details(
                        rule=rule,
                        limits=manager.resolve_limits(
                            current_app, rule_endpoint, bp_fullname
                        ),
                    )
                else:
                    rule_limits[rule_endpoint] = Details(
                        rule=rule,
                        limits=manager.resolve_limits(current_app, rule_endpoint, ""),
                    )
            application_limits = None
            if not filter_endpoint:
                application_limits = limiter.limit_manager.application_limits

            if not y:  # noqa
                if application_limits:
                    console.print(
                        render_limits(
                            current_app,
                            limiter,
                            application_limits,
                            label="Application Limits",
                            test=key,
                        )
                    )
                for endpoint, details in rule_limits.items():
                    if details["limits"]:
                        console.print(
                            render_limits(
                                current_app,
                                limiter,
                                details["limits"],
                                endpoint,
                                rule=details["rule"],
                                test=key,
                            )
                        )
            if y or Confirm.ask(
                f"Proceed with resetting limits for key: [danger]{key}[/danger]?"
            ):
                if application_limits:
                    node = Tree("Application Limits")
                    for limit in application_limits:
                        limiter.limiter.clear(
                            limit.limit,
                            *limit.args_for("", key, method),
                        )
                        node.add(f"{render_limit(limit)}: [success]Cleared[/success]")
                    console.print(node)
                for endpoint, details in rule_limits.items():
                    if details["limits"]:
                        node = Tree(endpoint)
                        for limit in details["limits"]:
                            if (
                                limit.per_method
                                and details["rule"]
                                and details["rule"].methods
                                and not method
                            ):
                                for rule_method in details["rule"].methods:
                                    limiter.limiter.clear(
                                        limit.limit,
                                        *limit.args_for(endpoint, key, rule_method),
                                    )
                            else:
                                limiter.limiter.clear(
                                    limit.limit,
                                    *limit.args_for(endpoint, key, method),
                                )
                            node.add(
                                f"{render_limit(limit)}: [success]Cleared[/success]"
                            )
                        console.print(node)
        else:
            console.print(
                f"No Flask-Limiter extension installed on {current_app}",
                style="bold red",
            )


if __name__ == "__main__":  # noqa
    cli()
