import requests
import re
import json
import csv
import unicodedata

from pathlib import Path
from datetime import datetime
from tabulate import tabulate
from bs4 import BeautifulSoup


# ==================================================
# 1. 基本設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

DBS_CASH_URL = (
    "https://www.dbs.com.tw/personal-zh/"
    "cards/rewards/cash-redeem-creditcard-cash-back"
)


POINT_TYPES = {
    "飛行積金": "飛行積金",
    "活利積分": "活利積分",
    "現金積點/現金紅利": "現金積點／現金紅利",
    "PChome聯名紅利點數": "PChome聯名紅利點數"
}


# ==================================================
# 2. 官網資料爬取
# ==================================================

def fetch_cash_data():

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        DBS_CASH_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.content,
        "lxml"
    )

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(
        separator=" ",
        strip=True
    )

    if not text:
        raise ValueError("官網回傳內容為空")

    return text


# ==================================================
# 3. 文字標準化
# ==================================================

def normalize_text(text):

    text = unicodedata.normalize("NFKC", text)

    text = text.replace("／", "/")
    text = text.replace("：", ":")
    text = text.replace("；", ";")

    text = re.sub(r"\s+", "", text)

    return text


# ==================================================
# 4. 取得刷卡金規則區域
# ==================================================

def get_cash_section(text):

    marker = "兌換刷卡金注意事項"

    if marker not in text:
        raise ValueError("找不到刷卡金兌換注意事項")

    section = text.split(marker, 1)[1]

    # 從注意事項的飛行積金規則開始
    start_marker = "飛行積金:"

    start = section.find(start_marker)

    if start == -1:
        raise ValueError("找不到飛行積金刷卡金規則")

    section = section[start:]

    # 結束於後續其他注意事項
    end_markers = [
        "持卡人若有以下任一情事",
        "本行將於兌換後",
        "紅利點數一經兌換"
    ]

    ends = [
        section.find(marker)
        for marker in end_markers
        if section.find(marker) != -1
    ]

    if ends:
        section = section[:min(ends)]

    return section


# ==================================================
# 5. 解析刷卡金比例
# ==================================================

def extract_cash_rules(text):

    text = normalize_text(text)

    section = get_cash_section(text)

    results = []

    for official_name, point_type in POINT_TYPES.items():

        # 擷取對應點數類型的規則
        pattern = (
            re.escape(official_name)
            + r":每([\d,]+)點"
            + r"[^;]*?"
            + r"可兌換刷卡金NT\$([\d,]+)"
            + r"[^;]*?"
            + r"單筆最低兌換([\d,]+)點"
            + r"[^;]*?"
            + r"須以([\d,]+)點為倍數"
        )

        match = re.search(
            pattern,
            section
        )

        if not match:

            raise ValueError(
                f"無法解析刷卡金規則：{point_type}"
            )

        points_required = int(
            match.group(1).replace(",", "")
        )

        cash_received = int(
            match.group(2).replace(",", "")
        )

        minimum_points = int(
            match.group(3).replace(",", "")
        )

        points_increment = int(
            match.group(4).replace(",", "")
        )

        values = [
            points_required,
            cash_received,
            minimum_points,
            points_increment
        ]

        if any(value <= 0 for value in values):

            raise ValueError(
                f"發現不合理數值：{point_type}"
            )

        # 驗證最低點數與兌換單位
        if minimum_points % points_increment != 0:

            raise ValueError(
                f"最低兌換點數不符合兌換單位：{point_type}"
            )

        if points_increment % points_required != 0:

            raise ValueError(
                f"兌換單位與比例無法整數對應：{point_type}"
            )

        results.append({

            "point_type": point_type,

            "points_required": points_required,

            "cash_received": cash_received,

            "minimum_points": minimum_points,

            "points_increment": points_increment

        })

    # ==================================================
    # 6. 資料驗證
    # ==================================================

    actual_types = {
        row["point_type"]
        for row in results
    }

    expected_types = set(POINT_TYPES.values())

    if actual_types != expected_types:

        raise ValueError(
            "刷卡金兌換資料不完整"
        )

    if len(results) != len(POINT_TYPES):

        raise ValueError(
            "刷卡金兌換資料筆數異常"
        )

    return results


# ==================================================
# 7. 顯示表格
# ==================================================

def display_cash_table(results):

    rows = []

    for row in results:

        rows.append([

            row["point_type"],

            f'{row["points_required"]:,}',

            f'NT${row["cash_received"]:,}',

            f'{row["minimum_points"]:,}',

            f'{row["points_increment"]:,}'

        ])

    headers = [
        "點數類型",
        "所需點數",
        "可換刷卡金",
        "最低點數",
        "兌換單位"
    ]

    print("\n星展銀行刷卡金兌換比例\n")

    print(
        tabulate(
            rows,
            headers=headers,
            tablefmt="simple",
            stralign="left"
        )
    )


# ==================================================
# 8. 儲存資料
# ==================================================

def save_cash_data(results):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fetch_time = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    payload = {

        "bank": "星展銀行",

        "reward_type": "cash",

        "source": DBS_CASH_URL,

        "fetched_at": fetch_time,

        "rules": results

    }

    json_path = DATA_DIR / "dbs_cash_rates.json"

    csv_path = DATA_DIR / "dbs_cash_rates.csv"

    temp_json = DATA_DIR / "dbs_cash_rates.tmp.json"

    temp_csv = DATA_DIR / "dbs_cash_rates.tmp.csv"

    with open(
        temp_json,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=4
        )

    with open(
        temp_csv,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "point_type",
                "points_required",
                "cash_received",
                "minimum_points",
                "points_increment"
            ]
        )

        writer.writeheader()
        writer.writerows(results)

    temp_json.replace(json_path)
    temp_csv.replace(csv_path)

    print("\n✅ 刷卡金資料儲存成功")
    print(f"JSON：{json_path}")
    print(f"CSV：{csv_path}")


# ==================================================
# 9. 主程式
# ==================================================

def main():

    print("=" * 55)
    print("星展銀行刷卡金兌換資料爬蟲")
    print("=" * 55)

    try:

        print("\n正在取得星展銀行官方資料...")

        text = fetch_cash_data()

        print("✅ 官網連線成功")

        print("正在解析刷卡金規則...")

        results = extract_cash_rules(text)

        print("✅ 刷卡金規則解析成功")

        print(f"共取得 {len(results)} 種點數類型")

        display_cash_table(results)

        save_cash_data(results)

    except (
        requests.RequestException,
        ValueError,
        OSError
    ) as e:

        print("\n❌ 刷卡金資料取得或解析失敗")

        print(f"錯誤原因：{e}")

        print("本次不更新資料。")


if __name__ == "__main__":
    main()