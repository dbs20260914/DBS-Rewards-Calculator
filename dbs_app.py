import json
import tkinter as tk
import webbrowser

from pathlib import Path
from tkinter import ttk, messagebox


# ============================================================
# 1. 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MILEAGE_FILE = BASE_DIR / "data" / "dbs_rates.json"
CASH_FILE = BASE_DIR / "data" / "dbs_cash_rates.json"

DBS_BASE_URL = (
    "https://www.dbs.com.tw/"
    "personal-zh/cards/rewards/"
)


# ============================================================
# 2. 航空哩程官方資料來源
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
# 3. 刷卡金官方資料來源
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
# 4. 介面設定
# ============================================================

BG_COLOR = "#f3f6fb"
BLUE_COLOR = "#286aa5"
GREEN_COLOR = "#167a45"
RED_COLOR = "#bb3030"
YELLOW_COLOR = "#a16a00"

FONT_NAME = "Microsoft JhengHei"


# ============================================================
# 5. 點數類型文字標準化
# ============================================================

def normalize_point_type(point_type):

    return (
        point_type
        .strip()
        .replace(" ", "")
        .replace("　", "")
        .replace("／", "/")
        .replace("（", "(")
        .replace("）", ")")
    )


# ============================================================
# 6. 讀取 JSON 資料
# ============================================================

