from __future__ import annotations

import argparse
from pathlib import Path

from backend.data_bridge.adapters.sqlite_adapter import SQLiteCatalogAdapter
from backend.data_bridge.models import CourseOffering
from backend.data_pipeline.calendar_scraper import scrape_course_name_and_description
from backend.data_pipeline.migrate_from_folders import migrate_from_folders
from backend.data_pipeline.scrape_descriptions import scrape_missing_descriptions
from backend.data_pipeline.schema import init_db


def _default_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "magellan.db"


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description="MagellanAI data pipeline CLI")
    parser.add_argument("--db-path", default=str(_default_db_path()))
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db")

    migrate_folders_parser = subparsers.add_parser("migrate-from-folders")
    migrate_folders_parser.add_argument("--data-dir", default=str(_default_data_dir()))

    subparsers.add_parser("validate")

    scrape_parser = subparsers.add_parser("scrape-missing-descriptions")
    scrape_parser.add_argument("--limit", type=int, default=None)
    scrape_parser.add_argument("--include-excluded", action="store_true")
    scrape_parser.add_argument("--delay-s", type=float, default=0.25)
    scrape_parser.add_argument(
        "--report-path",
        default=None,
        help="Optional CSV path to write failed course_code list.",
    )
    scrape_parser.add_argument(
        "--only-code",
        action="append",
        default=None,
        help="Repeatable. If provided, only scrape these codes.",
    )

    upsert_parser = subparsers.add_parser("upsert-course")
    upsert_parser.add_argument("--course-code", required=True)
    upsert_parser.add_argument("--term", required=True, choices=["F", "S", "Y", "f", "s", "y"])
    upsert_parser.add_argument("--name", default=None)
    upsert_parser.add_argument("--description", default=None)
    upsert_parser.add_argument("--math", type=float, default=None)
    upsert_parser.add_argument("--ns", type=float, default=None)
    upsert_parser.add_argument("--cs", type=float, default=None)
    upsert_parser.add_argument("--es", type=float, default=None)
    upsert_parser.add_argument("--ed", type=float, default=None)
    upsert_parser.add_argument("--course-type", choices=["technical", "non_technical"], default="technical")
    upsert_parser.add_argument("--non-technical-type", choices=["hss", "cs", "other"], default=None)
    upsert_parser.add_argument("--area", type=int, default=None)
    upsert_parser.add_argument("--kernel", type=int, choices=[0, 1], default=0)
    upsert_parser.add_argument("--technical-elective", type=int, choices=[0, 1], default=0)
    upsert_parser.add_argument("--free-elective", type=int, choices=[0, 1], default=1)
    upsert_parser.add_argument("--is-excluded", type=int, choices=[0, 1], default=0)
    upsert_parser.add_argument(
        "--allow-update",
        action="store_true",
        help="If offering already exists, update it. Default behavior is insert-only.",
    )

    remove_parser = subparsers.add_parser("remove-course")
    remove_parser.add_argument("--course-code", required=True)
    remove_parser.add_argument("--term", required=True, choices=["F", "S", "Y", "f", "s", "y"])
    remove_parser.add_argument("--hard", action="store_true")
    remove_parser.add_argument("--reason", default=None)

    args = parser.parse_args()
    db_path = Path(args.db_path)

    if args.command == "init-db":
        init_db(db_path)
        print(f"Initialized database at {db_path}")
        return

    if args.command == "migrate-from-folders":
        init_db(db_path)
        migrate_from_folders(db_path=db_path, data_dir=Path(args.data_dir))
        print(f"Migrated folder-based CSVs into {db_path}")
        return

    adapter = SQLiteCatalogAdapter(db_path=db_path)

    if args.command == "validate":
        issues = adapter.validate_catalog()
        if issues:
            print("Catalog validation issues:")
            for issue in issues:
                print(f"- {issue}")
            raise SystemExit(1)
        print("Catalog validation passed")
        return

    if args.command == "scrape-missing-descriptions":
        only = set([c.strip() for c in (args.only_code or []) if c and c.strip()]) or None
        filled, failed, failed_codes = scrape_missing_descriptions(
            db_path=db_path,
            limit=args.limit,
            include_excluded=args.include_excluded,
            delay_s=float(args.delay_s),
            only_codes=only,
        )
        print(f"Scrape complete. Filled: {filled}, Failed: {failed}")
        if args.report_path and failed_codes:
            p = Path(args.report_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("course_code\n" + "\n".join(failed_codes) + "\n")
            print(f"Wrote failure report to {p}")
        if failed:
            raise SystemExit(1)
        return

    if args.command == "upsert-course":
        course_code = args.course_code.strip()
        term = args.term.upper()
        existing = adapter.get_course_offering(course_code, term)
        if existing and not args.allow_update:
            print(
                f"Offering already exists for {course_code} {term}. "
                "No changes made. Use --allow-update to overwrite."
            )
            return

        scraped_name, scraped_description = scrape_course_name_and_description(course_code)
        if not scraped_name or not scraped_description:
            print(
                f"Unable to scrape name/description for {course_code}. "
                "Course was not added/updated."
            )
            raise SystemExit(1)

        payload = CourseOffering(
            course_code=course_code,
            term=term,
            name=scraped_name,
            description=scraped_description,
            math=args.math,
            ns=args.ns,
            cs=args.cs,
            es=args.es,
            ed=args.ed,
            course_type=args.course_type,
            non_technical_type=args.non_technical_type,
            area=args.area,
            kernel_course=bool(args.kernel),
            technical_elective=bool(args.technical_elective),
            free_elective=bool(args.free_elective),
            is_excluded=bool(args.is_excluded),
            active=True,
        )
        adapter.upsert_course_offering(payload, scrape_if_missing=False)
        action = "Updated" if existing else "Inserted"
        print(f"{action} {course_code} {term}")
        return

    if args.command == "remove-course":
        if args.hard:
            adapter.hard_remove_course(args.course_code, args.term.upper())
            print(f"Hard-removed {args.course_code} {args.term.upper()}")
        else:
            adapter.soft_remove_course(args.course_code, args.term.upper(), reason=args.reason)
            print(f"Soft-removed {args.course_code} {args.term.upper()}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

