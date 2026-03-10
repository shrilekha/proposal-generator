import os
from datetime import datetime

from flask import current_app


class LocalFileStorage:
    """
    Local disk storage backend for generated files.
    Designed as an abstraction that can later be replaced
    with Google Drive or other backends without changing business logic.
    """

    def __init__(self) -> None:
        self.base_dir = current_app.config["GENERATED_FILES_DIR"]

    def save(self, abs_path: str) -> str:
        """
        For V1 we assume docxtpl already wrote to abs_path inside base_dir.
        This method just returns the path relative to base_dir/year for metadata.
        """
        rel_path = os.path.relpath(abs_path, self.base_dir)
        return rel_path

    def build_output_path(self, proposal_customer_name: str, version_number: int) -> str:
        year_dir = datetime.utcnow().strftime("%Y")
        safe_customer = "".join(c for c in proposal_customer_name if c.isalnum() or c in (" ", "_", "-")).strip()
        safe_customer = safe_customer.replace(" ", "_")
        filename = f"{safe_customer}_v{version_number}.docx"
        target_dir = os.path.join(self.base_dir, year_dir)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, filename)

    def get_absolute_path(self, rel_path: str) -> str:
        return os.path.join(self.base_dir, rel_path)

