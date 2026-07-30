"""Package Lambda MCP tools into zip archives for manual upload or CI deploys."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
SHARED = ROOT / "shared_lambda"
PAGE_KNOWLEDGE = ROOT / "page_knowledge"
FUNCTIONS = {
    "list_services": ROOT / "list_services" / "handler.py",
    "get_service_schema": ROOT / "get_service_schema" / "handler.py",
    "submit_service_request": ROOT / "submit_service_request" / "handler.py",
    "get_page_context": ROOT / "get_page_context" / "handler.py",
    "search_pages": ROOT / "search_pages" / "handler.py",
    "recommend_products_by_health_need": ROOT / "recommend_products_by_health_need" / "handler.py",
    "get_product_nutrition": ROOT / "get_product_nutrition" / "handler.py",
}


def build_zip(name: str, handler_path: Path) -> Path:
    DIST.mkdir(exist_ok=True)
    zip_path = DIST / f"{name}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(handler_path, arcname="handler.py")
        for path in SHARED.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(ROOT)))
        for path in PAGE_KNOWLEDGE.rglob("*"):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(ROOT)))
    return zip_path


def main() -> None:
    built = [build_zip(name, handler_path) for name, handler_path in FUNCTIONS.items()]
    print("Built Lambda bundles:")
    for zip_path in built:
        print(f"- {zip_path}")


if __name__ == "__main__":
    main()
