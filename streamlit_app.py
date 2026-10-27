import json
from pathlib import Path

import streamlit as st


# ============================================================
# 1. 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MILEAGE_FILE = DATA_DIR / "dbs_rates.json"
CASH_FILE = DATA_DIR / "dbs_cash_rates.json"
BILL_FILE = DATA_DIR / "dbs_bill_rates.json"

DBS_BASE_URL = (
    "https://www.dbs.com.tw/"
    "personal-zh/cards/rewards/"
)


# ============================================================
# 2. 官方兌換資料來源
# ============================================================

DBS_MILEAGE_SOURCES = {
    "飛行積金": (
        DBS_BASE_URL + "fly_redeem_mileage"
    ),
    "活利積分（一般卡）": (
        DBS_BASE_URL + "bonus_redeem_mileage"
    ),
    "活利積分（極耀無限卡）": (
        DBS_BASE_URL + "bonus_prestige_redeem_mileage"
    ),
    "現金積點／現金紅利": (
        DBS_BASE_URL + "cash-redeem-mileage"
    ),
    "PChome聯名紅利點數": (
        DBS_BASE_URL + "pchome-redeem-mileage"
    )
}

DBS_CASH_SOURCES = {
    "飛行積金": (
        DBS_BASE_URL + "fly_redeem_creditcard_cash_back"
    ),
    "活利積分": (
        DBS_BASE_URL + "bonus_redeem_creditcard_cash_back"
    ),
    "現金積點／現金紅利": (
        DBS_BASE_URL + "cash-redeem-creditcard-cash-back"
    ),
    "PChome聯名紅利點數": (
        DBS_BASE_URL + "pchome_redeem_creditcard_cash_back"
    )
}

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


# ============================================================
# 3. Streamlit 網頁設定
# ============================================================

