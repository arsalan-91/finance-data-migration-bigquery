"""Generate synthetic SAP-style CO documents (COBK headers, COEP line items).

All data is synthetic and reproducible: the same --seed always produces the
same files. A share of documents is deliberately corrupted (one error each)
so the dbt quarantine rules have something to catch.
"""

import argparse
import csv
import logging
import random
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

Row = dict[str, str | int]

CONTROLLING_AREA = "1000"
CURRENCY = "SAR"
BUSINESS_TRANSACTION = "RKU1"  # SAP: manual cost reposting
UNKNOWN_COST_CENTER = "CC9999"

COST_CENTERS = {
    "CC1010": "Finance",
    "CC1020": "Human Resources",
    "CC2010": "Sales North",
    "CC2020": "Sales South",
    "CC3010": "Production",
    "CC3020": "Maintenance",
    "CC4010": "IT Services",
    "CC5010": "Logistics",
}
COST_ELEMENTS = ["400000", "410000", "420000", "430000", "470000", "481000"]
USERS = ["FIUSER01", "FIUSER02", "COUSER01", "COUSER02"]

ERROR_TYPES = (
    "missing_key",
    "line_without_header",
    "unbalanced_document",
    "zero_amount",
    "unknown_cost_center",
    "invalid_posting_date",
)

CSKS_COLUMNS = ["kokrs", "kostl", "ktext"]
COBK_COLUMNS = [
    "kokrs", "belnr", "gjahr", "vrgng", "budat", "bldat",
    "cpudt", "cputm", "usnam", "bltxt",
]
COEP_COLUMNS = [
    "kokrs", "belnr", "buzei", "gjahr", "perio", "objnr",
    "kstar", "wkgbtr", "twaer", "beknz", "sgtxt",
]


def object_number(cost_center: str) -> str:
    """Return the SAP object number (OBJNR) of a cost center: 'KS' + KOKRS + KOSTL."""
    return f"KS{CONTROLLING_AREA}{cost_center}"


def random_amount(rng: random.Random) -> Decimal:
    """Return a positive amount between 10.00 and 50,000.00 with exactly two decimals."""
    return (Decimal(rng.randint(1_000, 5_000_000)) / Decimal(100)).quantize(Decimal("0.01"))


def build_document(
    rng: random.Random, doc_number: int, fiscal_year: int
) -> tuple[Row, list[Row]]:
    """Build one balanced cost reposting document (header + line items)."""
    belnr = f"{doc_number:010d}"
    posting_date = date(fiscal_year, 1, 1) + timedelta(days=rng.randrange(365))
    entered_at = datetime.combine(posting_date, time(8)) + timedelta(
        minutes=rng.randrange(600)
    )
    header: Row = {
        "kokrs": CONTROLLING_AREA,
        "belnr": belnr,
        "gjahr": fiscal_year,
        "vrgng": BUSINESS_TRANSACTION,
        "budat": posting_date.isoformat(),
        "bldat": (posting_date - timedelta(days=rng.randrange(5))).isoformat(),
        "cpudt": entered_at.date().isoformat(),
        "cputm": entered_at.time().isoformat(),
        "usnam": rng.choice(USERS),
        "bltxt": "Cost reposting",
    }

    lines: list[Row] = []
    for _ in range(rng.randint(1, 3)):  # each pair = one debit + one credit
        sender, receiver = rng.sample(list(COST_CENTERS), 2)
        cost_element = rng.choice(COST_ELEMENTS)
        amount = random_amount(rng)
        for cost_center, value, indicator in (
            (receiver, amount, "S"),
            (sender, -amount, "H"),
        ):
            lines.append(
                {
                    "kokrs": CONTROLLING_AREA,
                    "belnr": belnr,
                    "buzei": f"{len(lines) + 1:03d}",
                    "gjahr": fiscal_year,
                    "perio": f"{posting_date.month:03d}",
                    "objnr": object_number(cost_center),
                    "kstar": cost_element,
                    "wkgbtr": str(value),
                    "twaer": CURRENCY,
                    "beknz": indicator,
                    "sgtxt": f"Reposting {sender} to {receiver}",
                }
            )
    return header, lines


def inject_error(error: str, header: Row, lines: list[Row]) -> Row | None:
    """Corrupt one document in place. Return None when the header must be dropped."""
    if error == "missing_key":
        lines[0]["buzei"] = ""
    elif error == "line_without_header":
        return None
    elif error == "unbalanced_document":
        lines[0]["wkgbtr"] = str(Decimal(str(lines[0]["wkgbtr"])) + Decimal("10.00"))
    elif error == "zero_amount":
        lines.append(dict(lines[-1], buzei=f"{len(lines) + 1:03d}", wkgbtr="0.00"))
    elif error == "unknown_cost_center":
        lines[0]["objnr"] = object_number(UNKNOWN_COST_CENTER)
    elif error == "invalid_posting_date":
        header["budat"] = date(int(header["gjahr"]) + 1, 1, 15).isoformat()
    return header


def generate(
    documents: int, error_rate: float, seed: int, fiscal_year: int
) -> tuple[list[Row], list[Row], Counter[str]]:
    """Generate all headers and line items, and count the injected errors."""
    rng = random.Random(seed)
    headers: list[Row] = []
    lines: list[Row] = []
    injected: Counter[str] = Counter()

    for doc_number in range(1, documents + 1):
        header, doc_lines = build_document(rng, doc_number, fiscal_year)
        if rng.random() < error_rate:
            error = rng.choice(ERROR_TYPES)
            injected[error] += 1
            header = inject_error(error, header, doc_lines)
        if header is not None:
            headers.append(header)
        lines.extend(doc_lines)
    return headers, lines, injected


def write_csv(path: Path, columns: list[str], rows: list[Row]) -> None:
    """Write rows to a UTF-8 CSV file with a header line."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=int, default=1000)
    parser.add_argument("--error-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fiscal-year", type=int, default=2025)
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    if args.documents < 1:
        raise SystemExit("--documents must be at least 1")
    if not 0 <= args.error_rate <= 1:
        raise SystemExit("--error-rate must be between 0 and 1")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    headers, lines, injected = generate(
        args.documents, args.error_rate, args.seed, args.fiscal_year
    )
    cost_centers: list[Row] = [
        {"kokrs": CONTROLLING_AREA, "kostl": kostl, "ktext": ktext}
        for kostl, ktext in COST_CENTERS.items()
    ]

    write_csv(args.output_dir / "csks.csv", CSKS_COLUMNS, cost_centers)
    write_csv(args.output_dir / "cobk.csv", COBK_COLUMNS, headers)
    write_csv(args.output_dir / "coep.csv", COEP_COLUMNS, lines)
    for error in ERROR_TYPES:
        logger.info("Injected %-22s %d documents", error, injected[error])


if __name__ == "__main__":
    main()
