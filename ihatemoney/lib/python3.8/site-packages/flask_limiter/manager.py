from __future__ import annotations

import itertools
import logging
from typing import Dict, Iterable, List, Optional, Tuple

import flask
from ordered_set import OrderedSet

from .constants import ExemptionScope
from .util import get_qualified_name
from .wrappers import Limit, LimitGroup


class LimitManager:
    def __init__(
        self,
        application_limits: List[LimitGroup],
        default_limits: List[LimitGroup],
        static_decorated_limits: Dict[str, OrderedSet[Limit]],
        dynamic_decorated_limits: Dict[str, OrderedSet[LimitGroup]],
        static_blueprint_limits: Dict[str, OrderedSet[Limit]],
        dynamic_blueprint_limits: Dict[str, OrderedSet[LimitGroup]],
        route_exemptions: Dict[str, ExemptionScope],
        blueprint_exemptions: Dict[str, ExemptionScope],
    ) -> None:
        self._application_limits = application_limits
        self._default_limits = default_limits
        self._static_decorated_limits = static_decorated_limits
        self._runtime_decorated_limits = dynamic_decorated_limits
        self._static_blueprint_limits = static_blueprint_limits
        self._runtime_blueprint_limits = dynamic_blueprint_limits
        self._route_exemptions = route_exemptions
        self._blueprint_exemptions = blueprint_exemptions
        self._endpoint_hints: Dict[str, OrderedSet[str]] = {}
        self._logger = logging.getLogger("flask-limiter")

    @property
    def application_limits(self) -> List[Limit]:
        return list(itertools.chain(*self._application_limits))

    @property
    def default_limits(self) -> List[Limit]:
        return list(itertools.chain(*self._default_limits))

    def set_application_limits(self, limits: List[LimitGroup]) -> None:
        self._application_limits = limits

    def set_default_limits(self, limits: List[LimitGroup]) -> None:
        self._default_limits = limits

    def add_decorated_runtime_limit(self, route: str, limit: LimitGroup) -> None:
        self._runtime_decorated_limits.setdefault(route, OrderedSet()).add(limit)

    def add_runtime_blueprint_limits(self, blueprint: str, limit: LimitGroup) -> None:
        self._runtime_blueprint_limits.setdefault(blueprint, OrderedSet()).add(limit)

    def add_decorated_static_limit(self, route: str, *limits: Limit) -> None:
        self._static_decorated_limits.setdefault(route, OrderedSet()).update(
            OrderedSet(limits)
        )

    def add_static_blueprint_limits(self, blueprint: str, *limits: Limit) -> None:
        self._static_blueprint_limits.setdefault(blueprint, OrderedSet()).update(
            OrderedSet(limits)
        )

    def add_route_exemption(self, route: str, scope: ExemptionScope) -> None:
        self._route_exemptions[route] = scope

    def add_blueprint_exemption(self, blueprint: str, scope: ExemptionScope) -> None:
        self._blueprint_exemptions[blueprint] = scope

    def add_endpoint_hint(self, endpoint: str, callable: str) -> None:
        self._endpoint_hints.setdefault(endpoint, OrderedSet()).add(callable)

    def has_hints(self, endpoint: str) -> bool:
        return bool(self._endpoint_hints.get(endpoint))

    def resolve_limits(
        self,
        app: flask.Flask,
        endpoint: Optional[str] = None,
        blueprint: Optional[str] = None,
        callable_name: Optional[str] = None,
        in_middleware: bool = False,
        marked_for_limiting: bool = False,
        fallback_limits: Optional[List[Limit]] = None,
    ) -> List[Limit]:
        before_request_context = in_middleware and marked_for_limiting
        route_limits = []
        hinted_limits = []
        if endpoint:
            if not in_middleware:
                if not callable_name:
                    view_func = app.view_functions.get(endpoint, None)
                    name = get_qualified_name(view_func) if view_func else ""
                else:
                    name = callable_name
                route_limits.extend(self.route_limits(name))

            for hint in self._endpoint_hints.get(endpoint, OrderedSet()):
                hinted_limits.extend(self.route_limits(hint))

        if blueprint:
            if not before_request_context and (
                not route_limits
                or all(not limit.override_defaults for limit in route_limits)
            ):
                route_limits.extend(self.blueprint_limits(app, blueprint))
        exemption_scope = self.exemption_scope(app, endpoint, blueprint)
        all_limits = []

        if fallback_limits:
            all_limits.extend(fallback_limits)

        if not all_limits:
            all_limits = (
                self.application_limits
                if in_middleware and not (exemption_scope & ExemptionScope.APPLICATION)
                else []
            )
            all_limits += route_limits
            explicit_limits_exempt = all(limit.method_exempt for limit in route_limits)
            combined_defaults = all(
                not limit.override_defaults for limit in route_limits
            )
            hinted_limits_request_defaults = (
                all(not limit.override_defaults for limit in hinted_limits)
                if hinted_limits
                else False
            )
            if (
                (explicit_limits_exempt or combined_defaults)
                and (
                    not (
                        before_request_context
                        or exemption_scope & ExemptionScope.DEFAULT
                    )
                )
            ) or hinted_limits_request_defaults:
                all_limits += self.default_limits
        return all_limits

    def exemption_scope(
        self, app: flask.Flask, endpoint: Optional[str], blueprint: Optional[str]
    ) -> ExemptionScope:
        view_func = app.view_functions.get(endpoint or "", None)
        name = get_qualified_name(view_func) if view_func else ""
        route_exemption_scope = self._route_exemptions[name]
        blueprint_instance = app.blueprints.get(blueprint) if blueprint else None

        if not blueprint_instance:
            return route_exemption_scope
        else:
            assert blueprint
            (
                blueprint_exemption_scope,
                ancestor_exemption_scopes,
            ) = self._blueprint_exemption_scope(app, blueprint)
            if (
                blueprint_exemption_scope
                & ~(ExemptionScope.DEFAULT | ExemptionScope.APPLICATION)
                or ancestor_exemption_scopes
            ):
                for exemption in ancestor_exemption_scopes.values():
                    blueprint_exemption_scope |= exemption
            return route_exemption_scope | blueprint_exemption_scope

    def route_limits(self, callable_name: str) -> List[Limit]:
        limits = []
        if not self._route_exemptions[callable_name]:
            for limit in self._static_decorated_limits.get(callable_name, []):
                limits.append(limit)

            if callable_name in self._runtime_decorated_limits:
                for group in self._runtime_decorated_limits[callable_name]:
                    try:
                        for limit in group:
                            limits.append(limit)
                    except ValueError as e:
                        self._logger.error(
                            f"failed to load ratelimit for function {callable_name}: {e}",
                        )
        return limits

    def blueprint_limits(self, app: flask.Flask, blueprint: str) -> List[Limit]:
        limits: List[Limit] = []

        blueprint_instance = app.blueprints.get(blueprint) if blueprint else None
        if blueprint_instance:
            blueprint_name = blueprint_instance.name
            blueprint_ancestory = set(blueprint.split(".") if blueprint else [])

            self_exemption, ancestor_exemptions = self._blueprint_exemption_scope(
                app, blueprint
            )

            if not (
                self_exemption & ~(ExemptionScope.DEFAULT | ExemptionScope.APPLICATION)
                or ancestor_exemptions
            ):
                blueprint_self_dynamic_limits = self._runtime_blueprint_limits.get(
                    blueprint_name, OrderedSet()
                )
                blueprint_dynamic_limits: Iterable[LimitGroup] = (
                    itertools.chain(
                        *(
                            self._runtime_blueprint_limits.get(member, [])
                            for member in blueprint_ancestory.intersection(
                                self._runtime_blueprint_limits
                            )
                        )
                    )
                    if not (
                        blueprint_self_dynamic_limits
                        or all(
                            limit.override_defaults
                            for limit in blueprint_self_dynamic_limits
                        )
                    )
                    and not self._blueprint_exemptions[blueprint_name]
                    & ExemptionScope.ANCESTORS
                    else blueprint_self_dynamic_limits
                )
                if blueprint_dynamic_limits:
                    for limit_group in blueprint_dynamic_limits:
                        try:
                            limits.extend(
                                [
                                    Limit(
                                        limit.limit,
                                        limit.key_func,
                                        limit.scope,
                                        limit.per_method,
                                        limit.methods,
                                        limit.error_message,
                                        limit.exempt_when,
                                        limit.override_defaults,
                                        limit.deduct_when,
                                        limit.on_breach,
                                        limit.cost,
                                    )
                                    for limit in limit_group
                                ]
                            )
                        except ValueError as e:
                            self._logger.error(
                                f"failed to load ratelimit for blueprint {blueprint_name}: {e}",
                            )
            blueprint_self_limits = self._static_blueprint_limits.get(
                blueprint_name, OrderedSet()
            )
            if (
                not (
                    blueprint_self_limits
                    and all(limit.override_defaults for limit in blueprint_self_limits)
                )
                and not self._blueprint_exemptions[blueprint_name]
                & ExemptionScope.ANCESTORS
            ):
                for member in blueprint_ancestory.intersection(
                    self._static_blueprint_limits
                ).difference(ancestor_exemptions):
                    limits.extend(self._static_blueprint_limits[member])
            else:
                limits.extend(blueprint_self_limits)
        return limits

    def _blueprint_exemption_scope(
        self, app: flask.Flask, blueprint_name: str
    ) -> Tuple[ExemptionScope, Dict[str, ExemptionScope]]:
        name = app.blueprints[blueprint_name].name
        exemption = self._blueprint_exemptions[name] & ~(ExemptionScope.ANCESTORS)

        ancestory = set(blueprint_name.split("."))
        ancestor_exemption = {
            k
            for k, f in self._blueprint_exemptions.items()
            if f & ExemptionScope.DESCENDENTS
        }.intersection(ancestory)

        return exemption, {k: self._blueprint_exemptions[k] for k in ancestor_exemption}
