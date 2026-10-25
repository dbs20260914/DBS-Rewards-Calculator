import csv
import json
import os
import re
import tempfile
import time

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from tabulate import tabulate


# ============================================================
# 1. 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

JSON_FILE = DATA_DIR / "dbs_bill_rates.json"
CSV_FILE = DATA_DIR / "dbs_bill_rates.csv"

DBS_BASE_URL = (
    "https://www.dbs.com.tw/"
    "personal-zh/cards/rewards/"
)

# 三種點數各自的官方帳單折抵頁面
DBS_BILL_SOURCES = {

    "飛行積金": (
        DBS_BASE_URL + "fly_redeem_ir2"
    ),

    "活利積分": (
        DBS_BASE_URL + "bonus_redeem_ir2"
    ),

    "PChome聯名紅利點數": (
        DBS_BASE_URL + "pchome_redeem_ir2"
    )
}

POINT_TYPES = list(DBS_BILL_SOURCES.keys())

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9"
}

TIMEZONE = ZoneInfo("Asia/Taipei")


# ============================================================
# 2. 文字整理
# ============================================================

def clean_text(text):

    text = text.replace("\u00a0", " ")
    text = text.replace("\u3000", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_point_type(text):

    return (
        text.strip()
        .replace(" ", "")
        .replace("　", "")
        .replace("／", "/")
        .replace("（", "(")
        .replace("）", ")")
    )


def to_int(text):

    return int(
        text.replace(",", "").strip()
    )


# ============================================================
# 3. 下載星展銀行官方資料
# ============================================================

def fetch_official_page(session, point_type, url):

    print(f"\n正在取得：{point_type}")
    print(f"官方網址：{url}")

    try:

        response = session.get(
            url,
            timeout=20
        )

        response.raise_for_status()

        # 中文網頁編碼處理
        response.encoding = (
            response.apparent_encoding
            or response.encoding
            or "utf-8"
        )

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        # 移除不需要的內容
        for tag in soup([
            "script",
            "style",
            "noscript"
        ]):
            tag.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        text = clean_text(text)

        if "帳單折抵" not in text:
            raise ValueError(
                "網頁內容沒有出現帳單折抵資訊"
            )

        if len(text) < 300:
            raise ValueError(
                "取得的網頁內容過短"
            )

        print("✅ 官網連線成功")
        print(f"HTTP 狀態碼：{response.status_code}")

        return text

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"{point_type} 官網連線失敗：{e}"
        ) from e


# ============================================================
# 4. 尋找官方注意事項
# ============================================================

def extract_terms_section(text):

    # 優先使用官方注意事項中的「折抵方式」
    # 避免抓到 FAQ 的其他說明而混淆最低門檻

    matches = list(
        re.finditer(
            r"折抵方式\s*[：:]",
            text
        )
    )

    if not matches:
        raise ValueError(
            "找不到官方注意事項中的折抵方式"
        )

    # 通常最後一個折抵方式位於完整注意事項
    start = matches[-1].end()

    section = text[start:start + 2500]

    # 只擷取兌換比例所在的段落
    end_match = re.search(
        r"(?:\d+\s*[.、]\s*)?"
        r"最高可折抵金額為使用",
        section
    )

    if end_match:
        section = section[:end_match.start()]

    return section


# ============================================================
# 5. 解析點數兌換比例
# ============================================================

def parse_bill_rules(text):

    section = extract_terms_section(text)

    rules = []

    for point_type in POINT_TYPES:

        # 針對每個點數類型尋找完整兌換敘述
        #
        # 官網格式範例：
        # 飛行積金：每 100 點可折抵消費 NT$10，
        # 單筆最低折抵 300 點，須以 100 點為倍數。

        pattern = (
            re.escape(point_type)
            + r"\s*[：:]"
            + r"\s*每\s*([\d,]+)\s*點"
            + r"\s*可折抵(?:消費)?"
            + r"\s*(?:NT\s*\$|新臺幣|台幣)"
            + r"\s*([\d,]+)"
            + r".{0,100}?"
            + r"單筆最低折抵\s*([\d,]+)\s*點"
            + r".{0,100}?"
            + r"須以\s*([\d,]+)\s*點為倍數"
        )

        match = re.search(
            pattern,
            section,
            flags=re.IGNORECASE
        )

        if not match:
            raise ValueError(
                f"無法完整解析：{point_type}"
            )

        points_required = to_int(match.group(1))
        cash_received = to_int(match.group(2))
        minimum_points = to_int(match.group(3))
        points_increment = to_int(match.group(4))

        rule = {
            "point_type": point_type,
            "points_required": points_required,
            "cash_received": cash_received,
            "minimum_points": minimum_points,
            "points_increment": points_increment
        }

        rules.append(rule)

    return rules


