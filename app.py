from __future__ import annotations

import os
import threading
import time
import urllib.request
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from contract_generator import (
    generate_contract,
    generate_contract_archive,
    generate_store_proof,
    generate_store_proof_archive,
    normalize_row,
    normalize_store_proof_row,
    parse_csv_rows,
    parse_csv_store_proof_rows,
    parse_xlsx_rows,
    parse_xlsx_store_proof_rows,
)


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "resource" / "奇点电商平台产品服务合同模板.docx"
STORE_PROOF_TEMPLATE_PATH = BASE_DIR / "resource" / "奇点电商平台店铺经营证明模板.docx"
OUTPUT_DIR = BASE_DIR / "output"

app = Flask(__name__)
JOBS: dict[str, dict[str, object]] = {}
JOBS_LOCK = threading.Lock()


@app.after_request
def disable_static_cache(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/import")
def import_rows():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "请选择 CSV 或 Excel 文件"}), 400

    filename = uploaded.filename.lower()
    if filename.endswith(".csv"):
        rows = parse_csv_rows(uploaded.stream)
    elif filename.endswith(".xlsx"):
        rows = parse_xlsx_rows(uploaded.stream)
    else:
        return jsonify({"error": "仅支持 .csv 和 .xlsx 文件"}), 400
    return jsonify({"rows": rows})


@app.post("/api/store-proof/import")
def import_store_proof_rows():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "请选择 CSV 或 Excel 文件"}), 400

    filename = uploaded.filename.lower()
    if filename.endswith(".csv"):
        rows = parse_csv_store_proof_rows(uploaded.stream)
    elif filename.endswith(".xlsx"):
        rows = parse_xlsx_store_proof_rows(uploaded.stream)
    else:
        return jsonify({"error": "仅支持 .csv 和 .xlsx 文件"}), 400
    return jsonify({"rows": rows})


@app.post("/api/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    raw_rows = payload.get("rows") or []
    normalized = []
    errors = []

    for index, raw_row in enumerate(raw_rows, start=1):
        try:
            normalized.append(normalize_row(raw_row))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})

    if errors:
        return jsonify({"errors": errors}), 400
    if not normalized:
        return jsonify({"errors": [{"row": 0, "error": "请至少添加一行合同数据"}]}), 400

    job_id = uuid.uuid4().hex
    _set_job(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "total": len(normalized),
            "current_index": 1,
            "total_percent": 0,
            "current_percent": 0,
            "message": "准备生成合同",
            "download_url": "",
            "error": "",
        },
    )
    thread = threading.Thread(target=_run_generation_job, args=(job_id, normalized, "contract"), daemon=True)
    thread.start()
    return jsonify(_public_job(job_id))


@app.post("/api/store-proof/generate")
def generate_store_proof_route():
    payload = request.get_json(silent=True) or {}
    raw_rows = payload.get("rows") or []
    normalized = []
    errors = []

    for index, raw_row in enumerate(raw_rows, start=1):
        try:
            normalized.append(normalize_store_proof_row(raw_row))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})

    if errors:
        return jsonify({"errors": errors}), 400
    if not normalized:
        return jsonify({"errors": [{"row": 0, "error": "请至少添加一行经营证明数据"}]}), 400

    job_id = uuid.uuid4().hex
    _set_job(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "total": len(normalized),
            "current_index": 1,
            "total_percent": 0,
            "current_percent": 0,
            "message": "准备生成经营证明",
            "download_url": "",
            "error": "",
        },
    )
    thread = threading.Thread(target=_run_generation_job, args=(job_id, normalized, "store_proof"), daemon=True)
    thread.start()
    return jsonify(_public_job(job_id))


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    job = _public_job(job_id)
    if not job:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(job)


