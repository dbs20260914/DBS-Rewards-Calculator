import requests
import re
import csv
import json
import unicodedata

from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from tabulate import tabulate


# ============================================================
# 1. 基本設定
# ============================================================

DBS_URL = (
    "https://www.dbs.com.tw/"
    "personal-zh/cards/rewards/fly_redeem_mileage"
)

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"


# ============================================================
# 2. 點數種類設定
# ============================================================

# 左邊是官網文字標準化後的名稱
# 右邊是我們希望顯示的名稱

POINT_TYPES = {

    "飛行積金":
        "飛行積金",

    "活利積分(不含星展極耀無限卡)":
        "活利積分（一般卡）",

    "星展極耀無限卡":
        "活利積分（極耀無限卡）",

    "現金積點/現金紅利":
        "現金積點／現金紅利",

    "PChome聯名紅利點數":
        "PChome聯名紅利點數"

}


# ============================================================
# 3. 航空公司名稱對應
# ============================================================

AIRLINES = {

    "長榮無限萬哩遊":
        "長榮航空",

    "亞洲萬里通":
        "亞洲萬里通",

    "KrisFlyer":
        "新加坡航空",

    "華夏哩程酬賓計劃":
        "中華航空"

}


# ============================================================
# 4. 預期兌換組合
# ============================================================

EXPECTED_AIRLINES = {

    "飛行積金": {
        "長榮航空",
        "亞洲萬里通",
        "新加坡航空",
        "中華航空"
    },

    "活利積分（一般卡）": {
        "長榮航空",
        "亞洲萬里通",
        "中華航空"
    },

    "活利積分（極耀無限卡）": {
        "長榮航空",
        "亞洲萬里通",
        "中華航空"
    },

    "現金積點／現金紅利": {
        "長榮航空",
        "亞洲萬里通",
        "中華航空"
    },

    "PChome聯名紅利點數": {
        "長榮航空",
        "亞洲萬里通"
    }

}


# ============================================================
# 5. 爬取星展銀行官網
# ============================================================

def fetch_dbs_data():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        DBS_URL,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    # 解析 HTML
    soup = BeautifulSoup(
        response.content,
        "lxml"
    )

    # 移除不需要的標籤
    for tag in soup([
        "script",
        "style",
        "noscript"
    ]):

        tag.decompose()

    # 取得網頁文字
    text = soup.get_text(
        separator=" ",
        strip=True
    )

    if not text:
        raise ValueError(
            "官網回傳內容為空"
        )

    return text


# ============================================================
# 6. 文字標準化
# ============================================================

def normalize_text(text):

    # 全形英文、數字與標點轉半形
    text = unicodedata.normalize(
        "NFKC",
        text
    )

    # 統一斜線
    text = text.replace("／", "/")

    # 統一冒號
    text = text.replace("：", ":")

    # 統一分號
    text = text.replace("；", ";")

    # 移除所有空白與換行
    # 方便後續比對官網規則
    text = re.sub(
        r"\s+",
        "",
        text
    )

    return text


# ============================================================
# 7. 擷取兌換規則區域
# ============================================================

def get_exchange_section(text):

    marker = "兌換哩程注意事項"

    if marker not in text:

        raise ValueError(
            "找不到「兌換哩程注意事項」"
        )

    # 從注意事項開始
    section = text.split(
        marker,
        1
    )[1]

    # 找到第 3 點中的第一種點數方案
    start_marker = "飛行積金:"

    start = section.find(
        start_marker
    )

    if start == -1:

        raise ValueError(
            "找不到飛行積金兌換規則"
        )

    section = section[start:]

    # 第 4 點的開頭
    # 避免把其他注意事項納入解析
    end_marker = "兌換之點數將於申請當日"

    end = section.find(
        end_marker
    )

    if end != -1:
        section = section[:end]

    return section


# ============================================================
# 8. 將文字分成五種點數方案
# ============================================================