# ============================================================
# 6. 解析帳單折抵限制
# ============================================================

def parse_bill_restrictions(text):

    # 尋找官網公告的帳單差額門檻
    #
    # 範例：
    # 餘額金額須大於NT$1,000以上方可折抵

    pattern = (
        r"餘額金額須大於"
        r"\s*(?:NT\s*\$|新臺幣)"
        r"\s*([\d,]+)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "無法解析帳單差額最低門檻"
        )

    minimum_difference = to_int(
        match.group(1)
    )

    # 確認最高折抵額與最低應繳額的規定
    if (
        "最低應繳金額" not in text
        or "總應繳金額" not in text
    ):
        raise ValueError(
            "找不到完整的帳單折抵限制"
        )

    return {
        "minimum_bill_difference_exclusive":
            minimum_difference,

        "maximum_offset":
            "total_due - minimum_due",

        "minimum_due_can_be_offset":
            False
    }


# ============================================================
# 7. 驗證兌換資料
# ============================================================

def validate_rules(rules):

    if len(rules) != 3:
        raise ValueError(
            "帳單折抵資料必須包含三筆規則"
        )

    seen = set()

    for rule in rules:

        point_type = rule["point_type"]

        if point_type in seen:
            raise ValueError(
                f"重複的點數類型：{point_type}"
            )

        seen.add(point_type)

        numeric_fields = [
            "points_required",
            "cash_received",
            "minimum_points",
            "points_increment"
        ]

        for field in numeric_fields:

            value = rule[field]

            if type(value) is not int or value <= 0:

                raise ValueError(
                    f"{point_type} 的 {field} 數值異常"
                )

        # 最低兌換點數必須是兌換單位倍數
        if (
            rule["minimum_points"]
            % rule["points_increment"] != 0
        ):

            raise ValueError(
                f"{point_type} 最低門檻與兌換單位不相容"
            )

        # 每一兌換單位換得的金額必須為整數
        numerator = (
            rule["points_increment"]
            * rule["cash_received"]
        )

        if numerator % rule["points_required"] != 0:

            raise ValueError(
                f"{point_type} 兌換比例不相容"
            )

    if set(POINT_TYPES) != seen:
        raise ValueError(
            "點數類型資料不完整"
        )


# ============================================================
# 8. 比較三個官方頁面的資料
# ============================================================

def compare_source_data(all_results):

    if len(all_results) != 3:
        raise ValueError(
            "官方資料來源數量不完整"
        )

    reference = all_results[0]

    reference_rules = reference["rules"]
    reference_restrictions = reference["restrictions"]

    for result in all_results[1:]:

        if result["rules"] != reference_rules:

            raise ValueError(
                "三個官方頁面的兌換規則不一致，"
                "停止更新，請人工確認"
            )

        if result["restrictions"] != reference_restrictions:

            raise ValueError(
                "三個官方頁面的帳單限制不一致，"
                "停止更新，請人工確認"
            )

    return (
        reference_rules,
        reference_restrictions
    )


# ============================================================
# 9. 讀取舊資料
# ============================================================

def load_old_data():

    if not JSON_FILE.exists():
        return None

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 10. 比較新舊資料
# ============================================================

def compare_old_new(old_data, new_data):

    if old_data is None:

        print("\n首次建立帳單折抵資料")
        return

    old_rules = {
        row["point_type"]: row
        for row in old_data.get("rules", [])
    }

    new_rules = {
        row["point_type"]: row
        for row in new_data["rules"]
    }

    print("\n正在比較新舊兌換資料...")

    changes = []

    fields = [
        "points_required",
        "cash_received",
        "minimum_points",
        "points_increment"
    ]

    for point_type in sorted(
        set(old_rules) | set(new_rules)
    ):

        old = old_rules.get(point_type)
        new = new_rules.get(point_type)

        if old is None:

            changes.append(
                f"新增點數類型：{point_type}"
            )

            continue

        if new is None:

            changes.append(
                f"移除點數類型：{point_type}"
            )

            continue

        for field in fields:

            old_value = old.get(field)
            new_value = new.get(field)

            if old_value != new_value:

                changes.append(
                    f"{point_type}\n"
                    f"  {field}："
                    f"{old_value} → {new_value}"
                )

    old_restrictions = old_data.get(
        "restrictions", {}
    )

    new_restrictions = new_data["restrictions"]

    if old_restrictions != new_restrictions:

        changes.append(
            "帳單折抵限制發生變更"
        )

    if not changes:

        print("✅ 兌換規則與上次相同")

    else:

        print(f"⚠️ 發現 {len(changes)} 項異動")

        for change in changes:
            print(change)


