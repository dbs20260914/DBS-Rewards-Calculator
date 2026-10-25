import json
import tkinter as tk
import webbrowser

from pathlib import Path
from tkinter import ttk, messagebox


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

BG_COLOR = "#f3f6fb"
BLUE_COLOR = "#286aa5"
GREEN_COLOR = "#167a45"
RED_COLOR = "#bb3030"
YELLOW_COLOR = "#a16a00"

FONT_NAME = "Microsoft JhengHei"


# ============================================================
# 2. 航空哩程官方來源
# ============================================================

DBS_MILEAGE_SOURCES = {

    "飛行積金": {
        "name": "星展銀行｜飛行積金兌換哩程",
        "url": DBS_BASE_URL + "fly_redeem_mileage"
    },

    "活利積分（一般卡）": {
        "name": "星展銀行｜活利積分兌換哩程",
        "url": DBS_BASE_URL + "bonus_redeem_mileage"
    },

    "活利積分（極耀無限卡）": {
        "name": "星展銀行｜極耀無限卡兌換哩程",
        "url": DBS_BASE_URL + "bonus_prestige_redeem_mileage"
    },

    "現金積點／現金紅利": {
        "name": "星展銀行｜現金積點兌換哩程",
        "url": DBS_BASE_URL + "cash-redeem-mileage"
    },

    "PChome聯名紅利點數": {
        "name": "星展銀行｜PChome聯名紅利點數兌換哩程",
        "url": DBS_BASE_URL + "pchome-redeem-mileage"
    }
}


# ============================================================
# 3. 刷卡金官方來源
# ============================================================

DBS_CASH_SOURCES = {

    "飛行積金": {
        "name": "星展銀行｜飛行積金兌換刷卡金",
        "url": DBS_BASE_URL + "fly_redeem_creditcard_cash_back"
    },

    "活利積分": {
        "name": "星展銀行｜活利積分兌換刷卡金",
        "url": DBS_BASE_URL + "bonus_redeem_creditcard_cash_back"
    },

    "現金積點／現金紅利": {
        "name": "星展銀行｜現金積點兌換刷卡金",
        "url": DBS_BASE_URL + "cash-redeem-creditcard-cash-back"
    },

    "PChome聯名紅利點數": {
        "name": "星展銀行｜PChome聯名紅利點數兌換刷卡金",
        "url": DBS_BASE_URL + "pchome_redeem_creditcard_cash_back"
    }
}


# ============================================================
# 4. 帳單折抵官方來源（新增）
# ============================================================

DBS_BILL_SOURCES = {

    "飛行積金": {
        "name": "星展銀行｜飛行積金帳單折抵",
        "url": DBS_BASE_URL + "fly_redeem_ir2"
    },

    "活利積分": {
        "name": "星展銀行｜活利積分帳單折抵",
        "url": DBS_BASE_URL + "bonus_redeem_ir2"
    },

    "PChome聯名紅利點數": {
        "name": "星展銀行｜PChome聯名紅利點數帳單折抵",
        "url": DBS_BASE_URL + "pchome_redeem_ir2"
    }
}


# ============================================================
# 5. 數學工具
# ============================================================

def ceil_div(a, b):

    if b <= 0:
        raise ValueError("除數必須大於零")

    return (a + b - 1) // b


def minimum_valid_amount(minimum, increment):

    return ceil_div(
        minimum,
        increment
    ) * increment


def normalize_point_type(value):

    return (
        value.strip()
        .replace(" ", "")
        .replace("　", "")
        .replace("／", "/")
        .replace("（", "(")
        .replace("）", ")")
    )


def parse_positive_integer(value):

    number = int(
        value.replace(",", "").strip()
    )

    if number <= 0:
        raise ValueError

    return number


def parse_nonnegative_integer(value):

    number = int(
        value.replace(",", "").strip()
    )

    if number < 0:
        raise ValueError

    return number


# ============================================================
# 6. 讀取 JSON
# ============================================================

