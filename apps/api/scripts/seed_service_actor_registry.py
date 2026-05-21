from argparse import ArgumentParser

from sqlalchemy.orm import Session

from agent_governance_api.config import get_settings
from agent_governance_api.database import create_database_engine
from agent_governance_api.service_actor_registry_seed import (
    format_seed_results,
    seed_service_actor_registry_from_settings,
)


def main() -> int:
    parser = ArgumentParser(
        description=(
            "Seed DB-backed service actor registry records from hashed "
            "AGCP_SERVICE_ACTOR_API_KEYS config."
        )
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

    settings = get_settings()
    engine = create_database_engine(args.database_url)
    dry_run = not args.apply
    try:
        with Session(engine) as session:
            results = seed_service_actor_registry_from_settings(
                session,
                settings,
                dry_run=dry_run,
            )
            if dry_run:
                session.rollback()
            print(format_seed_results(results, dry_run=dry_run))
    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
