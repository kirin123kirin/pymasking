"""Flask Web アプリケーション。"""

import io
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

# ── ブラウザ閉じ検知：ハートビートウォッチドッグ ──────────────────
_heartbeat_lock = threading.Lock()
_last_heartbeat: float = 0.0
_heartbeat_active: bool = False
_HEARTBEAT_TIMEOUT = 15


def _watchdog() -> None:
    while True:
        time.sleep(5)
        with _heartbeat_lock:
            active = _heartbeat_active
            elapsed = time.time() - _last_heartbeat
        if active and elapsed > _HEARTBEAT_TIMEOUT:
            os._exit(0)


class _NoHeartbeatFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/heartbeat" not in record.getMessage()


_ALLOWED_EXTS = {
    ".txt", ".csv", ".json", ".xml", ".md", ".log",
    ".docx", ".xlsx", ".pptx",
    ".jpg", ".jpeg", ".png", ".bmp", ".pdf",
}


def _preload_ocr_models() -> None:
    """Background thread: load surya OCR models from local disk at startup."""
    try:
        from pymasking.core.extractor.image import preload_models
        preload_models()
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("OCRモデルのプリロードに失敗しました (初回リクエスト時に再試行): %s", e)


def create_app() -> Flask:
    logging.getLogger("werkzeug").addFilter(_NoHeartbeatFilter())

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    threading.Thread(target=_watchdog, daemon=True, name="heartbeat-watchdog").start()
    threading.Thread(target=_preload_ocr_models, daemon=True, name="ocr-model-preload").start()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/heartbeat", methods=["POST"])
    def api_heartbeat():
        global _last_heartbeat, _heartbeat_active
        with _heartbeat_lock:
            _last_heartbeat = time.time()
            _heartbeat_active = True
        return jsonify({"ok": True})

    @app.route("/api/mask/text", methods=["POST"])
    def api_mask_text():
        data = request.get_json(force=True)
        text = data.get("text", "")
        mode = data.get("mode", "blackout")
        if mode not in ("blackout", "unique"):
            return jsonify({"error": "不正な mode"}), 400

        cats = data.get("categories")
        categories = set(cats) if cats else None

        from pymasking.core.masker import mask_text
        result = mask_text(text, mode, categories=categories)
        return jsonify({"result": result})

    @app.route("/api/mask/file", methods=["POST"])
    def api_mask_file():
        if "file" not in request.files:
            return jsonify({"error": "ファイルが見つかりません"}), 400

        f = request.files["file"]
        mode = request.form.get("mode", "blackout")
        if mode not in ("blackout", "unique"):
            return jsonify({"error": "不正な mode"}), 400

        cats_str = request.form.get("categories", "").strip()
        categories = set(cats_str.split(",")) if cats_str else None
        opts_str = request.form.get("options", "").strip()
        options = {k: True for k in opts_str.split(",") if k.strip()} if opts_str else {}

        filename = Path(f.filename).name if f.filename else ""
        ext = Path(filename).suffix.lower()
        if not filename or ext not in _ALLOWED_EXTS:
            return jsonify({"error": f"未対応の形式: {ext}"}), 400

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / filename
            f.save(src)

            from pymasking.core.extractor import process_file
            try:
                out = process_file(src, mode, categories=categories, options=options)
            except Exception as e:
                app.logger.exception("api_mask_file error")
                return jsonify({"error": str(e)}), 500

            return send_file(
                io.BytesIO(out.read_bytes()),
                as_attachment=True,
                download_name=out.name,
                mimetype="application/octet-stream",
            )

    return app
