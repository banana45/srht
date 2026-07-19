from io import BytesIO
import time

from app import app


def test_import_csv_returns_rows():
    client = app.test_client()
    csv_data = "甲方名称,开始日期,结束日期,签署日期\n杭州测试科技有限公司,2026-7-1,2027-7-1,\n".encode(
        "utf-8-sig"
    )

    response = client.post(
        "/api/import",
        data={"file": (BytesIO(csv_data), "contracts.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json["rows"][0]["party_a"] == "杭州测试科技有限公司"


def test_import_store_proof_csv_returns_rows():
    client = app.test_client()
    csv_data = "企业名,营业执照,账户名称,店铺地址,时间\n杭州测试科技有限公司,91330000TEST000001,测试旗舰店,https://example.com/shop,2026-7-19\n".encode(
        "utf-8-sig"
    )

    response = client.post(
        "/api/store-proof/import",
        data={"file": (BytesIO(csv_data), "proofs.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json["rows"][0]["enterprise_name"] == "杭州测试科技有限公司"


def test_generate_rejects_invalid_rows():
    client = app.test_client()

    response = client.post(
        "/api/generate",
        json={"rows": [{"party_a": "", "start_date": "2026-7-1", "end_date": "2027-7-1"}]},
    )

    assert response.status_code == 400
    assert "甲方名称不能为空" in response.json["errors"][0]["error"]


def test_static_assets_are_not_cached():
    client = app.test_client()

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]


def test_generate_returns_job_and_download_for_valid_rows():
    client = app.test_client()

    response = client.post(
        "/api/generate",
        json={
            "rows": [
                {
                    "party_a": "杭州测试科技有限公司",
                    "start_date": "2026-7-1",
                    "end_date": "2027-7-1",
                    "signing_date": "",
                },
                {
                    "party_a": "上海样例网络有限公司",
                    "start_date": "2026/8/1",
                    "end_date": "2027/8/1",
                    "signing_date": "2026/8/2",
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json["job_id"]
    assert response.json["status"] == "running"

    job_id = response.json["job_id"]
    status = None
    for _ in range(30):
        status_response = client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200
        status = status_response.json
        assert "total_percent" in status
        assert "current_percent" in status
        if status["status"] == "complete":
            break
        time.sleep(0.1)

    assert status["status"] == "complete"
    assert status["total_percent"] == 100
    assert status["current_percent"] == 100

    download = client.get(f"/api/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.mimetype == "application/zip"


def test_store_proof_generate_returns_job_and_download_for_valid_rows():
    client = app.test_client()

    response = client.post(
        "/api/store-proof/generate",
        json={
            "rows": [
                {
                    "enterprise_name": "杭州测试科技有限公司",
                    "business_license": "91330000TEST000001",
                    "account_name": "测试旗舰店",
                    "shop_url": "https://example.com/shop",
                    "proof_date": "2026-7-19",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json["job_id"]
    assert response.json["status"] == "running"

    job_id = response.json["job_id"]
    status = None
    for _ in range(30):
        status_response = client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200
        status = status_response.json
        if status["status"] == "complete":
            break
        time.sleep(0.1)

    assert status["status"] == "complete"
    assert status["total_percent"] == 100

    download = client.get(f"/api/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
