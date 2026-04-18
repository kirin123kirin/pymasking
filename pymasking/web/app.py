"""Flask Web アプリケーション。"""

import io
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file


_ALLOWED_EXTS = {
    ".txt", ".csv", ".json", ".xml", ".md", ".log",
    ".docx", ".xlsx", ".pptx",
    ".jpg", ".jpeg", ".png", ".pdf",
}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    @app.route("/")
    def index():
        return render_template("index.html")

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

        ext = Path(f.filename).suffix.lower() if f.filename else ""
        if ext not in _ALLOWED_EXTS:
            return jsonify({"error": f"未対応の形式: {ext}"}), 400

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / f.filename
            f.save(src)

            from pymasking.core.extractor import process_file
            out = process_file(src, mode)

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
        masked = process_image_data(img)

        buf = io.BytesIO()
        masked.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png", download_name="masked.png", as_attachment=True)

    return app
