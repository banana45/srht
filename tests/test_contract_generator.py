from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from contract_generator import (
    ContractRow,
    StoreProofRow,
    format_chinese_date,
    generate_contract_archive,
    generate_contract,
    generate_store_proof,
    generate_store_proof_archive,
    normalize_row,
    normalize_store_proof_row,
    parse_csv_rows,
    parse_csv_store_proof_rows,
    parse_xlsx_rows,
    parse_xlsx_store_proof_rows,
)


def document_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return xml


def visible_document_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    root = __import__("xml.etree.ElementTree").etree.ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return "".join(text.text or "" for text in root.findall(".//w:t", namespace))


def contract_term_paragraph_xml(path: Path) -> str:
    xml = document_text(path)
    import re

    for match in re.finditer(r"<w:p[\s\S]*?</w:p>", xml):
        paragraph = match.group(0)
        if "合同履行期限自" in paragraph:
            return paragraph
    raise AssertionError("contract term paragraph not found")


def paragraphs_containing(path: Path, needle: str) -> list[str]:
    xml = document_text(path)
    import re

    return [match.group(0) for match in re.finditer(r"<w:p[\s\S]*?</w:p>", xml) if needle in match.group(0)]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-7-1", "2026年7月1日"),
        ("2026/07/01", "2026年7月1日"),
        ("2026年7月1日", "2026年7月1日"),
    ],
)
def test_format_chinese_date_accepts_common_formats(raw, expected):
    assert format_chinese_date(raw) == expected


def test_format_chinese_date_rejects_invalid_dates():
    with pytest.raises(ValueError, match="日期格式"):
        format_chinese_date("2026.07.01")


def test_normalize_row_allows_blank_signing_date():
    row = normalize_row(
        {
            "party_a": "杭州测试科技有限公司",
            "start_date": "2026-7-1",
            "end_date": "2027-7-1",
            "signing_date": "",
        }
    )

    assert row == ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="",
    )


def test_parse_csv_rows_reads_header_aliases():
    csv_bytes = "甲方名称,开始日期,结束日期,签署日期\n杭州测试科技有限公司,2026-7-1,2027-7-1,\n".encode(
        "utf-8-sig"
    )

    rows = parse_csv_rows(BytesIO(csv_bytes))

    assert rows == [
        {
            "party_a": "杭州测试科技有限公司",
            "start_date": "2026-7-1",
            "end_date": "2027-7-1",
            "signing_date": "",
        }
    ]


def test_parse_xlsx_rows_reads_header_aliases():
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["甲方名称", "开始日期", "结束日期", "签署日期"])
    sheet.append(["杭州测试科技有限公司", "2026-7-1", "2027-7-1", None])
    data = BytesIO()
    workbook.save(data)
    data.seek(0)

    rows = parse_xlsx_rows(data)

    assert rows == [
        {
            "party_a": "杭州测试科技有限公司",
            "start_date": "2026-7-1",
            "end_date": "2027-7-1",
            "signing_date": "",
        }
    ]


def test_generate_contract_fills_party_and_term(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="2026年7月2日",
    )

    generate_contract(template, output, row)

    xml = document_text(output)
    assert "杭州测试科技有限公司" in xml
    assert "2026年7月1日" in xml
    assert "2027年7月1日" in xml
    assert "2026年7月2日" in xml


def test_generate_contract_replaces_entire_contract_term_blanks(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="",
    )

    generate_contract(template, output, row)

    text = visible_document_text(output)
    assert "合同履行期限自 2026年7月1日  至 2027年7月1日，" in text
    assert "_______2027年7月1日" not in text


def test_generate_contract_preserves_word_namespace_prefixes(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="",
    )

    generate_contract(template, output, row)

    xml = document_text(output)
    assert "xmlns:w14=" in xml
    assert "w14:paraId=" in xml
    assert "xmlns:ns" not in xml[:1500]


def test_generate_contract_removes_underlines_from_filled_contract_term(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="",
    )

    generate_contract(template, output, row)

    paragraph = contract_term_paragraph_xml(output)
    assert "2026年7月1日" in paragraph
    assert "2027年7月1日" in paragraph
    assert "<w:u" not in paragraph


def test_generate_contract_fills_all_signing_date_slots(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="2026年7月2日",
    )

    generate_contract(template, output, row)

    text = visible_document_text(output)
    assert text.count("日期：2026年7月2日") == 3


def test_generate_contract_removes_underlines_from_all_filled_signature_slots(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="2026年7月2日",
    )

    generate_contract(template, output, row)

    for paragraph in paragraphs_containing(output, "杭州测试科技有限公司"):
        assert "<w:u" not in paragraph
    for paragraph in paragraphs_containing(output, "2026年7月2日"):
        assert "<w:u" not in paragraph


