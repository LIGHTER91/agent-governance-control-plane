from argparse import ArgumentParser
from sys import stderr

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from agent_governance_api.database import create_database_engine
from agent_governance_api.full_stack_demo_seed import (
    format_full_stack_demo_seed_result,
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
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    dry_run = not args.apply
    try:
        with Session(engine) as session:
            result = seed_full_stack_demo(session, dry_run=dry_run)
            if dry_run:
                session.rollback()
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