def load_json(path, reward_type):

    if not path.exists():

        raise FileNotFoundError(
            f"找不到資料檔案：{path.name}\n"
            "請先執行對應的爬蟲程式。"
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

        numeric_fields = [
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

        numeric_fields = [
            "points_required",
            "cash_received",
            "minimum_points",
            "points_increment"
        ]

    seen = set()

    for rule in rules:

        if not isinstance(rule, dict):

            raise ValueError(
                "兌換規則格式錯誤"
            )

        for field in required_fields:

            if field not in rule:

                raise ValueError(
                    f"{path.name} 缺少欄位：{field}"
                )

        for field in numeric_fields:

            value = rule[field]

            if type(value) is not int or value <= 0:

                raise ValueError(
                    f"{path.name} 數值異常：{field}"
                )

        if (
            not isinstance(rule["point_type"], str)
            or not rule["point_type"].strip()
        ):

            raise ValueError(
                "點數類型格式錯誤"
            )

        if reward_type == "mileage":

            if (
                not isinstance(rule["airline"], str)
                or not rule["airline"].strip()
            ):

                raise ValueError(
                    "航空公司名稱格式錯誤"
                )

            key = (
                rule["point_type"],
                rule["airline"]
            )

        else:

            key = rule["point_type"]

            numerator = (
                rule["points_increment"]
                * rule["cash_received"]
            )

            if numerator % rule["points_required"] != 0:

                raise ValueError(
                    f"刷卡金兌換單位與比例不相容：{key}"
                )

        if key in seen:

            raise ValueError(
                f"發現重複兌換規則：{key}"
            )

        seen.add(key)

    return data


# ============================================================
# 7. 數學輔助函式
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


# ============================================================
# 8. 點數 → 航空哩程（向下取整）
# ============================================================

def points_to_miles(points, rule):

    required = rule["points_required"]
    received = rule["miles_received"]

    minimum = rule["minimum_miles"]
    step = rule["miles_increment"]

    minimum_miles = minimum_valid_amount(
        minimum,
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

    if exchange_miles < minimum_miles:

        return {
            "success": False,
            "minimum_miles": minimum_miles,
            "minimum_points": minimum_points,
            "missing_points": max(
                0,
                minimum_points - points
            )
        }

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
# 9. 目標哩程 → 點數（向上取整）
# ============================================================

def mileage_to_points_target(target_miles, rule):

    required = rule["points_required"]
    received = rule["miles_received"]

    minimum = rule["minimum_miles"]
    step = rule["miles_increment"]

    minimum_exchange = minimum_valid_amount(
        minimum,
        step
    )

    target_exchange = minimum_valid_amount(
        target_miles,
        step
    )

    exchange_miles = max(
        minimum_exchange,
        target_exchange
    )

    required_points = ceil_div(
        exchange_miles * required,
        received
    )

    extra_miles = exchange_miles - target_miles

    return {
        "success": True,
        "target_miles": target_miles,
        "exchange_miles": exchange_miles,
        "required_points": required_points,
        "extra_miles": extra_miles,
        "below_minimum": target_miles < minimum_exchange,
        "adjusted": extra_miles > 0,
        "minimum_miles": minimum_exchange
    }


# ============================================================
# 10. 點數 → 刷卡金（向下取整）
# ============================================================

def points_to_cash(points, rule):

    required = rule["points_required"]
    cash = rule["cash_received"]

    minimum = rule["minimum_points"]
    step = rule["points_increment"]

    minimum_required = minimum_valid_amount(
        minimum,
        step
    )

    if points < minimum_required:

        return {
            "success": False,
            "minimum_points": minimum_required,
            "missing_points": minimum_required - points
        }

    used_points = (
        points // step
    ) * step

    numerator = used_points * cash

    if numerator % required != 0:

        raise ValueError(
            "刷卡金兌換金額無法換算為整數"
        )

    exchange_cash = numerator // required

    return {
        "success": True,
        "cash": exchange_cash,
        "used_points": used_points,
        "remaining_points": points - used_points
    }


# ============================================================
# 11. 目標刷卡金 → 點數（向下取整）
# ============================================================

def cash_to_points_floor(target_cash, rule):

    required = rule["points_required"]
    cash = rule["cash_received"]

    minimum = rule["minimum_points"]
    step = rule["points_increment"]

    numerator = step * cash

    if numerator % required != 0:

        raise ValueError(
            "刷卡金兌換單位與比例不相容"
        )

    cash_per_step = numerator // required

    minimum_points = minimum_valid_amount(
        minimum,
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
        "adjusted": actual_cash != target_cash,
        "difference": target_cash - actual_cash,
        "minimum_cash": minimum_cash
    }


# ============================================================
# 12. GUI 主程式
# ============================================================

class DBSApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "星展銀行信用卡點數兌換計算機"
        )

        self.root.geometry("850x850")
        self.root.minsize(700, 600)

        self.root.configure(bg=BG_COLOR)

        self.mileage_data = None
        self.cash_data = None

        self.airline_frame = None
        self.airline_combo = None

        self.reward_var = tk.StringVar(
            value="航空哩程"
        )

        self.point_var = tk.StringVar()
        self.airline_var = tk.StringVar()

        self.mode_var = tk.StringVar(
            value="points"
        )

        self.amount_var = tk.StringVar()

        self.ratio_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.info_var = tk.StringVar()

        self.current_source_url = None

        self.build_ui()
        self.load_data()


    # ========================================================
    # 13. 建立可捲動介面（本次主要修改）
    # ========================================================

    def build_ui(self):

        # ----------------------------------------------------
        # 主標題
        # ----------------------------------------------------

        tk.Label(
            self.root,
            text="星展銀行信用卡點數兌換計算機",
            font=(FONT_NAME, 20, "bold"),
            bg=BG_COLOR,
            fg="#173d65"
        ).pack(
            pady=(18, 7)
        )

        tk.Label(
            self.root,
            text="航空哩程 / 刷卡金雙向換算",
            font=(FONT_NAME, 11),
            bg=BG_COLOR,
            fg="#777777"
        ).pack(
            pady=(0, 12)
        )

        # ====================================================
        # 可捲動容器
        # ====================================================

        self.canvas_container = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        self.canvas_container.pack(
            fill="both",
            expand=True
        )

        # Canvas
        self.canvas = tk.Canvas(
            self.canvas_container,
            bg=BG_COLOR,
            highlightthickness=0
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        # 右側捲軸
        self.scrollbar = ttk.Scrollbar(
            self.canvas_container,
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

        # 真正放置所有元件的 Frame
        self.scrollable_frame = tk.Frame(
            self.canvas,
            bg=BG_COLOR
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        # 當內容高度改變，更新捲動範圍
        self.scrollable_frame.bind(
            "<Configure>",
            self.on_frame_configure
        )

        # 當視窗寬度改變，讓內部 Frame 一起變寬
        self.canvas.bind(
            "<Configure>",
            self.on_canvas_configure
        )

        # Windows 滑鼠滾輪
        self.root.bind_all(
            "<MouseWheel>",
            self.on_mousewheel
        )

        # ----------------------------------------------------
        # 主內容區
        # ----------------------------------------------------

        frame = tk.Frame(
            self.scrollable_frame,
            bg="white",
            padx=25,
            pady=18
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=5
        )

        # ----------------------------------------------------
        # 選擇區域
        # ----------------------------------------------------

        self.selection_frame = tk.Frame(
            frame,
            bg="white"
        )

        self.selection_frame.pack(fill="x")

        self.selection_frame.columnconfigure(
            0,
            weight=1
        )

        # 兌換類別
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
                "刷卡金"
            ],
            state="readonly",
            font=(FONT_NAME, 10)
        )

        self.reward_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 13)
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
            state="readonly",
            font=(FONT_NAME, 10)
        )

        self.point_combo.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(5, 13)
        )

        self.point_combo.bind(
            "<<ComboboxSelected>>",
            self.update_airlines
        )

        # ----------------------------------------------------
        # 兌換資訊區塊
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

        self.ratio_label = tk.Label(
            info_frame,
            textvariable=self.ratio_var,
            bg="#eef4fc",
            fg="#194c81",
            font=(FONT_NAME, 11, "bold"),
            justify="left",
            anchor="w"
        )

        self.ratio_label.pack(
            fill="x",
            anchor="w"
        )

        ttk.Separator(
            info_frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=(12, 10)
        )

        # ----------------------------------------------------
        # 官方資料來源
        # ----------------------------------------------------

        self.source_label = tk.Label(
            info_frame,
            textvariable=self.source_var,
            bg="#eef4fc",
            fg="#555555",
            font=(FONT_NAME, 10),
            anchor="w",
            justify="left"
        )

        self.source_label.pack(
            fill="x",
            anchor="w",
            pady=(0, 8)
        )

        self.source_button = tk.Button(
            info_frame,
            text="🔗 開啟對應的星展銀行官方兌換頁面",
            font=(FONT_NAME, 10, "bold"),
            bg="#dbe8f8",
            fg="#194c81",
            activebackground="#c8dbf2",
            relief="flat",
            cursor="hand2",
            command=self.open_official_source
        )

        self.source_button.pack(
            fill="x",
            ipady=5
        )

        # ----------------------------------------------------
        # 換算方式
        # ----------------------------------------------------

        tk.Label(
            frame,
            text="選擇換算方式",
            bg="white",
            font=(FONT_NAME, 10)
        ).pack(
            anchor="w"
        )

        mode_frame = tk.Frame(
            frame,
            bg="white"
        )

        mode_frame.pack(
            anchor="w",
            pady=8
        )

        self.points_radio = tk.Radiobutton(
            mode_frame,
            variable=self.mode_var,
            value="points",
            bg="white",
            font=(FONT_NAME, 10),
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
            font=(FONT_NAME, 10),
            command=self.on_mode_change
        )

        self.target_radio.pack(side="left")

        # ----------------------------------------------------
        # 輸入數量
        # ----------------------------------------------------

        self.amount_label = tk.Label(
            frame,
            bg="white",
            font=(FONT_NAME, 10)
        )

        self.amount_label.pack(
            anchor="w",
            pady=(8, 5)
        )

        self.amount_entry = ttk.Entry(
            frame,
            textvariable=self.amount_var,
            font=(FONT_NAME, 11)
        )

        self.amount_entry.pack(
            fill="x",
            pady=(0, 13)
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
            activebackground="#174d7c",
            activeforeground="white",
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
            font=(FONT_NAME, 12, "bold"),
            bg="#f1f5fa",
            fg="#333333",
            anchor="w",
            padx=15,
            pady=10
        )

        self.status_label.pack(fill="x")

        # 改用 Label 顯示結果，讓高度隨內容自動增加
        self.result_label = tk.Label(
            frame,
            text="",
            font=(FONT_NAME, 11),
            bg="#f1f5fa",
            fg="#222222",
            justify="left",
            anchor="nw",
            padx=15,
            pady=12
        )

        self.result_label.pack(
            fill="x"
        )

        # ----------------------------------------------------
        # 資料更新時間
        # ----------------------------------------------------

        self.footer_frame = tk.Frame(
            self.scrollable_frame,
            bg=BG_COLOR
        )

        self.footer_frame.pack(
            fill="x",
            pady=(5, 15)
        )

        tk.Label(
            self.footer_frame,
            textvariable=self.info_var,
            bg=BG_COLOR,
            fg="#777777",
            font=(FONT_NAME, 9),
            justify="center"
        ).pack(
            pady=(5, 8)
        )

        tk.Button(
            self.footer_frame,
            text="重新讀取本機兌換資料",
            font=(FONT_NAME, 10),
            command=self.load_data
        ).pack(
            pady=(0, 10)
        )


    # ========================================================
    # 14. 更新捲動範圍
    # ========================================================

    def on_frame_configure(self, event=None):

        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )


    # ========================================================
    # 15. 更新內容寬度
    # ========================================================

    def on_canvas_configure(self, event):

        self.canvas.itemconfigure(
            self.canvas_window,
            width=event.width
        )


    # ========================================================
    # 16. 滑鼠滾輪控制
    # ========================================================

    def on_mousewheel(self, event):

        if self.canvas.winfo_height() <= 0:
            return

        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )


    # ========================================================
    # 17. 自動捲動至結果
    # ========================================================

    def scroll_to_result(self):

        self.root.update_idletasks()

        content_height = (
            self.scrollable_frame.winfo_height()
        )

        canvas_height = (
            self.canvas.winfo_height()
        )

        if content_height <= canvas_height:
            return

        # 取得結果區域在捲動 Frame 中的位置
        result_y = (
            self.status_label.winfo_rooty()
            - self.scrollable_frame.winfo_rooty()
        )

        max_scroll = content_height - canvas_height

        target_scroll = min(
            result_y - 30,
            max_scroll
        )

        scroll_fraction = (
            target_scroll / max_scroll
        )

        self.canvas.yview_moveto(
            max(0, scroll_fraction)
        )


    # ========================================================
    # 18. 動態建立航空公司選單
    # ========================================================

    def create_airline_selector(self):

        self.destroy_airline_selector()

        self.airline_frame = tk.Frame(
            self.selection_frame,
            bg="white"
        )

        self.airline_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        self.airline_frame.columnconfigure(
            0,
            weight=1
        )

        tk.Label(
            self.airline_frame,
            text="選擇航空公司",
            bg="white",
            font=(FONT_NAME, 10)
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.airline_combo = ttk.Combobox(
            self.airline_frame,
            textvariable=self.airline_var,
            state="readonly",
            font=(FONT_NAME, 10)
        )

        self.airline_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 10)
        )

        self.airline_combo.bind(
            "<<ComboboxSelected>>",
            self.on_airline_change
        )


    # ========================================================
    # 19. 刪除航空公司選單
    # ========================================================

    def destroy_airline_selector(self):

        if self.airline_frame is not None:

            self.airline_frame.destroy()

            self.airline_frame = None
            self.airline_combo = None

        self.airline_var.set("")


    # ========================================================
    # 20. 取得官方資料來源
    # ========================================================

    def get_official_source(self):

        reward = self.reward_var.get()

        point_type = normalize_point_type(
            self.point_var.get()
        )

        if reward == "航空哩程":

            sources = DBS_MILEAGE_SOURCES

        else:

            sources = DBS_CASH_SOURCES

        for name, source in sources.items():

            normalized_name = normalize_point_type(
                name
            )

            if point_type == normalized_name:

                return source

        return None


    # ========================================================
    # 21. 開啟官方資料來源
    # ========================================================

    def open_official_source(self):

        source = self.get_official_source()

        if source is None:

            messagebox.showwarning(
                "沒有對應來源",
                "目前沒有找到此點數類型的專屬官方頁面。"
            )

            return

        url = source["url"]

        try:

            opened = webbrowser.open(
                url,
                new=2
            )

            if not opened:

                messagebox.showwarning(
                    "瀏覽器開啟失敗",
                    "無法自動開啟瀏覽器，"
                    "請確認預設瀏覽器設定。"
                )

        except Exception as e:

            messagebox.showerror(
                "開啟失敗",
                f"無法開啟官方頁面：{e}"
            )


    # ========================================================
    # 22. 更新官方資料來源顯示
    # ========================================================

    def update_source(self):

        source = self.get_official_source()

        if source is None:

            self.current_source_url = None

            self.source_var.set(
                "官方資料來源：尚未建立對應頁面"
            )

            self.source_button.config(
                state="disabled"
            )

            return

        self.current_source_url = source["url"]

        self.source_var.set(
            f'官方資料來源：{source["name"]}'
        )

        self.source_button.config(
            state="normal"
        )


    # ========================================================
    # 23. 載入資料
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

            self.mileage_data = mileage
            self.cash_data = cash

            self.update_reward_type()

            mileage_time = mileage.get(
                "fetched_at",
                "未知"
            )

            cash_time = cash.get(
                "fetched_at",
                "未知"
            )

            self.info_var.set(
                f"哩程資料更新：{mileage_time}\n"
                f"刷卡金資料更新：{cash_time}"
            )

            self.show_result(
                "兌換資料載入成功，"
                "請選擇項目並輸入數量。",
                scroll=False
            )

        except (
            FileNotFoundError,
            ValueError,
            json.JSONDecodeError,
            OSError
        ) as e:

            messagebox.showerror(
                "資料載入失敗",
                str(e)
            )


    # ========================================================
    # 24. 切換兌換類別
    # ========================================================

    def update_reward_type(self, event=None):

        if (
            self.mileage_data is None
            or self.cash_data is None
        ):

            return

        reward = self.reward_var.get()

        if reward == "航空哩程":

            self.create_airline_selector()

            rules = self.mileage_data["rules"]

            point_types = list(
                dict.fromkeys(
                    rule["point_type"]
                    for rule in rules
                )
            )

        else:

            self.destroy_airline_selector()

            rules = self.cash_data["rules"]

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
    # 25. 更新航空公司
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

            if self.airline_combo is None:

                self.create_airline_selector()

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
    # 26. 尋找兌換規則
    # ========================================================

    def get_selected_rule(self):

        if (
            self.mileage_data is None
            or self.cash_data is None
        ):

            return None

        point_type = self.point_var.get()

        if self.reward_var.get() == "航空哩程":

            airline = self.airline_var.get()

            for rule in self.mileage_data["rules"]:

                if (
                    rule["point_type"] == point_type
                    and rule["airline"] == airline
                ):

                    return rule

        else:

            for rule in self.cash_data["rules"]:

                if rule["point_type"] == point_type:

                    return rule

        return None


    # ========================================================
    # 27. 更新比例、門檻及兌換單位
    # ========================================================

    def update_ratio(self):

        rule = self.get_selected_rule()

        if rule is None:

            self.ratio_var.set(
                "無可用兌換資料"
            )

            return

        if self.reward_var.get() == "航空哩程":

            points_required = rule[
                "points_required"
            ]

            miles_received = rule[
                "miles_received"
            ]

            minimum_miles = rule[
                "minimum_miles"
            ]

            miles_increment = rule[
                "miles_increment"
            ]

            minimum_exchange = minimum_valid_amount(
                minimum_miles,
                miles_increment
            )

            minimum_points = ceil_div(
                minimum_exchange * points_required,
                miles_received
            )

            display_text = (
                f"兌換比例："
                f"{points_required:,} 點 = "
                f"{miles_received:,} 哩\n"
                f"最低兌換門檻："
                f"{minimum_exchange:,} 哩"
                f"（需 {minimum_points:,} 點）\n"
                f"兌換單位：每 {miles_increment:,} 哩"
            )

        else:

            points_required = rule[
                "points_required"
            ]

            cash_received = rule[
                "cash_received"
            ]

            minimum_points = rule[
                "minimum_points"
            ]

            points_increment = rule[
                "points_increment"
            ]

            minimum_exchange_points = minimum_valid_amount(
                minimum_points,
                points_increment
            )

            numerator = (
                minimum_exchange_points
                * cash_received
            )

            if numerator % points_required != 0:

                raise ValueError(
                    "最低刷卡金金額無法換算為整數"
                )

            minimum_cash = (
                numerator // points_required
            )

            display_text = (
                f"兌換比例："
                f"{points_required:,} 點 = "
                f"NT${cash_received:,}\n"
                f"最低兌換門檻："
                f"{minimum_exchange_points:,} 點"
                f"（NT${minimum_cash:,}）\n"
                f"兌換單位：每 {points_increment:,} 點"
            )

        self.ratio_var.set(display_text)


    # ========================================================
    # 28. 更新換算方式
    # ========================================================

    def update_mode(self):

        reward = self.reward_var.get()

        if reward == "航空哩程":

            self.points_radio.config(
                text="點數 → 哩程"
            )

            self.target_radio.config(
                text="哩程 → 點數"
            )

        else:

            self.points_radio.config(
                text="點數 → 刷卡金"
            )

            self.target_radio.config(
                text="刷卡金 → 點數"
            )

        if self.mode_var.get() == "points":

            self.amount_label.config(
                text="輸入目前擁有的點數"
            )

        elif reward == "航空哩程":

            self.amount_label.config(
                text="輸入希望取得的哩程"
            )

        else:

            self.amount_label.config(
                text="輸入希望折抵的刷卡金（NT$）"
            )


    def on_mode_change(self):

        self.update_mode()

        self.amount_var.set("")

        self.show_result("")


    # ========================================================
    # 29. 顯示計算結果
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
    # 30. 開始計算
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

            amount = int(
                self.amount_var.get()
                .replace(",", "")
                .strip()
            )

            if amount <= 0:

                raise ValueError

        except ValueError:

            messagebox.showwarning(
                "輸入錯誤",
                "請輸入大於 0 的整數"
            )

            return

        reward = self.reward_var.get()
        mode = self.mode_var.get()
        point_type = self.point_var.get()

        try:

            # ==================================================
            # A. 航空哩程
            # ==================================================

            if reward == "航空哩程":

                airline = self.airline_var.get()

                ratio = (
                    f'{rule["points_required"]:,} 點 = '
                    f'{rule["miles_received"]:,} 哩'
                )

                basic = (
                    f"點數類型：{point_type}\n"
                    f"航空公司：{airline}\n"
                    f"兌換比例：{ratio}\n\n"
                )

                # ------------------------------------------------
                # 點數 → 哩程
                # ------------------------------------------------

                if mode == "points":

                    result = points_to_miles(
                        amount,
                        rule
                    )

                    if result["success"]:

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

                        self.show_result(
                            output,
                            "mileage_success",
                            scroll=True
                        )

                    else:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'最低兌換門檻：'
                            f'{result["minimum_miles"]:,} 哩\n'
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點\n'
                            + f'還差：'
                            f'{result["missing_points"]:,} 點'
                        )

                        self.show_result(
                            output,
                            "insufficient",
                            scroll=True
                        )

                # ------------------------------------------------
                # 目標哩程 → 點數
                # ------------------------------------------------

                else:

                    result = mileage_to_points_target(
                        amount,
                        rule
                    )

                    output = (
                        basic
                        + f"目標哩程：{amount:,} 哩\n"
                        + f'最低兌換門檻：'
                        f'{result["minimum_miles"]:,} 哩\n'
                        + f'兌換單位：'
                        f'{rule["miles_increment"]:,} 哩\n\n'
                        + f'實際需轉入哩程：'
                        f'{result["exchange_miles"]:,} 哩\n'
                        + f'所需信用卡點數：'
                        f'{result["required_points"]:,} 點\n'
                        + f'額外取得哩程：'
                        f'{result["extra_miles"]:,} 哩'
                    )

                    if result["below_minimum"]:

                        output += (
                            "\n\n提醒：原始目標低於"
                            "銀行最低兌換門檻。"
                            "\n以上為符合最低門檻的"
                            "轉點試算方案。"
                        )

                        self.show_result(
                            output,
                            "mileage_adjusted",
                            scroll=True
                        )

                    elif result["adjusted"]:

                        output += (
                            "\n\n提醒：因兌換單位限制，"
                            "已向上調整轉入哩程。"
                        )

                        self.show_result(
                            output,
                            "mileage_adjusted",
                            scroll=True
                        )

                    else:

                        self.show_result(
                            output,
                            "mileage_success",
                            scroll=True
                        )

            # ==================================================
            # B. 刷卡金
            # ==================================================

            else:

                ratio = (
                    f'{rule["points_required"]:,} 點 = '
                    f'NT${rule["cash_received"]:,}'
                )

                basic = (
                    f"點數類型：{point_type}\n"
                    f"兌換比例：{ratio}\n\n"
                )

                # ------------------------------------------------
                # 點數 → 刷卡金
                # ------------------------------------------------

                if mode == "points":

                    result = points_to_cash(
                        amount,
                        rule
                    )

                    if result["success"]:

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

                        self.show_result(
                            output,
                            "cash_success",
                            scroll=True
                        )

                    else:

                        output = (
                            basic
                            + f"目前點數：{amount:,} 點\n"
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點\n'
                            + f'還差：'
                            f'{result["missing_points"]:,} 點'
                        )

                        self.show_result(
                            output,
                            "insufficient",
                            scroll=True
                        )

                # ------------------------------------------------
                # 目標刷卡金 → 點數
                # ------------------------------------------------

                else:

                    result = cash_to_points_floor(
                        amount,
                        rule
                    )

                    if not result["success"]:

                        output = (
                            basic
                            + f"希望折抵金額：NT${amount:,}\n"
                            + "目前低於最低兌換門檻。\n\n"
                            + f'最低可兌換刷卡金：'
                            f'NT${result["minimum_cash"]:,}\n'
                            + f'最低所需點數：'
                            f'{result["minimum_points"]:,} 點'
                        )

                        self.show_result(
                            output,
                            "below_minimum",
                            scroll=True
                        )

                    else:

                        output = (
                            basic
                            + f"希望折抵金額：NT${amount:,}\n"
                            + f'實際可兌換刷卡金：'
                            f'NT${result["actual_cash"]:,}\n'
                            + f'所需信用卡點數：'
                            f'{result["required_points"]:,} 點\n'
                            + f'尚未折抵金額：'
                            f'NT${result["difference"]:,}'
                        )

                        if result["adjusted"]:

                            output += (
                                "\n\n提醒：依兌換單位"
                                "向下調整，"
                                "不會超過希望折抵的金額。"
                            )

                            self.show_result(
                                output,
                                "cash_adjusted",
                                scroll=True
                            )

                        else:

                            self.show_result(
                                output,
                                "cash_success",
                                scroll=True
                            )

        except (ValueError, ZeroDivisionError) as e:

            messagebox.showerror(
                "換算失敗",
                f"兌換規則或計算資料異常：{e}"
            )


# ============================================================
# 31. 啟動程式
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = DBSApp(root)

    root.mainloop()