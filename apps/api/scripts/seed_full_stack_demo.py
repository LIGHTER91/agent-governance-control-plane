import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from sys import stderr

API_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = API_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from agent_governance_api.database import create_database_engine  # noqa: E402
from agent_governance_api.full_stack_demo_seed import (  # noqa: E402
    format_full_stack_demo_seed_result,
    metadata_pre_check_demo_runtime_payload,
    seed_full_stack_demo,
)


def main() -> int:
    parser = ArgumentParser(
        description=("Seed safe local-only demo data for the full-stack AGCP UI flow.")
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write records. Without this flag, the command runs as a dry run.",
    )
    parser.add_argument(
        "--database-url",
        help="Optional database URL override. Defaults to AGCP_DATABASE_URL.",
    )
    parser.add_argument(
        "--print-runtime-payload",
        action="store_true",
        help=(
            "Print only the metadata pre-check Runtime Gateway payload JSON. "
            "Without --apply this does not connect to the database."
        ),
    )
    args = parser.parse_args()

    if args.print_runtime_payload and not args.apply:
        print(json.dumps(metadata_pre_check_demo_runtime_payload(), sort_keys=True))
        return 0

    engine = create_database_engine(args.database_url)
    dry_run = not args.apply
    try:
        with Session(engine) as session:
            result = seed_full_stack_demo(session, dry_run=dry_run)
            if dry_run:
                session.rollback()
            if args.print_runtime_payload:
                print(
                    json.dumps(
                        metadata_pre_check_demo_runtime_payload(),
                        sort_keys=True,
                    )
                )
            else:
                print(format_full_stack_demo_seed_result(result))
    except SQLAlchemyError as exc:
        print(f"ERROR: Could not seed local demo data: {exc}", file=stderr)
        print(
            "Hint: verify AGCP_DATABASE_URL, make sure PostgreSQL is reachable, "
            "and run `uv run alembic upgrade head` first.",
            file=stderr,
        )
        return 1
    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
