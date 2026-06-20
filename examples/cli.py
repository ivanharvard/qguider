import argparse
import qguider
import logging
from pathlib import Path
from examples._ui import make_rich_ui
import shutil


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }

    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        return (
            f"{color}[{record.levelname}]{self.RESET} "
            f"{record.getMessage()}"
        )
    
def configure_logging(level: str = "INFO"):
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())

    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

def download_all(progress = None, agg = False, sleep_for_sec = 0):
    qgdr = qguider.QGuider(creds=".env")

    results = (
        qgdr
        .query()
        .semesters(
            "Fall 2023",
            "Spring 2024",
            "Fall 2024",
            "Spring 2025",
            "Fall 2025",
            "Spring 2026",
        )
        .progress(progress)
        .download(
            checkpoint=True,
            checkpoint_interval=15,
            report_failed=True,
            sleep_for_sec=sleep_for_sec
        )
        .parse(
            skip_failed=True,
        )
    )

    if agg:
        results = results.agg(by="id")

    qguider.exporter.to_json(results, "qguider_data/all_qguides.json")

def parse_all(progress=None):
    import qguider.parser

    qguide_files = list(Path("qguider_data").rglob("*.html"))
    task_id = None

    if progress:
        task_id = progress.add_task("Parsing QGuides", total=len(qguide_files))

    for file in qguide_files:
        try:
            qguide = qguider.parser.QGuideParser(file).parse()
            print(qguide.course, qguide.instructor)
        finally:
            if progress and task_id is not None:
                progress.advance(task_id)

def import_all():
    results = qguider.importer.from_json("qguider_data/all_qguides.json")
    print(f"Imported {len(results)} QGuides.")

def clear_all():
    shutil.rmtree("qguider_data", ignore_errors=True)
    print("Cleared all downloaded data.")

def _parse_sleep_arg(value: str) -> float | tuple[float, float]:
    if "," in value:
        parts = value.split(",")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError("Range must be two comma-separated values, e.g. 2.5,5.0")
        return (float(parts[0]), float(parts[1]))
    return float(value)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and parse QGuides")
    parser.add_argument("--import", dest="do_import", action="store_true")
    parser.add_argument("--parse", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--no-agg", action="store_true")
    parser.add_argument("--clear-all", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--sleep-for-sec",
        default=0,
        type=_parse_sleep_arg,
        help="Set an exact value or a random interval of seconds to sleep "
             "between requests and retries when downloading."
             "\nExample:\n"
             "\n--sleep-for-sec 4"
             "\n--sleep-for-sec 2.5,5.0"
    )

    args = parser.parse_args()

    if args.clear_all:
        clear_all()

    if args.progress:
        console, layout, progress, Live = make_rich_ui(args.log_level)

        with Live(layout, console=console, refresh_per_second=10):
            if args.download:
                download_all(
                    progress=progress, 
                    agg=not args.no_agg,
                    sleep_for_sec=args.sleep_for_sec
                )

            if args.parse:
                parse_all(progress=progress)

            if args.do_import:
                import_all()
    else:
        configure_logging(args.log_level)

        if args.download:
            download_all(
                progress=None, 
                agg=not args.no_agg, 
                sleep_for_sec=args.sleep_for_sec
            )

        if args.parse:
            parse_all(progress=None)

        if args.do_import:
            import_all()

    