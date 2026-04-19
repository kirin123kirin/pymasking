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


def create_app() -> Flask:
    logging.getLogger("werkzeug").addFilter(_NoHeartbeatFilter())

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    threading.Thread(target=_watchdog, daemon=True, name="heartbeat-watchdog").start()

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
        if mode not in ("blackout", "unique", "pigpen"):
            return jsonify({"error": "不正な mode"}), 400

        from pymasking.core.masker import mask_text
        result = mask_text(text, mode)
        return jsonify({"result": result})

    @app.route("/api/unmask/text", methods=["POST"])
    def api_unmask_text():
        data = request.get_json(force=True)
        text = data.get("text", "")
        from pymasking.core.masker import unmask_text
        result = unmask_text(text)
        return jsonify({"result": result})

    @app.route("/api/mask/file", methods=["POST"])
    def api_mask_file():
        if "file" not in request.files:
            return jsonify({"error": "ファイルが見つかりません"}), 400

        f = request.files["file"]
        mode = request.form.get("mode", "blackout")
        if mode not in ("blackout", "unique", "pigpen"):
            return jsonify({"error": "不正な mode"}), 400

        filename = Path(f.filename).name if f.filename else ""
        ext = Path(filename).suffix.lower()
        if not filename or ext not in _ALLOWED_EXTS:
            return jsonify({"error": f"未対応の形式: {ext}"}), 400

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / filename
            f.save(src)

            from pymasking.core.extractor import process_file
            try:
                out = process_file(src, mode)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

            return send_file(
                io.BytesIO(out.read_bytes()),
                as_attachment=True,
                download_name=out.name,
                mimetype="application/octet-stream",
            )

    @app.route("/api/mask/image", methods=["POST"])
    def api_mask_image():
        """クリップボード画像（base64 または multipart）のマスキング。"""
        if "file" in request.files:
            f = request.files["file"]
            from PIL import Image
            img = Image.open(f.stream)
        else:
            data = request.get_json(force=True)
            b64 = data.get("image_base64", "")
            if not b64:
                return jsonify({"error": "画像データがありません"}), 400
            import base64
            from PIL import Image
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw))

        from pymasking.core.extractor.image import process_image_data
        try:
            masked = process_image_data(img)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        buf = io.BytesIO()
        masked.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png", download_name="masked.png", as_attachment=True)

    return app