def test_generate_contract_keeps_signing_date_blank_when_omitted(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contract.docx"
    row = ContractRow(
        party_a="杭州测试科技有限公司",
        start_date="2026年7月1日",
        end_date="2027年7月1日",
        signing_date="",
    )

    generate_contract(template, output, row)

    text = visible_document_text(output)
    assert "杭州测试科技有限公司" in text
    assert "日期：_______________" in text


def test_generate_contract_archive_creates_zip_for_multiple_rows(tmp_path):
    template = Path("resource/奇点电商平台产品服务合同模板.docx")
    output = tmp_path / "contracts.zip"
    rows = [
        ContractRow("杭州测试科技有限公司", "2026年7月1日", "2027年7月1日", ""),
        ContractRow("上海样例网络有限公司", "2026年8月1日", "2027年8月1日", "2026年8月2日"),
    ]

    generate_contract_archive(template, output, rows)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    assert len(names) == 2
    assert names[0].endswith(".docx")
    assert names[1].endswith(".docx")


def test_normalize_store_proof_row_formats_time():
    row = normalize_store_proof_row(
        {
            "enterprise_name": "杭州测试科技有限公司",
            "business_license": "91330000TEST000001",
            "account_name": "测试旗舰店",
            "shop_url": "https://example.com/shop",
            "proof_date": "2026-7-19",
        }
    )

    assert row == StoreProofRow(
        enterprise_name="杭州测试科技有限公司",
        business_license="91330000TEST000001",
        account_name="测试旗舰店",
        shop_url="https://example.com/shop",
        proof_date="2026年7月19日",
    )


def test_parse_store_proof_csv_rows_reads_header_aliases():
    csv_bytes = "企业名,营业执照,账户名称,店铺地址,时间\n杭州测试科技有限公司,91330000TEST000001,测试旗舰店,https://example.com/shop,2026-7-19\n".encode(
        "utf-8-sig"
    )

    rows = parse_csv_store_proof_rows(BytesIO(csv_bytes))

    assert rows == [
        {
            "enterprise_name": "杭州测试科技有限公司",
            "business_license": "91330000TEST000001",
            "account_name": "测试旗舰店",
            "shop_url": "https://example.com/shop",
            "proof_date": "2026-7-19",
        }
    ]


def test_parse_store_proof_xlsx_rows_reads_header_aliases():
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["企业名", "营业执照", "账户名称", "店铺地址", "时间"])
    sheet.append(["杭州测试科技有限公司", "91330000TEST000001", "测试旗舰店", "https://example.com/shop", "2026-7-19"])
    data = BytesIO()
    workbook.save(data)
    data.seek(0)

    rows = parse_xlsx_store_proof_rows(data)

    assert rows == [
        {
            "enterprise_name": "杭州测试科技有限公司",
            "business_license": "91330000TEST000001",
            "account_name": "测试旗舰店",
            "shop_url": "https://example.com/shop",
            "proof_date": "2026-7-19",
        }
    ]


def test_generate_store_proof_replaces_template_values(tmp_path):
    template = Path("resource/奇点电商平台店铺经营证明模板.docx")
    output = tmp_path / "proof.docx"
    row = StoreProofRow(
        enterprise_name="杭州测试科技有限公司",
        business_license="91330000TEST000001",
        account_name="测试旗舰店",
        shop_url="https://example.com/shop",
        proof_date="2026年7月19日",
    )

    generate_store_proof(template, output, row)

    text = visible_document_text(output)
    assert "杭州测试科技有限公司" in text
    assert "91330000TEST000001" in text
    assert "测试旗舰店" in text
    assert "https://example.com/shop" in text
    assert "2026年7月19日" in text
    assert "厦门淑莱汝信息科技有限公司" not in text
    assert "91350206MAKGH6NDXJ" not in text
    assert "厦门淑莱汝网络设计" not in text
    assert "https://xmslr.qidian.hzshengruikj.cn/" not in text


def test_generate_store_proof_archive_creates_zip_for_multiple_rows(tmp_path):
    template = Path("resource/奇点电商平台店铺经营证明模板.docx")
    output = tmp_path / "proofs.zip"
    rows = [
        StoreProofRow("杭州测试科技有限公司", "91330000TEST000001", "测试旗舰店", "https://example.com/a", "2026年7月19日"),
        StoreProofRow("上海样例网络有限公司", "91310000TEST000002", "样例店铺", "https://example.com/b", "2026年7月20日"),
    ]

    generate_store_proof_archive(template, output, rows)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    assert len(names) == 2
    assert names[0].endswith(".docx")
    assert names[1].endswith(".docx")
