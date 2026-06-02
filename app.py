"""
Uniec3 Downgrade 3.4 → 3.3 — Flask app.

GET  /          → uploadpagina
POST /convert   → verwerk bestand → download direct
"""

import io
import os
import re

from flask import Flask, render_template, request, send_file, jsonify

from downgrade import downgrade_bytes

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    f = request.files.get("bestand")
    if not f or not f.filename.lower().endswith(".uniec3"):
        return jsonify(error="Geen geldig .uniec3 bestand."), 400

    try:
        input_bytes = f.read()
        output_bytes = downgrade_bytes(input_bytes)
    except Exception as e:
        return jsonify(error=f"Verwerking mislukt: {e}"), 500

    # Bestandsnaam: origineel zonder extensie + _v33 + .uniec3
    base = re.sub(r"\.uniec3$", "", f.filename, flags=re.IGNORECASE)
    download_name = f"{base}_v33.uniec3"

    return send_file(
        io.BytesIO(output_bytes),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=download_name,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