def split_point_types(section):

    positions = []

    for official_name, display_name in POINT_TYPES.items():

        # 點數方案標題以冒號結尾
        marker = official_name + ":"

        position = section.find(
            marker
        )

        if position == -1:

            raise ValueError(
                f"找不到點數方案：{display_name}\n"
                f"搜尋文字：{marker}"
            )

        positions.append({

            "start": position,

            "content_start": position + len(marker),

            "point_type": display_name

        })

    # 依官網出現順序排序
    positions.sort(
        key=lambda x: x["start"]
    )

    sections = {}

    for i, item in enumerate(positions):

        start = item["content_start"]

        if i + 1 < len(positions):

            end = positions[i + 1]["start"]

        else:

            end = len(section)

        content = section[start:end]

        sections[item["point_type"]] = content

    return sections


# ============================================================
# 9. 解析單筆兌換規則
# ============================================================

def parse_exchange_rule(part, point_type):

    # 官網範例：
    # 每5點活利積分可兌換1哩...
    #
    # 允許點數中間有其他文字

    ratio_pattern = (
        r"每([\d,]+)點"
        r"[^;]*?"
        r"可兌換([\d,]+)哩"
    )

    ratio_match = re.search(
        ratio_pattern,
        part
    )

    if not ratio_match:

        return []

    points = int(
        ratio_match.group(1).replace(",", "")
    )

    miles = int(
        ratio_match.group(2).replace(",", "")
    )

    # 最低兌換門檻
    minimum_match = re.search(
        r"單筆最低兌換([\d,]+)哩",
        part
    )

    # 兌換單位
    step_match = re.search(
        r"須以([\d,]+)哩為倍數",
        part
    )

    if not minimum_match:

        raise ValueError(
            f"{point_type} 找不到最低兌換門檻\n"
            f"原始內容：{part[:150]}"
        )

    if not step_match:

        raise ValueError(
            f"{point_type} 找不到兌換單位\n"
            f"原始內容：{part[:150]}"
        )

    minimum = int(
        minimum_match.group(1).replace(",", "")
    )

    step = int(
        step_match.group(1).replace(",", "")
    )

    # 基本數值檢查
    if any(
        value <= 0
        for value in [
            points,
            miles,
            minimum,
            step
        ]
    ):

        raise ValueError(
            f"發現不合理兌換數值：{point_type}"
        )

    # 只檢查航空公司名稱所在區段
    airline_text = part[
        ratio_match.end():
        minimum_match.start()
    ]

    results = []

    for official_name, airline in AIRLINES.items():

        if official_name in airline_text:

            results.append({

                "point_type": point_type,

                "airline": airline,

                "points_required": points,

                "miles_received": miles,

                "minimum_miles": minimum,

                "miles_increment": step

            })

    if not results:

        raise ValueError(
            f"{point_type} 找不到航空公司\n"
            f"原始內容：{part[:150]}"
        )

    return results


# ============================================================
# 10. 解析所有兌換規則
# ============================================================

def extract_mileage_rules(text):

    # 文字標準化
    text = normalize_text(text)

    # 擷取注意事項
    section = get_exchange_section(text)

    # 分成五種點數方案
    point_sections = split_point_types(section)

    results = []

    for point_type, content in point_sections.items():

        # 每種方案可能有多種兌換條件
        parts = content.split(";")

        for part in parts:

            part = part.strip()

            if not part:
                continue

            # 僅解析包含兌換比例的段落
            if "可兌換" not in part:
                continue

            parsed = parse_exchange_rule(
                part,
                point_type
            )

            results.extend(parsed)

    validate_results(results)

    return results


# ============================================================
# 11. 資料完整性驗證
# ============================================================