# ============================================================
# 11. 安全寫入文字檔案
# ============================================================

def atomic_write_text(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=path.stem + "_",
            suffix=".tmp",
            delete=False
        ) as f:

            f.write(content)
            temporary_path = Path(f.name)

        # 同一磁碟上替換，避免寫到一半損壞正式檔案
        os.replace(
            temporary_path,
            path
        )

    finally:

        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


# ============================================================
# 12. 儲存 JSON
# ============================================================

def save_json(data):

    content = json.dumps(
        data,
        ensure_ascii=False,
        indent=4
    )

    atomic_write_text(
        JSON_FILE,
        content
    )

    print(f"✅ JSON 儲存成功：{JSON_FILE}")


# ============================================================
# 13. 儲存 CSV
# ============================================================

def save_csv(rules):

    import io

    output = io.StringIO()

    fieldnames = [
        "point_type",
        "points_required",
        "cash_received",
        "minimum_points",
        "points_increment"
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(rules)

    atomic_write_text(
        CSV_FILE,
        "\ufeff" + output.getvalue()
    )

    print(f"✅ CSV 儲存成功：{CSV_FILE}")


# ============================================================
# 14. 顯示兌換規則表格
# ============================================================

def display_table(rules):

    table = []

    for rule in rules:

        points = rule["points_required"]
        cash = rule["cash_received"]

        minimum = rule["minimum_points"]
        increment = rule["points_increment"]

        minimum_cash = (
            minimum * cash
        ) // points

        table.append([
            rule["point_type"],
            f"{points:,} 點 = NT${cash:,}",
            f"{minimum:,}",
            f"{increment:,}",
            f"NT${minimum_cash:,}"
        ])

    print("\n" + "=" * 65)
    print("星展銀行信用卡帳單折抵規則")
    print("=" * 65)

    print(
        tabulate(
            table,
            headers=[
                "點數類型",
                "兌換比例",
                "最低點數",
                "兌換單位",
                "最低折抵金額"
            ],
            tablefmt="grid",
            stralign="center"
        )
    )


# ============================================================
# 15. 主程式
# ============================================================

def main():

    print("=" * 65)
    print("星展銀行信用卡帳單折抵資料爬蟲")
    print("=" * 65)

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_results = []

    try:

        with requests.Session() as session:

            session.headers.update(HEADERS)

            # 依序讀取三個官方頁面
            for point_type, url in DBS_BILL_SOURCES.items():

                text = fetch_official_page(
                    session,
                    point_type,
                    url
                )

                rules = parse_bill_rules(text)

                restrictions = parse_bill_restrictions(text)

                validate_rules(rules)

                all_results.append({
                    "source": url,
                    "rules": rules,
                    "restrictions": restrictions
                })

                print(
                    f"✅ 成功解析 {len(rules)} 筆兌換規則"
                )

                # 避免短時間內密集請求
                time.sleep(1)

        # 三個頁面交叉比對
        rules, restrictions = compare_source_data(
            all_results
        )

        validate_rules(rules)

        print("\n✅ 三個官方頁面的資料一致")

        # 建立正式資料
        fetched_at = datetime.now(
            TIMEZONE
        ).strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "bank": "星展銀行",
            "reward_type": "帳單折抵",
            "fetched_at": fetched_at,
            "sources": DBS_BILL_SOURCES,
            "rules": rules,
            "restrictions": restrictions
        }

        # 讀取原始資料並比較
        old_data = load_old_data()

        compare_old_new(
            old_data,
            data
        )

        # 顯示表格
        display_table(rules)

        print("\n帳單折抵限制：")

        print(
            "帳單差額必須大於："
            f'NT${restrictions["minimum_bill_difference_exclusive"]:,}'
        )

        print(
            "最高折抵金額："
            "當期帳單總應繳－最低應繳金額"
        )

        print(
            "最低應繳金額不得使用點數折抵"
        )

        print("\n資料抓取時間：", fetched_at)

        # 完整驗證後才更新檔案
        save_csv(rules)
        save_json(data)

        print("\n" + "=" * 65)
        print("✅ 帳單折抵資料更新完成")
        print("=" * 65)

    except (
        requests.exceptions.RequestException,
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        json.JSONDecodeError
    ) as e:

        print("\n" + "=" * 65)
        print("❌ 帳單折抵資料取得或解析失敗")
        print("=" * 65)

        print(f"錯誤原因：{e}")

        print(
            "\n本次未執行完整更新。"
            "\n若已有 JSON 資料，請保留原檔並人工核對。"
        )

        raise SystemExit(1)


# ============================================================
# 16. 啟動程式
# ============================================================

if __name__ == "__main__":
    main()