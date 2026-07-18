from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from .database import SessionLocal, engine, init_database
from .event_store import EventStore
from .schemas import RunCreate
from .simulator import DEMO_SEED, build_demo_events


def migrate() -> None:
    config = Config("alembic.ini")
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
    if "analysis_runs" in tables and current_revision is None:
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")


def reset() -> None:
    init_database()
    with SessionLocal() as session:
        EventStore(session).reset()
    root = Path("data/artifacts")
    root.mkdir(parents=True, exist_ok=True)
    print("Evolastra local state reset.")


def seed() -> None:
    init_database()
    with SessionLocal() as session:
        store = EventStore(session)
        record, _ = store.create_run(
            RunCreate(
                title="Churn atlas: reliable signals and caveats",
                objective="Identify reliable drivers of customer churn without overstating causal evidence",
                seed=DEMO_SEED,
                tags=["seeded-demo", "churn", "observability"],
            )
        )
        events = build_demo_events(record.id, DEMO_SEED)
        for event in events:
            result = store.ingest(event.model_dump(mode="json"))
            if not result.accepted:
                raise RuntimeError(result.reason)
        durable_total = record.last_sequence
    print(
        f"Seeded {record.id} with {len(events) + 1} semantic events "
        f"and {durable_total - len(events) - 1} snapshot events ({durable_total} durable total)."
    )


def _print_result(result: object) -> None:
    print(json.dumps(result, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(prog="evolastra")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_name in ("migrate", "reset", "seed"):
        subparsers.add_parser(command_name)

    service_parser = subparsers.add_parser("service", help="Manage the local-private companion")
    service_commands = service_parser.add_subparsers(dest="service_command", required=True)
    install_parser = service_commands.add_parser("install")
    install_parser.add_argument("--port", type=int, default=8000)
    install_parser.add_argument("--origin", action="append", default=[])
    install_parser.add_argument("--no-hooks", action="store_true")
    install_parser.add_argument(
        "--autostart",
        action="store_true",
        help="Start the companion automatically when the user logs in",
    )
    for command_name in ("start", "stop", "status"):
        service_commands.add_parser(command_name)
    uninstall_parser = service_commands.add_parser("uninstall")
    uninstall_parser.add_argument("--keep-hooks", action="store_true")

    codex_parser = subparsers.add_parser("codex", help="Manage automatic Codex hooks")
    codex_commands = codex_parser.add_subparsers(dest="codex_command", required=True)
    codex_commands.add_parser("install")
    codex_commands.add_parser("status")
    codex_commands.add_parser("uninstall")
    subparsers.add_parser("pair", help="Print a one-time browser pairing code")
    args = parser.parse_args()
    if args.command in {"migrate", "reset", "seed"}:
        {"migrate": migrate, "reset": reset, "seed": seed}[args.command]()
        return
    if args.command == "service":
        from .service import (
            install_service,
            service_status,
            start_service,
            stop_service,
            uninstall_service,
        )

        if args.service_command == "install":
            _print_result(
                install_service(
                    port=args.port,
                    origins=args.origin,
                    install_hooks=not args.no_hooks,
                    autostart=args.autostart,
                )
            )
        elif args.service_command == "start":
            _print_result(start_service())
        elif args.service_command == "stop":
            _print_result(stop_service())
        elif args.service_command == "status":
            _print_result(service_status())
        else:
            _print_result(uninstall_service(uninstall_hooks=not args.keep_hooks))
        return
    if args.command == "codex":
        from .codex_install import codex_hook_status, install_codex_hooks, uninstall_codex_hooks

        if args.codex_command == "install":
            _print_result(install_codex_hooks())
        elif args.codex_command == "status":
            _print_result(codex_hook_status())
        else:
            _print_result(uninstall_codex_hooks())
        return
    if args.command == "pair":
        from .service import create_pairing_code

        _print_result(create_pairing_code())


if __name__ == "__main__":
    main()