def validate_results(results):

    expected = {

        (point_type, airline)

        for point_type, airlines
        in EXPECTED_AIRLINES.items()

        for airline in airlines

    }

    actual = [

        (
            row["point_type"],
            row["airline"]
        )

        for row in results

    ]

    # 不允許重複
    if len(actual) != len(set(actual)):

        raise ValueError(
            "發現重複的兌換規則"
        )

    missing = expected - set(actual)

    extra = set(actual) - expected

    if missing or extra:

        message = [
            "兌換資料不完整"
        ]

        if missing:

            message.append(
                f"缺少：{sorted(missing)}"
            )

        if extra:

            message.append(
                f"多出：{sorted(extra)}"
            )

        raise ValueError(
            "\n".join(message)
        )

    # 驗證所有數值
    for row in results:

        for key in [
            "points_required",
            "miles_received",
            "minimum_miles",
            "miles_increment"
        ]:

            if row[key] <= 0:

                raise ValueError(
                    f"發現不合理數值：{row}"
                )

    # 固定排序，方便查看
    point_order = list(
        EXPECTED_AIRLINES.keys()
    )

    airline_order = [
        "長榮航空",
        "亞洲萬里通",
        "新加坡航空",
        "中華航空"
    ]

    results.sort(
        key=lambda row: (
            point_order.index(
                row["point_type"]
            ),
            airline_order.index(
                row["airline"]
            )
        )
    )


# ============================================================
# 12. 顯示兌換表格
# ============================================================

def display_table(results):

    rows = []

    for row in results:

        ratio = (
            f'{row["points_required"]:,}'
            f' : '
            f'{row["miles_received"]:,}'
        )

        rows.append([

            row["point_type"],

            row["airline"],

            ratio,

            f'{row["minimum_miles"]:,}',

            f'{row["miles_increment"]:,}'

        ])

    headers = [

        "點數類型",

        "航空公司",

        "點數:哩程",

        "最低哩程",

        "兌換單位"

    ]

    print("\n")
    print("=" * 65)
    print("星展銀行信用卡點數兌換哩程比例")
    print("=" * 65)

    print(
        tabulate(
            rows,
            headers=headers,
            tablefmt="grid",
            stralign="left"
        )
    )


# ============================================================
# 13. 儲存 JSON 與 CSV
# ============================================================

def save_data(results):

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

        "source": DBS_URL,

        "fetched_at": fetch_time,

        "total_rules": len(results),

        "rules": results

    }

    json_path = DATA_DIR / "dbs_rates.json"

    csv_path = DATA_DIR / "dbs_rates.csv"

    # 先準備暫存檔
    # 避免解析失敗時覆蓋既有資料
    temp_json = DATA_DIR / "dbs_rates.tmp.json"

    temp_csv = DATA_DIR / "dbs_rates.tmp.csv"

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
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "point_type",
                "airline",
                "points_required",
                "miles_received",
                "minimum_miles",
                "miles_increment"
            ]
        )

        writer.writeheader()

        writer.writerows(results)

    # 只有通過驗證才更新正式檔案
    temp_json.replace(json_path)

    temp_csv.replace(csv_path)

    print("\n✅ 兌換資料儲存成功")

    print(f"JSON：{json_path}")

    print(f"CSV：{csv_path}")


# ============================================================
# 14. 主程式
# ============================================================

def main():

    print("=" * 55)
    print("星展銀行哩程兌換資料系統")
    print("=" * 55)

    try:

        print("\n正在取得星展銀行官方資料...")

        text = fetch_dbs_data()

        print("✅ 官網連線成功")

        print("\n正在解析兌換規則...")

        results = extract_mileage_rules(text)

        print("✅ 兌換規則解析成功")

        print(
            f"共取得 {len(results)} 筆兌換資料"
        )

        display_table(results)

        save_data(results)

        print("\n✅ 程式執行完成")

    except requests.RequestException as e:

        print("\n❌ 官網連線失敗")

        print(f"錯誤原因：{e}")

        print("本次不更新兌換資料。")

    except ValueError as e:

        print("\n❌ 兌換規則解析失敗")

        print(f"錯誤原因：{e}")

        print("本次不更新兌換資料。")


if __name__ == "__main__":

    main()