def load_json(path, reward_type):

    if not path.exists():

        raise FileNotFoundError(
            f"找不到資料檔案：{path.name}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name} 資料格式錯誤"
        )

    rules = data.get("rules")

    if not isinstance(rules, list) or not rules:

        raise ValueError(
            f"{path.name} 沒有有效兌換資料"
        )

    if reward_type == "mileage":

        required_fields = [
            "point_type",
            "airline",
            "points_required",
            "miles_received",
            "minimum_miles",
            "miles_increment"
        ]

    else:

        required_fields = [
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

        for field in required_fields:

            if field not in rule:

                raise ValueError(
                    f"{path.name} 缺少欄位：{field}"
                )

        if not isinstance(rule["point_type"], str):
            raise ValueError("點數類型格式錯誤")

        if not rule["point_type"].strip():
            raise ValueError("點數類型不得為空白")

        if reward_type == "mileage":

            if not isinstance(rule["airline"], str):
                raise ValueError("航空公司格式錯誤")

            key = (
                normalize_point_type(rule["point_type"]),
                rule["airline"]
            )

            numeric_fields = required_fields[2:]

        else:

            key = normalize_point_type(
                rule["point_type"]
            )

            numeric_fields = required_fields[1:]

        for field in numeric_fields:

            value = rule[field]

            if type(value) is not int or value <= 0:

                raise ValueError(
                    f"{path.name} 數值異常：{field}"
                )

        if key in seen:

            raise ValueError(
                f"重複兌換規則：{key}"
            )

        seen.add(key)

        if reward_type != "mileage":

            numerator = (
                rule["points_increment"]
                * rule["cash_received"]
            )

            if numerator % rule["points_required"] != 0:

                raise ValueError(
                    f"{key} 的兌換單位無法換算為整數金額"
                )

    if reward_type == "bill":

        restrictions = data.get("restrictions")

        if not isinstance(restrictions, dict):
            raise ValueError("帳單折抵限制資料不存在")

        threshold = restrictions.get(
            "minimum_bill_difference_exclusive"
        )

        if type(threshold) is not int or threshold < 0:

            raise ValueError(
                "帳單最低差額門檻格式錯誤"
            )

        if restrictions.get("maximum_offset") != (
            "total_due - minimum_due"
        ):

            raise ValueError(
                "帳單最高折抵公式不符合預期"
            )

        if restrictions.get(
            "minimum_due_can_be_offset"
        ) is not False:

            raise ValueError(
                "最低應繳金額限制不符合預期"
            )

    return data


# ============================================================
# 7. 點數 → 哩程
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
            "minimum_miles": minimum_miles,
            "minimum_points": minimum_points,
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
# 8. 哩程 → 點數
# ============================================================

def mileage_to_points_target(target_miles, rule):

    required = rule["points_required"]
    received = rule["miles_received"]

    step = rule["miles_increment"]

    minimum_miles = minimum_valid_amount(
        rule["minimum_miles"],
        step
    )

    target_exchange = minimum_valid_amount(
        target_miles,
        step
    )

    exchange_miles = max(
        minimum_miles,
        target_exchange
    )

    required_points = ceil_div(
        exchange_miles * required,
        received
    )

    return {
        "success": True,
        "target_miles": target_miles,
        "exchange_miles": exchange_miles,
        "required_points": required_points,
        "extra_miles": exchange_miles - target_miles,
        "minimum_miles": minimum_miles,
        "adjusted": exchange_miles != target_miles
    }


# ============================================================
# 9. 點數 → 刷卡金
# ============================================================

def points_to_cash(points, rule):

    required = rule["points_required"]
    cash = rule["cash_received"]

    step = rule["points_increment"]

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    if points < minimum_points:

        return {
            "success": False,
            "minimum_points": minimum_points,
            "missing_points": minimum_points - points
        }

    used_points = (
        points // step
    ) * step

    exchange_cash = (
        used_points * cash
    ) // required

    return {
        "success": True,
        "cash": exchange_cash,
        "used_points": used_points,
        "remaining_points": points - used_points
    }


# ============================================================
# 10. 刷卡金 → 點數
# ============================================================

def cash_to_points_floor(target_cash, rule):

    required = rule["points_required"]
    cash = rule["cash_received"]

    step = rule["points_increment"]

    cash_per_step = (
        step * cash
    ) // required

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    minimum_cash = (
        minimum_points // step
    ) * cash_per_step

    if target_cash < minimum_cash:

        return {
            "success": False,
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points
        }

    units = target_cash // cash_per_step

    actual_cash = units * cash_per_step

    return {
        "success": True,
        "actual_cash": actual_cash,
        "required_points": units * step,
        "difference": target_cash - actual_cash,
        "adjusted": actual_cash != target_cash
    }


# ============================================================
# 11. 帳單折抵資格判斷（新增）
# ============================================================

def check_bill_eligibility(
    total_due,
    minimum_due,
    restrictions
):

    if minimum_due > total_due:

        raise ValueError(
            "最低應繳金額不可大於帳單總應繳金額"
        )

    bill_difference = total_due - minimum_due

    threshold = restrictions[
        "minimum_bill_difference_exclusive"
    ]

    eligible = bill_difference > threshold

    return {
        "eligible": eligible,
        "bill_difference": bill_difference,
        "maximum_offset": bill_difference,
        "threshold": threshold
    }


# ============================================================
# 12. 點數 → 帳單折抵（新增）
# ============================================================

def points_to_bill(
    points,
    rule,
    total_due,
    minimum_due,
    restrictions
):

    eligibility = check_bill_eligibility(
        total_due,
        minimum_due,
        restrictions
    )

    if not eligibility["eligible"]:

        return {
            "success": False,
            "reason": "bill_ineligible",
            **eligibility
        }

    step = rule["points_increment"]

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    cash_per_step = (
        step * rule["cash_received"]
    ) // rule["points_required"]

    minimum_cash = (
        minimum_points // step
    ) * cash_per_step

    # 帳單差額可能符合資格，
    # 但最高折抵金額仍低於兌換最低門檻。
    if eligibility["maximum_offset"] < minimum_cash:

        return {
            "success": False,
            "reason": "below_minimum_cash",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **eligibility
        }

    if points < minimum_points:

        return {
            "success": False,
            "reason": "insufficient_points",
            "minimum_points": minimum_points,
            "missing_points": minimum_points - points,
            **eligibility
        }

    # 目前點數可以提供多少完整折抵單位
    point_units = points // step

    # 帳單上限允許多少完整折抵單位
    bill_units = (
        eligibility["maximum_offset"]
        // cash_per_step
    )

    # 取兩種限制下較小的數量
    actual_units = min(
        point_units,
        bill_units
    )

    minimum_units = minimum_points // step

    if actual_units < minimum_units:

        return {
            "success": False,
            "reason": "below_minimum_cash",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **eligibility
        }

    actual_cash = actual_units * cash_per_step

    used_points = actual_units * step

    theoretical_cash = point_units * cash_per_step

    return {
        "success": True,
        "actual_cash": actual_cash,
        "used_points": used_points,
        "remaining_points": points - used_points,
        "theoretical_cash": theoretical_cash,
        "bill_limit_adjusted": (
            theoretical_cash > actual_cash
        ),
        "remaining_bill": total_due - actual_cash,
        **eligibility
    }


# ============================================================
# 13. 目標帳單折抵 → 點數（新增）
# ============================================================

def bill_to_points(
    target_cash,
    rule,
    total_due,
    minimum_due,
    restrictions
):

    eligibility = check_bill_eligibility(
        total_due,
        minimum_due,
        restrictions
    )

    if not eligibility["eligible"]:

        return {
            "success": False,
            "reason": "bill_ineligible",
            **eligibility
        }

    step = rule["points_increment"]

    cash_per_step = (
        step * rule["cash_received"]
    ) // rule["points_required"]

    minimum_points = minimum_valid_amount(
        rule["minimum_points"],
        step
    )

    minimum_cash = (
        minimum_points // step
    ) * cash_per_step

    if eligibility["maximum_offset"] < minimum_cash:

        return {
            "success": False,
            "reason": "below_minimum_cash",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **eligibility
        }

    if target_cash < minimum_cash:

        return {
            "success": False,
            "reason": "target_below_minimum",
            "minimum_cash": minimum_cash,
            "minimum_points": minimum_points,
            **eligibility
        }

    # 先限制不得超過帳單最高折抵金額
    allowed_target = min(
        target_cash,
        eligibility["maximum_offset"]
    )

    # 再向下取至合法兌換單位
    units = allowed_target // cash_per_step

    actual_cash = units * cash_per_step

    required_points = units * step

    return {
        "success": True,
        "actual_cash": actual_cash,
        "required_points": required_points,
        "difference": target_cash - actual_cash,
        "bill_limit_adjusted": (
            target_cash > eligibility["maximum_offset"]
        ),
        "unit_adjusted": (
            actual_cash != allowed_target
        ),
        "remaining_bill": total_due - actual_cash,
        **eligibility
    }


# ============================================================
# 14. Tkinter 主程式
# ============================================================

class DBSApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "星展銀行信用卡點數兌換計算機"
        )

        self.root.geometry("900x850")
        self.root.minsize(720, 600)

        self.root.configure(bg=BG_COLOR)

        self.mileage_data = None
        self.cash_data = None
        self.bill_data = None

        self.reward_var = tk.StringVar(
            value="航空哩程"
        )

        self.point_var = tk.StringVar()
        self.airline_var = tk.StringVar()

        self.mode_var = tk.StringVar(
            value="points"
        )

        self.amount_var = tk.StringVar()

        # 帳單折抵專用輸入
        self.total_due_var = tk.StringVar()
        self.minimum_due_var = tk.StringVar()

        self.ratio_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.info_var = tk.StringVar()

        self.build_ui()
        self.load_data()


    # ========================================================
    # 15. 建立介面
    # ========================================================

    def build_ui(self):

        tk.Label(
            self.root,
            text="星展銀行信用卡點數兌換計算機",
            font=(FONT_NAME, 20, "bold"),
            bg=BG_COLOR,
            fg="#173d65"
        ).pack(pady=(18, 7))

        tk.Label(
            self.root,
            text="航空哩程／刷卡金／帳單折抵",
            font=(FONT_NAME, 11),
            bg=BG_COLOR,
            fg="#777777"
        ).pack(pady=(0, 12))

        # ----------------------------------------------------
        # 可捲動容器
        # ----------------------------------------------------

        container = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        container.pack(
            fill="both",
            expand=True
        )

        self.canvas = tk.Canvas(
            container,
            bg=BG_COLOR,
            highlightthickness=0
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview
        )

        self.scrollbar.pack(
            side="right",
            fill="y"
        )

        self.canvas.configure(
            yscrollcommand=self.scrollbar.set
        )

        self.scrollable_frame = tk.Frame(
            self.canvas,
            bg=BG_COLOR
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.scrollable_frame.bind(
            "<Configure>",
            self.update_scrollregion
        )

        self.canvas.bind(
            "<Configure>",
            self.update_canvas_width
        )

        self.root.bind(
            "<MouseWheel>",
            self.on_mousewheel
        )

        self.root.bind_all(
            "<MouseWheel>",
            self.on_mousewheel
        )

        # ----------------------------------------------------
        # 主操作區
        # ----------------------------------------------------

        frame = tk.Frame(
            self.scrollable_frame,
            bg="white",
            padx=25,
            pady=20
        )

        frame.pack(
            fill="x",
            padx=25,
            pady=5
        )

        self.selection_frame = tk.Frame(
            frame,
            bg="white"
        )

        self.selection_frame.pack(fill="x")

        self.selection_frame.columnconfigure(
            0,
            weight=1
        )

        # ----------------------------------------------------
        # 兌換類別
        # ----------------------------------------------------

        tk.Label(
            self.selection_frame,
            text="選擇兌換類別",
            bg="white",
            font=(FONT_NAME, 10)
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.reward_combo = ttk.Combobox(
            self.selection_frame,
            textvariable=self.reward_var,
            values=[
                "航空哩程",
                "刷卡金",
                "帳單折抵"
            ],
            state="readonly"
        )

        self.reward_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 15)
        )

        self.reward_combo.bind(
            "<<ComboboxSelected>>",
            self.update_reward_type
        )

        # ----------------------------------------------------
        # 點數類型
        # ----------------------------------------------------

        tk.Label(
            self.selection_frame,
            text="選擇點數類型",
            bg="white",
            font=(FONT_NAME, 10)
        ).grid(
            row=2,
            column=0,
            sticky="w"
        )

        self.point_combo = ttk.Combobox(
            self.selection_frame,
            textvariable=self.point_var,
            state="readonly"
        )

        self.point_combo.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(5, 15)
        )

        self.point_combo.bind(
            "<<ComboboxSelected>>",
            self.update_airlines
        )

        # ----------------------------------------------------
        # 航空公司區域
        # ----------------------------------------------------

        self.airline_frame = tk.Frame(
            self.selection_frame,
            bg="white"
        )

        self.airline_frame.grid(
            row=4,
            column=0,
            sticky="ew"
        )

        self.airline_frame.columnconfigure(
            0,
            weight=1
        )

        tk.Label(
            self.airline_frame,
            text="選擇航空公司",
            bg="white"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.airline_combo = ttk.Combobox(
            self.airline_frame,
            textvariable=self.airline_var,
            state="readonly"
        )

        self.airline_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 15)
        )

        self.airline_combo.bind(
            "<<ComboboxSelected>>",
            self.on_airline_change
        )

        # ----------------------------------------------------
        # 兌換規則資訊
        # ----------------------------------------------------

        info_frame = tk.Frame(
            frame,
            bg="#eef4fc",
            padx=15,
            pady=12
        )

        info_frame.pack(
            fill="x",
            pady=(5, 15)
        )

        tk.Label(
            info_frame,
            textvariable=self.ratio_var,
            bg="#eef4fc",
            fg="#194c81",
            font=(FONT_NAME, 11, "bold"),
            justify="left",
            anchor="w"
        ).pack(fill="x")

        ttk.Separator(
            info_frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=(12, 10)
        )

        tk.Label(
            info_frame,
            textvariable=self.source_var,
            bg="#eef4fc",
            fg="#555555",
            justify="left",
            anchor="w"
        ).pack(
            fill="x",
            pady=(0, 8)
        )

        self.source_button = tk.Button(
            info_frame,
            text="開啟對應的星展銀行官方兌換頁面",
            bg="#dbe8f8",
            fg="#194c81",
            relief="flat",
            cursor="hand2",
            command=self.open_official_source
        )

        self.source_button.pack(
            fill="x",
            ipady=6
        )

        # ----------------------------------------------------
        # 帳單折抵專用欄位
        # ----------------------------------------------------

        self.bill_frame = tk.Frame(
            frame,
            bg="#fff8e8",
            padx=15,
            pady=12
        )

        tk.Label(
            self.bill_frame,
            text="帳單折抵資格資料",
            bg="#fff8e8",
            fg="#8a5b00",
            font=(FONT_NAME, 11, "bold")
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        tk.Label(
            self.bill_frame,
            text="當期帳單總應繳金額（NT$）",
            bg="#fff8e8"
        ).pack(anchor="w")

        ttk.Entry(
            self.bill_frame,
            textvariable=self.total_due_var
        ).pack(
            fill="x",
            pady=(5, 12)
        )

        tk.Label(
            self.bill_frame,
            text="最低應繳金額（NT$）",
            bg="#fff8e8"
        ).pack(anchor="w")

        ttk.Entry(
            self.bill_frame,
            textvariable=self.minimum_due_var
        ).pack(
            fill="x",
            pady=(5, 5)
        )

        # ----------------------------------------------------
        # 換算模式
        # ----------------------------------------------------

        tk.Label(
            frame,
            text="選擇換算方式",
            bg="white"
        ).pack(
            anchor="w",
            pady=(10, 0)
        )

        mode_frame = tk.Frame(
            frame,
            bg="white"
        )

        mode_frame.pack(
            anchor="w",
            pady=10
        )

        self.points_radio = tk.Radiobutton(
            mode_frame,
            variable=self.mode_var,
            value="points",
            bg="white",
            command=self.on_mode_change
        )

        self.points_radio.pack(
            side="left",
            padx=(0, 25)
        )

        self.target_radio = tk.Radiobutton(
            mode_frame,
            variable=self.mode_var,
            value="target",
            bg="white",
            command=self.on_mode_change
        )

        self.target_radio.pack(side="left")

        # ----------------------------------------------------
        # 數量輸入
        # ----------------------------------------------------

        self.amount_label = tk.Label(
            frame,
            bg="white"
        )

        self.amount_label.pack(
            anchor="w",
            pady=(10, 5)
        )

        self.amount_entry = ttk.Entry(
            frame,
            textvariable=self.amount_var
        )

        self.amount_entry.pack(
            fill="x",
            pady=(0, 15)
        )

        # ----------------------------------------------------
        # 開始計算
        # ----------------------------------------------------

        tk.Button(
            frame,
            text="開始計算",
            font=(FONT_NAME, 12, "bold"),
            bg=BLUE_COLOR,
            fg="white",
            relief="flat",
            command=self.calculate
        ).pack(
            fill="x",
            ipady=9,
            pady=(5, 15)
        )

        # ----------------------------------------------------
        # 計算結果
        # ----------------------------------------------------

        self.status_label = tk.Label(
            frame,
            text="兌換試算結果",
            bg="#f1f5fa",
            fg="#333333",
            font=(FONT_NAME, 12, "bold"),
            anchor="w",
            padx=15,
            pady=10
        )

        self.status_label.pack(fill="x")

        self.result_label = tk.Label(
            frame,
            text="",
            bg="#f1f5fa",
            fg="#222222",
            font=(FONT_NAME, 11),
            justify="left",
            anchor="nw",
            padx=15,
            pady=12
        )

        self.result_label.pack(fill="x")

        # ----------------------------------------------------
        # 資料更新時間
        # ----------------------------------------------------

        tk.Label(
            self.scrollable_frame,
            textvariable=self.info_var,
            bg=BG_COLOR,
            fg="#777777",
            justify="center",
            font=(FONT_NAME, 9)
        ).pack(pady=(10, 5))

        tk.Button(
            self.scrollable_frame,
            text="重新讀取本機兌換資料",
            command=self.load_data
        ).pack(pady=(0, 20))


    # ========================================================
    # 16. 捲動控制
    # ========================================================

    def update_scrollregion(self, event=None):

        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )


    def update_canvas_width(self, event):

        self.canvas.itemconfigure(
            self.canvas_window,
            width=event.width
        )


    def on_mousewheel(self, event):

        if self.canvas.winfo_height() <= 0:
            return

        # 避免滑鼠滾輪干擾下拉選單
        if isinstance(event.widget, ttk.Combobox):
            return

        if event.delta:

            direction = (
                -1 if event.delta > 0 else 1
            )

            self.canvas.yview_scroll(
                direction,
                "units"
            )


    def scroll_to_result(self):

        self.root.update_idletasks()

        content_height = (
            self.scrollable_frame.winfo_height()
        )

        canvas_height = self.canvas.winfo_height()

        if content_height <= canvas_height:
            return

        result_y = (
            self.status_label.winfo_rooty()
            - self.scrollable_frame.winfo_rooty()
        )

        target = max(
            0,
            result_y - 30
        )

        # Canvas 捲動位置以整個內容高度為基準
        fraction = target / content_height

        self.canvas.yview_moveto(
            min(1, fraction)
        )


    # ========================================================
    # 17. 載入全部兌換資料
    # ========================================================

    def load_data(self):

        try:

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

            self.mileage_data = mileage
            self.cash_data = cash
            self.bill_data = bill

            self.update_reward_type()

            self.info_var.set(
                "哩程資料更新："
                f'{mileage.get("fetched_at", "未知")}\n'
                "刷卡金資料更新："
                f'{cash.get("fetched_at", "未知")}\n'
                "帳單折抵資料更新："
                f'{bill.get("fetched_at", "未知")}'
            )

            self.show_result(
                "三種兌換資料已載入成功。"
            )

        except (
            OSError,
            ValueError,
            KeyError,
            json.JSONDecodeError
        ) as e:

            messagebox.showerror(
                "資料載入失敗",
                str(e)
            )


    # ========================================================
    # 18. 切換兌換類別
    # ========================================================

    def update_reward_type(self, event=None):

        if (
            self.mileage_data is None
            or self.cash_data is None
            or self.bill_data is None
        ):
            return

        reward = self.reward_var.get()

        if reward == "航空哩程":

            rules = self.mileage_data["rules"]

            self.airline_frame.grid()

            self.bill_frame.pack_forget()

        elif reward == "刷卡金":

            rules = self.cash_data["rules"]

            self.airline_frame.grid_remove()

            self.bill_frame.pack_forget()

        else:

            rules = self.bill_data["rules"]

            self.airline_frame.grid_remove()

            # 帳單折抵才顯示兩個帳單欄位
            self.bill_frame.pack(
                fill="x",
                after=self.selection_frame,
                pady=(0, 15)
            )

        point_types = list(
            dict.fromkeys(
                rule["point_type"]
                for rule in rules
            )
        )

        self.point_combo["values"] = point_types

        self.point_var.set(
            point_types[0] if point_types else ""
        )

        self.amount_var.set("")

        self.update_airlines()
        self.update_mode()
        self.update_source()

        self.show_result("")


    # ========================================================
    # 19. 更新航空公司
    # ========================================================

    def update_airlines(self, event=None):

        if self.mileage_data is None:
            return

        if self.reward_var.get() == "航空哩程":

            point_type = self.point_var.get()

            airlines = list(
                dict.fromkeys(
                    rule["airline"]
                    for rule in self.mileage_data["rules"]
                    if rule["point_type"] == point_type
                )
            )

            self.airline_combo["values"] = airlines

            self.airline_var.set(
                airlines[0] if airlines else ""
            )

        else:

            self.airline_var.set("")

        self.update_ratio()
        self.update_source()

        self.show_result("")


    def on_airline_change(self, event=None):

        self.update_ratio()
        self.update_source()

        self.show_result("")


    # ========================================================
    # 20. 尋找兌換規則
    # ========================================================

    def get_selected_rule(self):

        reward = self.reward_var.get()

        point_type = self.point_var.get()

        if reward == "航空哩程":

            if self.mileage_data is None:
                return None

            airline = self.airline_var.get()

            rules = self.mileage_data["rules"]

            for rule in rules:

                if (
                    rule["point_type"] == point_type
                    and rule["airline"] == airline
                ):
                    return rule

        else:

            data = (
                self.cash_data
                if reward == "刷卡金"
                else self.bill_data
            )

            if data is None:
                return None

            for rule in data["rules"]:

                if rule["point_type"] == point_type:
                    return rule

        return None


    # ========================================================
    # 21. 更新兌換比例與門檻
    # ========================================================

    def update_ratio(self):

        rule = self.get_selected_rule()

        if rule is None:

            self.ratio_var.set(
                "無可用兌換資料"
            )

            return

        reward = self.reward_var.get()

        if reward == "航空哩程":

            minimum_miles = minimum_valid_amount(
                rule["minimum_miles"],
                rule["miles_increment"]
            )

            minimum_points = ceil_div(
                minimum_miles
                * rule["points_required"],
                rule["miles_received"]
            )

            text = (
                f'兌換比例：'
                f'{rule["points_required"]:,} 點 = '
                f'{rule["miles_received"]:,} 哩\n'
                f'最低兌換門檻：'
                f'{minimum_miles:,} 哩'
                f'（需 {minimum_points:,} 點）\n'
                f'兌換單位：'
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

            text = (
                f'兌換比例：'
                f'{rule["points_required"]:,} 點 = '
                f'NT${rule["cash_received"]:,}\n'
                f'最低兌換門檻：'
                f'{minimum_points:,} 點'
                f'（NT${minimum_cash:,}）\n'
                f'兌換單位：'
                f'每 {rule["points_increment"]:,} 點'
            )

            if reward == "帳單折抵":

                threshold = self.bill_data[
                    "restrictions"
                ][
                    "minimum_bill_difference_exclusive"
                ]

                text += (
                    "\n帳單資格限制："
                    f"總應繳－最低應繳 > NT${threshold:,}"
                )

        self.ratio_var.set(text)


    # ========================================================
    # 22. 官方來源
    # ========================================================

    def get_official_source(self):

        reward = self.reward_var.get()

        if reward == "航空哩程":

            sources = DBS_MILEAGE_SOURCES

        elif reward == "刷卡金":

            sources = DBS_CASH_SOURCES

        else:

            sources = DBS_BILL_SOURCES

        selected = normalize_point_type(
            self.point_var.get()
        )

        for name, source in sources.items():

            if normalize_point_type(name) == selected:
                return source

        return None


    def update_source(self):

        source = self.get_official_source()

        if source is None:

            self.source_var.set(
                "官方資料來源：尚未建立對應頁面"
            )

            self.source_button.config(
                state="disabled"
            )

            return

        self.source_var.set(
            f'官方資料來源：{source["name"]}'
        )

        self.source_button.config(
            state="normal"
        )


    def open_official_source(self):

        source = self.get_official_source()

        if source is None:

            messagebox.showwarning(
                "沒有來源",
                "尚未建立對應官方頁面"
            )

            return

        try:

            opened = webbrowser.open(
                source["url"],
                new=2
            )

            if not opened:

                messagebox.showwarning(
                    "開啟失敗",
                    "無法啟動預設瀏覽器"
                )

        except Exception as e:

            messagebox.showerror(
                "開啟失敗",
                str(e)
            )


    # ========================================================
    # 23. 更新換算方向
    # ========================================================

    def update_mode(self):

        reward = self.reward_var.get()

        if reward == "航空哩程":

            left = "點數 → 哩程"
            right = "哩程 → 點數"

        elif reward == "刷卡金":

            left = "點數 → 刷卡金"
            right = "刷卡金 → 點數"

        else:

            left = "點數 → 帳單折抵"
            right = "帳單折抵 → 點數"

        self.points_radio.config(text=left)
        self.target_radio.config(text=right)

        if self.mode_var.get() == "points":

            label = "輸入目前擁有的點數"

        elif reward == "航空哩程":

            label = "輸入希望取得的哩程"

        elif reward == "刷卡金":

            label = "輸入希望取得的刷卡金（NT$）"

        else:

            label = "輸入希望折抵的帳單金額（NT$）"

        self.amount_label.config(
            text=label
        )


    def on_mode_change(self):

        self.update_mode()

        self.amount_var.set("")

        self.show_result("")


    # ========================================================
    # 24. 顯示計算結果
    # ========================================================

    def show_result(
        self,
        text,
        status="normal",
        scroll=False
    ):

        styles = {

            "mileage_success": (
                "✅ 哩程兌換試算完成",
                GREEN_COLOR
            ),

            "mileage_adjusted": (
                "⚠️ 已向上調整目標哩程",
                YELLOW_COLOR
            ),

            "cash_success": (
                "✅ 刷卡金兌換試算完成",
                GREEN_COLOR
            ),

            "cash_adjusted": (
                "⚠️ 已向下調整刷卡金金額",
                YELLOW_COLOR
            ),

            "bill_success": (
                "✅ 帳單折抵試算完成",
                GREEN_COLOR
            ),

            "bill_adjusted": (
                "⚠️ 已依帳單限制調整折抵金額",
                YELLOW_COLOR
            ),

            "bill_ineligible": (
                "❌ 本期帳單不符合折抵資格",
                RED_COLOR
            ),

            "insufficient": (
                "❌ 點數不足，無法兌換",
                RED_COLOR
            ),

            "below_minimum": (
                "❌ 未達最低兌換門檻",
                RED_COLOR
            ),

            "normal": (
                "兌換試算結果",
                "#333333"
            )
        }

        title, color = styles.get(
            status,
            styles["normal"]
        )

        self.status_label.config(
            text=title,
            fg=color
        )

        self.result_label.config(
            text=text
        )

        if scroll:

            self.root.after(
                100,
                self.scroll_to_result
            )


    # ========================================================
    # 25. 開始計算
    # ========================================================

    def calculate(self):

        rule = self.get_selected_rule()

        if rule is None:

            messagebox.showwarning(
                "缺少資料",
                "請先選擇有效的兌換項目"
            )

            return

        try:

            amount = parse_positive_integer(
                self.amount_var.get()
            )

        except ValueError:

            messagebox.showwarning(
                "輸入錯誤",
                "請輸入大於零的整數"
            )

            return

        reward = self.reward_var.get()
        mode = self.mode_var.get()
        point_type = self.point_var.get()

        try:

            # ------------------------------------------------
            # A. 航空哩程
            # ------------------------------------------------

            if reward == "航空哩程":

                airline = self.airline_var.get()

                basic = (
                    f"點數類型：{point_type}\n"
                    f"航空公司：{airline}\n"
                    f'兌換比例：'
                    f'{rule["points_required"]:,} 點 = '
                    f'{rule["miles_received"]:,} 哩\n\n'
                )

                if mode == "points":

                    result = points_to_miles(
                        amount,
                        rule
                    )

                    if not result["success"]:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點\n'
                            + f'還差：'
                            f'{result["missing_points"]:,} 點'
                        )

                        status = "insufficient"

                    else:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'可兌換哩程：'
                            f'{result["exchange_miles"]:,} 哩\n'
                            + f'實際扣除點數：'
                            f'{result["used_points"]:,} 點\n'
                            + f'剩餘點數：'
                            f'{result["remaining_points"]:,} 點'
                        )

                        status = "mileage_success"

                else:

                    result = mileage_to_points_target(
                        amount,
                        rule
                    )

                    output = (
                        basic
                        + f"目標哩程：{amount:,} 哩\n"
                        + f'實際需轉入哩程：'
                        f'{result["exchange_miles"]:,} 哩\n'
                        + f'所需點數：'
                        f'{result["required_points"]:,} 點\n'
                        + f'額外取得哩程：'
                        f'{result["extra_miles"]:,} 哩'
                    )

                    status = (
                        "mileage_adjusted"
                        if result["adjusted"]
                        else "mileage_success"
                    )

            # ------------------------------------------------
            # B. 刷卡金
            # ------------------------------------------------

            elif reward == "刷卡金":

                basic = (
                    f"點數類型：{point_type}\n"
                    f'兌換比例：'
                    f'{rule["points_required"]:,} 點 = '
                    f'NT${rule["cash_received"]:,}\n\n'
                )

                if mode == "points":

                    result = points_to_cash(
                        amount,
                        rule
                    )

                    if not result["success"]:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點\n'
                            + f'還差：'
                            f'{result["missing_points"]:,} 點'
                        )

                        status = "insufficient"

                    else:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'可兌換刷卡金：'
                            f'NT${result["cash"]:,}\n'
                            + f'實際扣除點數：'
                            f'{result["used_points"]:,} 點\n'
                            + f'剩餘點數：'
                            f'{result["remaining_points"]:,} 點'
                        )

                        status = "cash_success"

                else:

                    result = cash_to_points_floor(
                        amount,
                        rule
                    )

                    if not result["success"]:

                        output = (
                            basic
                            + f"希望折抵金額：NT${amount:,}\n"
                            + f'最低可兌換刷卡金：'
                            f'NT${result["minimum_cash"]:,}\n'
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點'
                        )

                        status = "below_minimum"

                    else:

                        output = (
                            basic
                            + f"希望折抵金額：NT${amount:,}\n"
                            + f'實際可兌換刷卡金：'
                            f'NT${result["actual_cash"]:,}\n'
                            + f'所需點數：'
                            f'{result["required_points"]:,} 點\n'
                            + f'未納入兌換金額：'
                            f'NT${result["difference"]:,}'
                        )

                        status = (
                            "cash_adjusted"
                            if result["adjusted"]
                            else "cash_success"
                        )

            # ------------------------------------------------
            # C. 帳單折抵（新增）
            # ------------------------------------------------

            else:

                try:

                    total_due = parse_nonnegative_integer(
                        self.total_due_var.get()
                    )

                    minimum_due = parse_nonnegative_integer(
                        self.minimum_due_var.get()
                    )

                except ValueError:

                    messagebox.showwarning(
                        "帳單資料錯誤",
                        "請輸入有效的帳單總應繳金額"
                        "與最低應繳金額（非負整數）。"
                    )

                    return

                restrictions = self.bill_data[
                    "restrictions"
                ]

                basic = (
                    f"點數類型：{point_type}\n"
                    f'兌換比例：'
                    f'{rule["points_required"]:,} 點 = '
                    f'NT${rule["cash_received"]:,}\n\n'
                    f"當期帳單總應繳：NT${total_due:,}\n"
                    f"最低應繳金額：NT${minimum_due:,}\n"
                )

                if mode == "points":

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

                basic += (
                    f'帳單差額：'
                    f'NT${result["bill_difference"]:,}\n\n'
                )

                if not result["success"]:

                    reason = result["reason"]

                    if reason == "bill_ineligible":

                        output = (
                            basic
                            + "本期帳單差額未達折抵資格。\n"
                            + f'官方差額門檻：'
                            f'須大於 NT${result["threshold"]:,}\n\n'
                            + "因此本期無法使用帳單折抵。"
                        )

                        status = "bill_ineligible"

                    elif reason == "insufficient_points":

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點\n'
                            + f'還差：'
                            f'{result["missing_points"]:,} 點'
                        )

                        status = "insufficient"

                    else:

                        output = (
                            basic
                            + "目前無法達到最低折抵門檻。\n"
                            + f'最低折抵金額：'
                            f'NT${result["minimum_cash"]:,}\n'
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點'
                        )

                        status = "below_minimum"

                else:

                    if mode == "points":

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'理論可折抵：'
                            f'NT${result["theoretical_cash"]:,}\n'
                            + f'帳單最高可折抵：'
                            f'NT${result["maximum_offset"]:,}\n\n'
                            + f'實際可折抵：'
                            f'NT${result["actual_cash"]:,}\n'
                            + f'實際使用點數：'
                            f'{result["used_points"]:,} 點\n'
                            + f'剩餘點數：'
                            f'{result["remaining_points"]:,} 點\n'
                            + f'折抵後帳單剩餘：'
                            f'NT${result["remaining_bill"]:,}'
                        )

                        adjusted = result["bill_limit_adjusted"]

                    else:

                        output = (
                            basic
                            + f"希望折抵金額：NT${amount:,}\n"
                            + f'帳單最高可折抵：'
                            f'NT${result["maximum_offset"]:,}\n\n'
                            + f'實際可折抵：'
                            f'NT${result["actual_cash"]:,}\n'
                            + f'所需點數：'
                            f'{result["required_points"]:,} 點\n'
                            + f'未納入折抵的目標金額：'
                            f'NT${result["difference"]:,}\n'
                            + f'折抵後帳單剩餘：'
                            f'NT${result["remaining_bill"]:,}'
                        )

                        adjusted = (
                            result["bill_limit_adjusted"]
                            or result["unit_adjusted"]
                        )

                    if adjusted:

                        output += (
                            "\n\n提醒：已依帳單最高折抵額"
                            "及兌換單位限制調整試算結果。"
                        )

                        status = "bill_adjusted"

                    else:

                        status = "bill_success"

                    output += (
                        "\n\n注意：以上為帳單折抵試算，"
                        "實際申請仍須符合銀行相關規定；"
                        "最低應繳金額不得以點數折抵。"
                    )

                    if mode == "target":

                        output += (
                            "\n本模式僅反推所需點數，"
                            "尚未確認客戶實際持有點數。"
                        )

            self.show_result(
                output,
                status,
                scroll=True
            )

        except (
            ValueError,
            ZeroDivisionError,
            KeyError
        ) as e:

            messagebox.showerror(
                "計算失敗",
                str(e)
            )


# ============================================================
# 26. 啟動程式
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = DBSApp(root)

    root.mainloop()