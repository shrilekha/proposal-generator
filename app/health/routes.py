import shutil

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from .. import db

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("/weekly-summary")
def weekly_summary():
    """
    Simple JSON endpoint that can be called by a weekly cron job
    to capture DB size and disk usage for generated files.
    """
    # Disk usage for generated_files directory
    base_dir = current_app.config["GENERATED_FILES_DIR"]
    disk_usage = shutil.disk_usage(base_dir)
    disk_usage_percent = disk_usage.used / disk_usage.total * 100

    # Database size (PostgreSQL specific; requires proper permissions)
    db_size_mb = None
    try:
        result = db.session.execute(
            text("SELECT pg_database_size(current_database()) / 1024 / 1024 AS size_mb")
        ).first()
        if result:
            db_size_mb = float(result.size_mb)
    except Exception:
        # If this fails, we still return disk usage; DB size monitoring can be configured later
        db_size_mb = None

    return jsonify(
        {
            "disk_total_bytes": disk_usage.total,
            "disk_used_bytes": disk_usage.used,
            "disk_usage_percent": disk_usage_percent,
            "disk_threshold_percent": current_app.config["DISK_USAGE_THRESHOLD_PERCENT"],
            "db_size_mb": db_size_mb,
            "db_threshold_mb": current_app.config["DB_SIZE_THRESHOLD_MB"],
        }
    )

