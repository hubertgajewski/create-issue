#!/usr/bin/env python3
"""Normalize a create-issue target project or parent issue reference.

Implements references/reference-grammar.md. Prints one JSON object with provider, host,
project, and issue on success; exits 2 with a reason on standard error otherwise. A reason
never contains the rejected text, which may carry a credential.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import NoReturn

PROVIDERS = ("github", "gitlab")
MAX_REFERENCE_LENGTH = 4096
MAX_PROJECT_LENGTH = 255
MAX_HOST_LENGTH = 253

PRINTABLE = re.compile(r"[!-~]+")
URL = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://(?P<authority>[^/?#]*)(?P<path>[^?#]*)(?:[?#].*)?"
)
AUTHORITY = re.compile(r"(?P<host>[^:]+)(?::(?P<port>[0-9]+))?")
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
COMPONENT = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_.-]{0,99}")
ISSUE_NUMBER = re.compile(r"[1-9][0-9]{0,19}")
SHORT_PARENT = re.compile(r"#?(?P<number>[^#/]*)")
QUALIFIED_PARENT = re.compile(r"(?P<project>[^#]+)#(?P<number>[^#]*)")


class Rejected(ValueError):
    """The reference is outside the grammar. The message is safe to print."""


def check_text(value: str, what: str) -> str:
    value = value.strip()
    if not value:
        raise Rejected(f"{what} is empty")
    if len(value) > MAX_REFERENCE_LENGTH:
        raise Rejected(f"{what} is too long")
    if not PRINTABLE.fullmatch(value):
        raise Rejected(f"{what} must be printable ASCII without spaces")
    return value


def issue_number(text: str) -> int:
    if not ISSUE_NUMBER.fullmatch(text):
        raise Rejected("issue number must be 1 to 20 digits with no leading zero")
    return int(text)


def provider_of_host(host: str) -> str | None:
    labels = set(host.split(":", 1)[0].split("."))
    found = [provider for provider in PROVIDERS if provider in labels]
    if len(found) > 1:
        raise Rejected("host names both GitHub and GitLab")
    return found[0] if found else None


def normalize_host(authority: str) -> str:
    if "@" in authority:
        raise Rejected("URL must not contain user information")
    match = AUTHORITY.fullmatch(authority)
    if match is None:
        raise Rejected("URL has an invalid host")
    host = match.group("host").lower()
    labels = host.split(".")
    if len(host) > MAX_HOST_LENGTH or not all(HOST_LABEL.fullmatch(label) for label in labels):
        raise Rejected("URL has an invalid host")
    port = match.group("port")
    if port is None or port == "443":
        return host
    if port.startswith("0") or not 1 <= int(port) <= 65535:
        raise Rejected("URL has an invalid port")
    return f"{host}:{port}"


def resolve_provider(host: str | None, provider: str | None) -> str | None:
    named = provider_of_host(host) if host else None
    if named and provider and named != provider:
        raise Rejected("--provider contradicts the host")
    return named or provider


def check_project(parts: list[str], provider: str | None) -> str:
    project = "/".join(parts)
    if (
        len(parts) < 2
        or len(project) > MAX_PROJECT_LENGTH
        or not all(COMPONENT.fullmatch(part) and part not in (".", "..") for part in parts)
    ):
        raise Rejected("not a valid project path")
    if provider == "github" and len(parts) != 2:
        raise Rejected("a GitHub project path must have exactly two components")
    if provider == "gitlab" and parts[0].lower() == "groups":
        raise Rejected("a group-level GitLab URL does not name a project")
    return project


def split_url(value: str) -> tuple[str, list[str]]:
    """Return the normalized host and path components of an HTTPS URL."""
    match = URL.fullmatch(value)
    if match is None:
        raise Rejected("not a valid URL")
    scheme = match.group("scheme").lower()
    if scheme == "http":
        raise Rejected("plain HTTP is not accepted; use HTTPS")
    if scheme != "https":
        raise Rejected("only HTTPS URLs are accepted")
    host = normalize_host(match.group("authority"))
    path = match.group("path")
    if "%" in path:
        raise Rejected("URL path must not use percent-encoding")
    path = path.removeprefix("/").removesuffix("/")
    if not path:
        raise Rejected("URL has no project path")
    parts = path.split("/")
    if "" in parts:
        raise Rejected("not a valid project path")
    return host, parts


def project_reference(value: str, provider: str | None) -> dict[str, object]:
    if "://" not in value:
        return {
            "host": None,
            "issue": None,
            "project": check_project(value.split("/"), provider),
            "provider": provider,
        }
    host, parts = split_url(value)
    provider = resolve_provider(host, provider)
    if "-" in parts:
        raise Rejected("not a project URL: it points inside a project")
    parts[-1] = parts[-1].removesuffix(".git")
    return {
        "host": host,
        "issue": None,
        "project": check_project(parts, provider),
        "provider": provider,
    }


def parent_reference(
    value: str, provider: str, target_host: str, target_project: str
) -> dict[str, object]:
    if "://" not in value:
        short = SHORT_PARENT.fullmatch(value)
        qualified = QUALIFIED_PARENT.fullmatch(value)
        if short is not None:
            project, number = target_project, short.group("number")
        elif qualified is not None:
            project = check_project(qualified.group("project").split("/"), provider)
            number = qualified.group("number")
        else:
            raise Rejected("not an issue reference")
        return {
            "host": target_host,
            "issue": issue_number(number),
            "project": project,
            "provider": provider,
        }

    host, parts = split_url(value)
    resolve_provider(host, provider)
    if host != target_host:
        raise Rejected("parent is on another host than the target")
    if len(parts) >= 4 and parts[-3] == "-" and parts[-2] in ("issues", "work_items"):
        form, project_parts = "gitlab", parts[:-3]
    elif len(parts) >= 3 and parts[-2] == "issues" and "-" not in parts:
        form, project_parts = "github", parts[:-2]
    else:
        raise Rejected("not an issue or work item URL")
    if form != provider:
        raise Rejected(f"not a {provider} issue URL")
    return {
        "host": host,
        "issue": issue_number(parts[-1]),
        "project": check_project(project_parts, provider),
        "provider": provider,
    }


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse messages can quote argument values, which may hold a credential.
        self.exit(2, f"error: invalid arguments; run {self.prog} --help\n")


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=__doc__.split("\n", 1)[0])
    modes = parser.add_subparsers(dest="mode", required=True, parser_class=Parser)

    project = modes.add_parser("project", help="normalize a target project reference")
    project.add_argument("--ref", required=True, help="project path or HTTPS project URL")
    project.add_argument("--provider", choices=PROVIDERS, help="provider, when known")

    parent = modes.add_parser("parent", help="normalize a parent issue reference")
    parent.add_argument("--ref", required=True, help="#N, N, PROJECT#N, or HTTPS issue URL")
    parent.add_argument("--provider", choices=PROVIDERS, required=True, help="frozen target provider")
    parent.add_argument("--host", required=True, help="frozen target host")
    parent.add_argument("--project", required=True, help="frozen target project")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        value = check_text(args.ref, "reference")
        if args.mode == "project":
            result = project_reference(value, args.provider)
        else:
            target_host = normalize_host(check_text(args.host, "--host"))
            resolve_provider(target_host, args.provider)
            target_project = check_project(
                check_text(args.project, "--project").split("/"), args.provider
            )
            result = parent_reference(value, args.provider, target_host, target_project)
    except Rejected as rejection:
        print(f"error: {rejection}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