st.set_page_config(
    page_title="DBS Rewards Calculator",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# 4. CSS 介面設計
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1080px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #173d65;
    }

    div.stButton > button {
        background-color: #286aa5;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        width: 100%;
    }

    div.stButton > button:hover {
        background-color: #174d7c;
        color: white;
    }

    div[data-testid="stMetric"] {
        background-color: #eef4fc;
        border-radius: 10px;
        padding: 16px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 5. 文字標準化
# ============================================================

def normalize_point_type(value):

    return (
        value.strip()
        .replace(" ", "")
        .replace("　", "")
        .replace("／", "/")
        .replace("（", "(")
        .replace("）", ")")
    )


# ============================================================
# 6. 讀取及驗證 JSON
# ============================================================

def load_json(path, reward_type):

    if not path.exists():
        raise FileNotFoundError(
            f"找不到資料檔案：{path.name}"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 格式錯誤")

    rules = data.get("rules")

    if not isinstance(rules, list) or not rules:
        raise ValueError(
            f"{path.name} 沒有有效兌換資料"
        )

    if reward_type == "mileage":

        fields = [
            "point_type",
            "airline",
            "points_required",
            "miles_received",
            "minimum_miles",
            "miles_increment"
        ]

    else:

        fields = [
            "point_type",
            "points_required",
            "cash_received",
            "minimum_points",
            "points_increment"
        ]

    seen = set()

    for rule in rules:

        if not isinstance(rule, dict):
            raise ValueError("兌換規則格式錯誤")

        for field in fields:
            if field not in rule:
                raise ValueError(
                    f"{path.name} 缺少 {field}"
                )

        if (
            not isinstance(rule["point_type"], str)
            or not rule["point_type"].strip()
        ):
            raise ValueError("點數類型格式錯誤")

        if reward_type == "mileage":

            if not isinstance(rule["airline"], str):
                raise ValueError("航空公司格式錯誤")

            numeric_fields = fields[2:]

            key = (
                normalize_point_type(rule["point_type"]),
                rule["airline"]
            )

        else:

            numeric_fields = fields[1:]

            key = normalize_point_type(
                rule["point_type"]
            )

        for field in numeric_fields:

            value = rule[field]

            if type(value) is not int or value <= 0:
                raise ValueError(
                    f"{path.name} 數值異常：{field}"
                )

        if key in seen:
            raise ValueError(f"重複兌換規則：{key}")

        seen.add(key)

        if reward_type != "mileage":

            numerator = (
                rule["points_increment"]
                * rule["cash_received"]
            )

            if numerator % rule["points_required"] != 0:
                raise ValueError(
                    f"{key} 的兌換單位與比例不相容"
                )

    if reward_type == "bill":

        restrictions = data.get("restrictions")

        if not isinstance(restrictions, dict):
            raise ValueError("缺少帳單折抵限制資料")

        threshold = restrictions.get(
            "minimum_bill_difference_exclusive"
        )

        if type(threshold) is not int or threshold < 0:
            raise ValueError("帳單差額門檻異常")

        if restrictions.get("maximum_offset") != (
            "total_due - minimum_due"
        ):
            raise ValueError("帳單最高折抵公式異常")

        if restrictions.get(
            "minimum_due_can_be_offset"
        ) is not False:
            raise ValueError("最低應繳限制異常")

    return data


@st.cache_data
def load_all_data():

    mileage = load_json(
        MILEAGE_FILE,
        "mileage"
    )

    cash = load_json(
        CASH_FILE,
        "cash"
    )

    bill = load_json(
        BILL_FILE,
        "bill"
    )

    return {
        "航空哩程": mileage,
        "刷卡金": cash,
        "帳單折抵": bill
    }


# ============================================================
# 7. 數學輔助
# ============================================================

def ceil_div(a, b):

    if b <= 0:
        raise ValueError("除數必須大於零")

    return (a + b - 1) // b


def minimum_valid_amount(minimum, increment):

    return ceil_div(minimum, increment) * increment


def cash_per_unit(rule):

    numerator = (
        rule["points_increment"]
        * rule["cash_received"]
    )

    required = rule["points_required"]

    if numerator % required != 0:
        raise ValueError(
            "兌換單位無法換算成整數金額"
        )

    return numerator // required


# ============================================================
# 8. 點數 → 哩程
# ============================================================

def points_to_miles(points, rule):

    required = rule["points_required"]
    received = rule["miles_received"]

    step = rule["miles_increment"]

    minimum_miles = minimum_valid_amount(
        rule["minimum_miles"],
        step
    )

    minimum_points = ceil_div(
        minimum_miles * required,
        received
    )

    if points < minimum_points:

        return {
            "success": False,
            "reason": "insufficient",
            "minimum_points": minimum_points,
            "minimum_miles": minimum_miles,
            "missing_points": minimum_points - points
        }

    theoretical_miles = (
        points * received
    ) // required

    exchange_miles = (
        theoretical_miles // step
    ) * step

    used_points = ceil_div(
        exchange_miles * required,
        received
    )

    return {
        "success": True,
        "exchange_miles": exchange_miles,
        "used_points": used_points,
        "remaining_points": points - used_points
    }


# ============================================================
# 9. 哩程 → 點數
# ============================================================

def mileage_to_points(target, rule):

    required = rule["points_required"]
    received = rule["miles_received"]

    step = rule["miles_increment"]

    minimum_miles = minimum_valid_amount(
        rule["minimum_miles"],
        step
    )

    exchange_miles = max(
        minimum_miles,
        minimum_valid_amount(target, step)
    )

    required_points = ceil_div(
        exchange_miles * required,
        received
    )

    return {
        "success": True,
        "target": target,
        "exchange_miles": exchange_miles,
        "required_points": required_points,
        "extra_miles": exchange_miles - target,
        "adjusted": exchange_miles != target
    }


# ============================================================
# 10. 點數 → 刷卡金
# ============================================================

def points_to_cash(points, rule):

    step = rule["points_increment"]

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    if points < minimum_points:

        return {
            "success": False,
            "reason": "insufficient",
            "minimum_points": minimum_points,
            "missing_points": minimum_points - points
        }

    units = points // step

    used_points = units * step

    cash = units * cash_per_unit(rule)

    return {
        "success": True,
        "cash": cash,
        "used_points": used_points,
        "remaining_points": points - used_points
    }


# ============================================================
# 11. 刷卡金 → 點數
# ============================================================

def cash_to_points(target, rule):

    step = rule["points_increment"]

    unit_cash = cash_per_unit(rule)

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    minimum_cash = (
        minimum_points // step
    ) * unit_cash

    if target < minimum_cash:

        return {
            "success": False,
            "reason": "below_minimum",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points
        }

    units = target // unit_cash

    actual_cash = units * unit_cash

    return {
        "success": True,
        "actual_cash": actual_cash,
        "required_points": units * step,
        "difference": target - actual_cash,
        "adjusted": actual_cash != target
    }


# ============================================================
# 12. 帳單折抵資格判斷
# ============================================================

def check_bill(
    total_due,
    minimum_due,
    restrictions
):

    if minimum_due > total_due:
        raise ValueError(
            "最低應繳金額不可大於總應繳金額"
        )

    difference = total_due - minimum_due

    threshold = restrictions[
        "minimum_bill_difference_exclusive"
    ]

    return {
        "eligible": difference > threshold,
        "difference": difference,
        "maximum_offset": difference,
        "threshold": threshold
    }


# ============================================================
# 13. 點數 → 帳單折抵
# ============================================================

def points_to_bill(
    points,
    rule,
    total_due,
    minimum_due,
    restrictions
):

    bill = check_bill(
        total_due,
        minimum_due,
        restrictions
    )

    if not bill["eligible"]:

        return {
            "success": False,
            "reason": "bill_ineligible",
            **bill
        }

    step = rule["points_increment"]
    unit_cash = cash_per_unit(rule)

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    minimum_cash = (
        minimum_points // step
    ) * unit_cash

    if points < minimum_points:

        return {
            "success": False,
            "reason": "insufficient",
            "minimum_points": minimum_points,
            "missing_points": minimum_points - points,
            **bill
        }

    point_units = points // step

    bill_units = (
        bill["maximum_offset"] // unit_cash
    )

    actual_units = min(
        point_units,
        bill_units
    )

    if actual_units < minimum_points // step:

        return {
            "success": False,
            "reason": "below_minimum",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **bill
        }

    actual_cash = actual_units * unit_cash

    used_points = actual_units * step

    theoretical_cash = point_units * unit_cash

    return {
        "success": True,
        "actual_cash": actual_cash,
        "used_points": used_points,
        "remaining_points": points - used_points,
        "theoretical_cash": theoretical_cash,
        "bill_adjusted": theoretical_cash > actual_cash,
        "remaining_bill": total_due - actual_cash,
        **bill
    }


# ============================================================
# 14. 目標帳單折抵 → 點數
# ============================================================

def bill_to_points(
    target,
    rule,
    total_due,
    minimum_due,
    restrictions
):

    bill = check_bill(
        total_due,
        minimum_due,
        restrictions
    )

    if not bill["eligible"]:

        return {
            "success": False,
            "reason": "bill_ineligible",
            **bill
        }

    step = rule["points_increment"]
    unit_cash = cash_per_unit(rule)

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    minimum_cash = (
        minimum_points // step
    ) * unit_cash

    if target < minimum_cash:

        return {
            "success": False,
            "reason": "below_minimum",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **bill
        }

    allowed_target = min(
        target,
        bill["maximum_offset"]
    )

    units = allowed_target // unit_cash

    if units < minimum_points // step:

        return {
            "success": False,
            "reason": "below_minimum",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **bill
        }

    actual_cash = units * unit_cash

    return {
        "success": True,
        "actual_cash": actual_cash,
        "required_points": units * step,
        "difference": target - actual_cash,
        "bill_adjusted": target > bill["maximum_offset"],
        "unit_adjusted": actual_cash != allowed_target,
        "remaining_bill": total_due - actual_cash,
        **bill
    }


# ============================================================
# 15. 官方網址查找
# ============================================================

def get_official_url(reward, point_type):

    if reward == "航空哩程":
        sources = DBS_MILEAGE_SOURCES

    elif reward == "刷卡金":
        sources = DBS_CASH_SOURCES

    else:
        sources = DBS_BILL_SOURCES

    selected = normalize_point_type(point_type)

    for name, url in sources.items():

        if normalize_point_type(name) == selected:
            return url

    return None


# ============================================================
# 16. 顯示結果的輔助函式
# ============================================================

def show_values(values):

    for label, value in values:
        st.write(f"**{label}：** {value}")


def show_failure(result):

    reason = result.get("reason")

    if reason == "bill_ineligible":

        st.error("本期帳單不符合折抵資格")

        st.write(
            f'帳單差額：NT${result["difference"]:,}'
        )

        st.write(
            "必須大於 "
            f'NT${result["threshold"]:,}'
        )

    elif reason == "insufficient":

        st.error("點數不足，未達最低兌換門檻")

        st.write(
            f'最低所需點數：'
            f'{result["minimum_points"]:,} 點'
        )

        st.write(
            f'還差：'
            f'{result["missing_points"]:,} 點'
        )

    elif reason == "below_minimum":

        st.error("未達最低兌換門檻")

        st.write(
            f'最低所需點數：'
            f'{result["minimum_points"]:,} 點'
        )

        if "minimum_cash" in result:

            st.write(
                f'最低可兌換金額：'
                f'NT${result["minimum_cash"]:,}'
            )


# ============================================================
# 17. 載入資料
# ============================================================

try:

    DATA = load_all_data()

except (
    FileNotFoundError,
    ValueError,
    KeyError,
    json.JSONDecodeError,
    OSError
) as e:

    st.error(f"兌換資料載入失敗：{e}")

    st.info(
        "請確認 data 資料夾內有三份 JSON，"
        "並確認爬蟲已成功執行。"
    )

    st.stop()


# ============================================================
# 18. 網頁標題
# ============================================================

st.title("💳 DBS Rewards Calculator")

st.subheader("星展銀行信用卡點數兌換試算系統")

st.caption(
    "航空哩程｜刷卡金｜帳單折抵"
)

st.info(
    "本工具依星展銀行公開兌換規則進行試算，"
    "並提供官方網站供人工核對。"
    "本專案為個人開發作品，非星展銀行官方服務。"
)

st.divider()


# ============================================================
# 19. 選擇兌換類別
# ============================================================

st.header("① 選擇兌換項目")

reward = st.selectbox(
    "選擇兌換類別",
    [
        "航空哩程",
        "刷卡金",
        "帳單折抵"
    ]
)

current_data = DATA[reward]

rules = current_data["rules"]

point_types = list(
    dict.fromkeys(
        rule["point_type"]
        for rule in rules
    )
)

point_type = st.selectbox(
    "選擇點數類型",
    point_types
)


# ============================================================
# 20. 航空公司
# ============================================================

airline = None

if reward == "航空哩程":

    airlines = list(
        dict.fromkeys(
            rule["airline"]
            for rule in rules
            if rule["point_type"] == point_type
        )
    )

    airline = st.selectbox(
        "選擇航空公司",
        airlines
    )


# ============================================================
# 21. 尋找兌換規則
# ============================================================

selected_rule = None

for rule in rules:

    if rule["point_type"] != point_type:
        continue

    if reward == "航空哩程":

        if rule["airline"] != airline:
            continue

    selected_rule = rule
    break

if selected_rule is None:

    st.error("找不到對應的兌換規則")
    st.stop()


# ============================================================
# 22. 顯示兌換條件
# ============================================================

st.header("② 官方兌換條件")

rule = selected_rule

if reward == "航空哩程":

    minimum_miles = minimum_valid_amount(
        rule["minimum_miles"],
        rule["miles_increment"]
    )

    minimum_points = ceil_div(
        minimum_miles * rule["points_required"],
        rule["miles_received"]
    )

    ratio = (
        f'{rule["points_required"]:,} 點 = '
        f'{rule["miles_received"]:,} 哩'
    )

    minimum_text = (
        f"{minimum_miles:,} 哩"
        f"（需 {minimum_points:,} 點）"
    )

    increment_text = (
        f'每 {rule["miles_increment"]:,} 哩'
    )

else:

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        rule["points_increment"]
    )

    minimum_cash = (
        minimum_points
        * rule["cash_received"]
    ) // rule["points_required"]

    ratio = (
        f'{rule["points_required"]:,} 點 = '
        f'NT${rule["cash_received"]:,}'
    )

    minimum_text = (
        f"{minimum_points:,} 點"
        f"（NT${minimum_cash:,}）"
    )

    increment_text = (
        f'每 {rule["points_increment"]:,} 點'
    )


col1, col2, col3 = st.columns(3)

with col1:
    st.metric("兌換比例", ratio)

with col2:
    st.metric("最低兌換門檻", minimum_text)

with col3:
    st.metric("兌換單位", increment_text)


if reward == "帳單折抵":

    threshold = current_data["restrictions"][
        "minimum_bill_difference_exclusive"
    ]

    st.warning(
        "帳單折抵限制："
        "帳單總應繳金額扣除最低應繳金額後，"
        f"差額必須大於 NT${threshold:,}。"
    )


# ============================================================
# 23. 官方資料來源
# ============================================================

official_url = get_official_url(
    reward,
    point_type
)

if official_url:

    st.link_button(
        "🔗 開啟對應的星展銀行官方兌換頁面",
        official_url
    )

else:

    st.warning(
        "目前沒有找到此點數類型的專屬官方頁面"
    )


st.divider()


# ============================================================
# 24. 選擇換算方式
# ============================================================

st.header("③ 兌換試算")

if reward == "航空哩程":

    mode_options = [
        "點數 → 哩程",
        "哩程 → 點數"
    ]

elif reward == "刷卡金":

    mode_options = [
        "點數 → 刷卡金",
        "刷卡金 → 點數"
    ]

else:

    mode_options = [
        "點數 → 帳單折抵",
        "帳單折抵 → 點數"
    ]


mode = st.radio(
    "選擇換算方式",
    mode_options,
    horizontal=True
)


# ============================================================
# 25. 數量輸入
# ============================================================

if mode.startswith("點數"):

    amount_label = "輸入目前擁有的點數"

elif reward == "航空哩程":

    amount_label = "輸入希望取得的哩程"

elif reward == "刷卡金":

    amount_label = "輸入希望取得的刷卡金（NT$）"

else:

    amount_label = "輸入希望折抵的帳單金額（NT$）"


amount = st.number_input(
    amount_label,
    min_value=0,
    value=0,
    step=1,
    format="%d"
)


# ============================================================
# 26. 帳單折抵專用欄位
# ============================================================

total_due = 0
minimum_due = 0

if reward == "帳單折抵":

    st.subheader("帳單折抵資格資料")

    bill_col1, bill_col2 = st.columns(2)

    with bill_col1:

        total_due = st.number_input(
            "當期帳單總應繳金額（NT$）",
            min_value=0,
            value=0,
            step=1,
            format="%d"
        )

    with bill_col2:

        minimum_due = st.number_input(
            "最低應繳金額（NT$）",
            min_value=0,
            value=0,
            step=1,
            format="%d"
        )


# ============================================================
# 27. 開始計算
# ============================================================

calculate_button = st.button(
    "開始計算",
    use_container_width=True
)


if calculate_button:

    if amount <= 0:

        st.error("請輸入大於 0 的兌換數量")
        st.stop()

    try:

        st.divider()
        st.header("④ 兌換試算結果")

        # ====================================================
        # A. 航空哩程
        # ====================================================

        if reward == "航空哩程":

            if mode == "點數 → 哩程":

                result = points_to_miles(
                    amount,
                    rule
                )

                if not result["success"]:

                    show_failure(result)

                else:

                    st.success("航空哩程兌換試算完成")

                    st.metric(
                        "實際可兌換哩程",
                        f'{result["exchange_miles"]:,} 哩'
                    )

                    show_values([
                        ("點數類型", point_type),
                        ("航空公司", airline),
                        ("目前點數", f"{amount:,} 點"),
                        (
                            "實際扣除點數",
                            f'{result["used_points"]:,} 點'
                        ),
                        (
                            "剩餘點數",
                            f'{result["remaining_points"]:,} 點'
                        )
                    ])

            else:

                result = mileage_to_points(
                    amount,
                    rule
                )

                if result["adjusted"]:

                    st.warning(
                        "已依最低門檻及兌換單位"
                        "向上調整目標哩程"
                    )

                else:

                    st.success("目標哩程試算完成")

                st.metric(
                    "所需信用卡點數",
                    f'{result["required_points"]:,} 點'
                )

                show_values([
                    ("點數類型", point_type),
                    ("航空公司", airline),
                    ("原始目標哩程", f"{amount:,} 哩"),
                    (
                        "實際需轉入哩程",
                        f'{result["exchange_miles"]:,} 哩'
                    ),
                    (
                        "額外取得哩程",
                        f'{result["extra_miles"]:,} 哩'
                    )
                ])

                st.caption(
                    "此模式反推所需點數，"
                    "未確認實際持有點數。"
                )

        # ====================================================
        # B. 刷卡金
        # ====================================================

        elif reward == "刷卡金":

            if mode == "點數 → 刷卡金":

                result = points_to_cash(
                    amount,
                    rule
                )

                if not result["success"]:

                    show_failure(result)

                else:

                    st.success("刷卡金兌換試算完成")

                    st.metric(
                        "實際可兌換刷卡金",
                        f'NT${result["cash"]:,}'
                    )

                    show_values([
                        ("點數類型", point_type),
                        ("目前點數", f"{amount:,} 點"),
                        (
                            "實際使用點數",
                            f'{result["used_points"]:,} 點'
                        ),
                        (
                            "剩餘點數",
                            f'{result["remaining_points"]:,} 點'
                        )
                    ])

            else:

                result = cash_to_points(
                    amount,
                    rule
                )

                if not result["success"]:

                    show_failure(result)

                else:

                    if result["adjusted"]:

                        st.warning(
                            "已依兌換單位向下調整刷卡金"
                        )

                    else:

                        st.success("刷卡金試算完成")

                    st.metric(
                        "所需信用卡點數",
                        f'{result["required_points"]:,} 點'
                    )

                    show_values([
                        ("點數類型", point_type),
                        (
                            "希望折抵金額",
                            f"NT${amount:,}"
                        ),
                        (
                            "實際可兌換刷卡金",
                            f'NT${result["actual_cash"]:,}'
                        ),
                        (
                            "未納入兌換金額",
                            f'NT${result["difference"]:,}'
                        )
                    ])

                    st.caption(
                        "本模式僅反推所需點數，"
                        "未確認客戶實際持有點數。"
                    )

        # ====================================================
        # C. 帳單折抵
        # ====================================================

        else:

            restrictions = current_data[
                "restrictions"
            ]

            if mode == "點數 → 帳單折抵":

                result = points_to_bill(
                    amount,
                    rule,
                    total_due,
                    minimum_due,
                    restrictions
                )

            else:

                result = bill_to_points(
                    amount,
                    rule,
                    total_due,
                    minimum_due,
                    restrictions
                )

            if not result["success"]:

                show_failure(result)

            else:

                if (
                    result.get("bill_adjusted")
                    or result.get("unit_adjusted")
                ):

                    st.warning(
                        "已依帳單上限或兌換單位"
                        "調整實際折抵金額"
                    )

                else:

                    st.success("帳單折抵試算完成")

                st.metric(
                    "實際可折抵帳單金額",
                    f'NT${result["actual_cash"]:,}'
                )

                show_values([
                    ("點數類型", point_type),
                    (
                        "帳單總應繳",
                        f"NT${total_due:,}"
                    ),
                    (
                        "最低應繳金額",
                        f"NT${minimum_due:,}"
                    ),
                    (
                        "帳單最高可折抵",
                        f'NT${result["maximum_offset"]:,}'
                    )
                ])

                st.divider()

                if mode == "點數 → 帳單折抵":

                    show_values([
                        (
                            "目前點數",
                            f"{amount:,} 點"
                        ),
                        (
                            "理論可折抵",
                            f'NT${result["theoretical_cash"]:,}'
                        ),
                        (
                            "實際使用點數",
                            f'{result["used_points"]:,} 點'
                        ),
                        (
                            "剩餘點數",
                            f'{result["remaining_points"]:,} 點'
                        )
                    ])

                else:

                    show_values([
                        (
                            "希望折抵金額",
                            f"NT${amount:,}"
                        ),
                        (
                            "所需信用卡點數",
                            f'{result["required_points"]:,} 點'
                        ),
                        (
                            "未納入折抵金額",
                            f'NT${result["difference"]:,}'
                        )
                    ])

                    st.caption(
                        "本模式僅反推所需點數，"
                        "未確認客戶實際持有點數。"
                    )

                st.info(
                    "折抵後帳單剩餘："
                    f'NT${result["remaining_bill"]:,}'
                )

                st.caption(
                    "本試算依帳單差額、"
                    "最低兌換門檻及兌換單位計算。"
                    "實際折抵仍須符合銀行申請規定。"
                )

    except (
        ValueError,
        KeyError,
        ZeroDivisionError
    ) as e:

        st.error(f"計算失敗：{e}")


# ============================================================
# 28. 資料更新資訊
# ============================================================

st.divider()

st.subheader("📅 資料來源與更新時間")

for reward_name, data in DATA.items():

    fetched_at = data.get(
        "fetched_at",
        "未知"
    )

    st.caption(
        f"{reward_name}：{fetched_at}"
    )


# ============================================================
# 29. 專案介紹
# ============================================================

st.divider()

with st.expander("📖 About This Project"):

    st.markdown(
        """
        ### DBS Rewards Calculator

        **星展銀行信用卡點數兌換試算系統**

        本專案使用 Python 建立信用卡回饋兌換工具，
        整合以下功能：

        - 航空哩程雙向換算
        - 刷卡金雙向換算
        - 帳單折抵資格與上限試算
        - 最低兌換門檻與兌換單位檢查
        - 官方兌換規則查核

        **技術架構**

        Python / Requests / BeautifulSoup /
        JSON / Streamlit

        **專案性質**

        本工具為個人開發作品，
        並非星展銀行官方系統。

        兌換比例及規則可能隨官方公告調整，
        實際申請結果以銀行最新規定為準。
        """
    )