@app.get("/api/jobs/<job_id>/download")
def job_download(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "任务不存在"}), 404
        if job.get("status") != "complete":
            return jsonify({"error": "任务尚未完成"}), 409
        output_path = Path(str(job["output_path"]))
        filename = str(job["filename"])

    mimetype = "application/zip" if output_path.suffix.lower() == ".zip" else None
    return send_file(output_path, mimetype=mimetype, as_attachment=True, download_name=filename)


def _safe_download_name(value: str) -> str:
    return "".join("_" if char in '\\/:*?"<>|' else char for char in value).strip() or "contract"


def _run_generation_job(job_id: str, rows, kind: str) -> None:
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        total = len(rows)
        if kind == "contract" and total == 1:
            output_path = OUTPUT_DIR / f"{_safe_download_name(rows[0].party_a)}-{stamp}.docx"

            def on_progress(percent: int, message: str) -> None:
                _set_job(
                    job_id,
                    {
                        "current_index": 1,
                        "current_percent": percent,
                        "total_percent": percent,
                        "message": message,
                    },
                )

            generate_contract(TEMPLATE_PATH, output_path, rows[0], progress=on_progress)
        elif kind == "contract":
            output_path = OUTPUT_DIR / f"contracts-{stamp}.zip"

            def on_archive_progress(row_index: int, current_percent: int, message: str) -> None:
                total_percent = int((((row_index - 1) + current_percent / 100) / total) * 100)
                _set_job(
                    job_id,
                    {
                        "current_index": row_index,
                        "current_percent": current_percent,
                        "total_percent": total_percent,
                        "message": message,
                    },
                )

            generate_contract_archive(TEMPLATE_PATH, output_path, rows, progress=on_archive_progress)
        elif total == 1:
            output_path = OUTPUT_DIR / f"{_safe_download_name(rows[0].enterprise_name)}-店铺经营证明-{stamp}.docx"

            def on_store_proof_progress(percent: int, message: str) -> None:
                _set_job(
                    job_id,
                    {
                        "current_index": 1,
                        "current_percent": percent,
                        "total_percent": percent,
                        "message": message,
                    },
                )

            generate_store_proof(STORE_PROOF_TEMPLATE_PATH, output_path, rows[0], progress=on_store_proof_progress)
        else:
            output_path = OUTPUT_DIR / f"store-proofs-{stamp}.zip"

            def on_store_proof_archive_progress(row_index: int, current_percent: int, message: str) -> None:
                total_percent = int((((row_index - 1) + current_percent / 100) / total) * 100)
                _set_job(
                    job_id,
                    {
                        "current_index": row_index,
                        "current_percent": current_percent,
                        "total_percent": total_percent,
                        "message": message,
                    },
                )

            generate_store_proof_archive(
                STORE_PROOF_TEMPLATE_PATH,
                output_path,
                rows,
                progress=on_store_proof_archive_progress,
            )

        _set_job(
            job_id,
            {
                "status": "complete",
                "current_index": total,
                "current_percent": 100,
                "total_percent": 100,
                "message": "生成完成",
                "download_url": f"/api/jobs/{job_id}/download",
                "output_path": str(output_path),
                "filename": output_path.name,
            },
        )
    except Exception as exc:
        _set_job(
            job_id,
            {
                "status": "error",
                "message": "生成失败",
                "error": str(exc),
            },
        )


def _set_job(job_id: str, values: dict[str, object]) -> None:
    with JOBS_LOCK:
        current = JOBS.get(job_id, {})
        current.update(values)
        JOBS[job_id] = current


def _public_job(job_id: str) -> dict[str, object]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return {}
        return {
            key: value
            for key, value in job.items()
            if key not in {"output_path", "filename"}
        }


def _open_browser_when_ready(url: str) -> None:
    def worker() -> None:
        for _ in range(40):
            try:
                with urllib.request.urlopen(url, timeout=1):
                    webbrowser.open(url)
                    return
            except Exception:
                time.sleep(0.5)
        webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "6001"))
    if os.environ.get("OPEN_BROWSER") == "1":
        _open_browser_when_ready(f"http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
