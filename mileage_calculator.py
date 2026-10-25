import json
import tkinter as tk

from pathlib import Path
from tkinter import ttk, messagebox


# ==================================================
# 1. 基本設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "data" / "dbs_rates.json"


# ==================================================
# 2. 載入兌換資料
# ==================================================

def load_rates():

    if not DATA_FILE.exists():

        raise FileNotFoundError(
            "找不到 dbs_rates.json\n"
            "請先執行 dbs_scraper.py"
        )

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if not isinstance(data, dict):

        raise ValueError(
            "兌換資料格式不正確"
        )

    rules = data.get("rules")

    if not isinstance(rules, list) or not rules:

        raise ValueError(
            "JSON 中沒有有效的兌換資料"
        )

    required_fields = [
        "point_type",
        "airline",
        "points_required",
        "miles_received",
        "minimum_miles",
        "miles_increment"
    ]

    seen = set()

    for rule in rules:

        if not isinstance(rule, dict):

            raise ValueError(
                "兌換規則格式不正確"
            )

        for field in required_fields:

            if field not in rule:

                raise ValueError(
                    f"兌換資料缺少欄位：{field}"
                )

        for field in required_fields[2:]:

            value = rule[field]

            if (
                type(value) is not int
                or value <= 0
            ):

                raise ValueError(
                    f"兌換資料數值錯誤：{field}"
                )

        key = (
            rule["point_type"],
            rule["airline"]
        )

        if key in seen:

            raise ValueError(
                f"發現重複兌換規則：{key}"
            )

        seen.add(key)

    return data


# ==================================================
# 3. 點數換算哩程
# ==================================================

def points_to_miles(points, rule):

    points_required = rule["points_required"]

    miles_received = rule["miles_received"]

    minimum = rule["minimum_miles"]

    step = rule["miles_increment"]

    # 最低所需點數
    minimum_points = (
        minimum * points_required
        + miles_received - 1
    ) // miles_received

    # 點數不足最低兌換門檻
    if points < minimum_points:

        return {
            "success": False,
            "minimum_points": minimum_points,
            "missing_points": minimum_points - points,
            "minimum_miles": minimum
        }

    # 理論可取得哩程
    raw_miles = (
        points * miles_received
    ) // points_required

    # 依兌換單位向下調整
    exchange_miles = (
        raw_miles // step
    ) * step

    # 再次確認最低門檻
    if exchange_miles < minimum:

        return {
            "success": False,
            "minimum_points": minimum_points,
            "missing_points": max(
                0,
                minimum_points - points
            ),
            "minimum_miles": minimum
        }

    # 實際使用點數
    used_points = (
        exchange_miles * points_required
        + miles_received - 1
    ) // miles_received

    remaining_points = points - used_points

    return {
        "success": True,
        "exchange_miles": exchange_miles,
        "used_points": used_points,
        "remaining_points": remaining_points,
        "minimum_miles": minimum
    }


# ==================================================
# 4. 哩程反推點數
# ==================================================

def miles_to_points(target_miles, rule):

    points_required = rule["points_required"]

    miles_received = rule["miles_received"]

    minimum = rule["minimum_miles"]

    step = rule["miles_increment"]

    # 先處理最低兌換門檻
    target = max(
        target_miles,
        minimum
    )

    # 依兌換倍數向上調整
    exchange_miles = (
        (target + step - 1) // step
    ) * step

    # 計算所需點數
    required_points = (
        exchange_miles * points_required
        + miles_received - 1
    ) // miles_received

    return {
        "exchange_miles": exchange_miles,
        "required_points": required_points,
        "adjusted": exchange_miles != target_miles,
        "minimum_miles": minimum
    }


# ==================================================
# 5. GUI 主視窗
# ==================================================

class MileageCalculatorApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "星展銀行信用卡哩程兌換計算機"
        )

        self.root.geometry("650x690")

        self.root.minsize(600, 650)

        self.root.configure(
            bg="#f4f7fb"
        )

        self.data = None
        self.rules = []

        self.point_var = tk.StringVar()

        self.airline_var = tk.StringVar()

        self.mode_var = tk.StringVar(
            value="points"
        )

        self.amount_var = tk.StringVar()

        self.rate_var = tk.StringVar()

        self.update_var = tk.StringVar()

        self.build_ui()

        self.reload_data()


    # ==========================================
    # 6. 建立介面
    # ==========================================

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="✈ 星展銀行哩程兌換計算機",
            font=("Microsoft JhengHei", 20, "bold"),
            bg="#f4f7fb",
            fg="#163a63"
        )

        title.pack(pady=(22, 8))

        subtitle = tk.Label(
            self.root,
            text="根據星展銀行官方兌換資料進行換算",
            font=("Microsoft JhengHei", 10),
            bg="#f4f7fb",
            fg="#666666"
        )

        subtitle.pack(pady=(0, 15))

        frame = tk.Frame(
            self.root,
            bg="white",
            padx=25,
            pady=20
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=5
        )

        # 點數類型
        tk.Label(
            frame,
            text="選擇點數類型",
            bg="white",
            font=("Microsoft JhengHei", 11)
        ).pack(anchor="w")

        self.point_combo = ttk.Combobox(
            frame,
            textvariable=self.point_var,
            state="readonly",
            font=("Microsoft JhengHei", 11)
        )

        self.point_combo.pack(
            fill="x",
            pady=(5, 15)
        )

        self.point_combo.bind(
            "<<ComboboxSelected>>",
            self.update_airlines
        )

        # 航空公司
        tk.Label(
            frame,
            text="選擇航空公司",
            bg="white",
            font=("Microsoft JhengHei", 11)
        ).pack(anchor="w")

        self.airline_combo = ttk.Combobox(
            frame,
            textvariable=self.airline_var,
            state="readonly",
            font=("Microsoft JhengHei", 11)
        )

        self.airline_combo.pack(
            fill="x",
            pady=(5, 15)
        )

        self.airline_combo.bind(
            "<<ComboboxSelected>>",
            self.update_rate
        )

        # 兌換比例
        tk.Label(
            frame,
            textvariable=self.rate_var,
            bg="white",
            fg="#2255aa",
            font=("Microsoft JhengHei", 11, "bold")
        ).pack(pady=(0, 15))

        # 換算模式
        tk.Label(
            frame,
            text="選擇換算方式",
            bg="white",
            font=("Microsoft JhengHei", 11)
        ).pack(anchor="w")

        mode_frame = tk.Frame(
            frame,
            bg="white"
        )

        mode_frame.pack(
            anchor="w",
            pady=8
        )

        tk.Radiobutton(
            mode_frame,
            text="點數 → 哩程",
            variable=self.mode_var,
            value="points",
            bg="white",
            command=self.update_mode
        ).pack(side="left", padx=(0, 20))

        tk.Radiobutton(
            mode_frame,
            text="哩程 → 點數",
            variable=self.mode_var,
            value="miles",
            bg="white",
            command=self.update_mode
        ).pack(side="left")

        # 輸入數量
        self.amount_label = tk.Label(
            frame,
            text="輸入目前擁有的點數",
            bg="white",
            font=("Microsoft JhengHei", 11)
        )

        self.amount_label.pack(
            anchor="w",
            pady=(12, 5)
        )

        self.amount_entry = ttk.Entry(
            frame,
            textvariable=self.amount_var,
            font=("Microsoft JhengHei", 12)
        )

        self.amount_entry.pack(
            fill="x",
            pady=(0, 15)
        )

        # 計算按鈕
        calculate_button = tk.Button(
            frame,
            text="開始計算",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="#2365a0",
            fg="white",
            activebackground="#164675",
            activeforeground="white",
            relief="flat",
            command=self.calculate
        )

        calculate_button.pack(
            fill="x",
            pady=(5, 15),
            ipady=8
        )

        # 結果顯示區
        self.result_text = tk.Text(
            frame,
            height=11,
            font=("Microsoft JhengHei", 11),
            bg="#f1f5fa",
            fg="#222222",
            relief="flat",
            padx=15,
            pady=12,
            wrap="word",
            state="disabled"
        )

        self.result_text.pack(
            fill="both",
            expand=True
        )

        # 更新時間
        tk.Label(
            self.root,
            textvariable=self.update_var,
            bg="#f4f7fb",
            fg="#777777",
            font=("Microsoft JhengHei", 9)
        ).pack(pady=(5, 2))

        # 重新讀取資料
        tk.Button(
            self.root,
            text="重新讀取兌換資料",
            command=self.reload_data,
            relief="flat",
            bg="#e0e6ef"
        ).pack(pady=(0, 12))


    # ==========================================
    # 7. 重新讀取 JSON
    # ==========================================

    def reload_data(self):

        try:

            data = load_rates()

            self.data = data

            self.rules = data["rules"]

            point_types = list(
                dict.fromkeys(
                    rule["point_type"]
                    for rule in self.rules
                )
            )

            self.point_combo["values"] = point_types

            self.point_var.set(point_types[0])

            self.update_airlines()

            self.update_var.set(
                "資料更新時間："
                + str(data.get("fetched_at", "未知"))
            )

            self.show_result(
                "兌換資料載入成功！\n\n"
                "請選擇點數類型、航空公司，"
                "並輸入欲換算的數量。"
            )

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError,
            OSError
        ) as e:

            messagebox.showerror(
                "資料載入失敗",
                str(e)
            )


    # ==========================================
    # 8. 更新航空公司選單
    # ==========================================

    def update_airlines(self, event=None):

        point_type = self.point_var.get()

        airlines = list(
            dict.fromkeys(
                rule["airline"]
                for rule in self.rules
                if rule["point_type"] == point_type
            )
        )

        self.airline_combo["values"] = airlines

        if airlines:

            self.airline_var.set(airlines[0])

        else:

            self.airline_var.set("")

        self.update_rate()


    # ==========================================
    # 9. 尋找兌換規則
    # ==========================================

    def get_selected_rule(self):

        point_type = self.point_var.get()

        airline = self.airline_var.get()

        for rule in self.rules:

            if (
                rule["point_type"] == point_type
                and rule["airline"] == airline
            ):

                return rule

        return None


    # ==========================================
    # 10. 更新比例顯示
    # ==========================================

    def update_rate(self, event=None):

        rule = self.get_selected_rule()

        if rule:

            self.rate_var.set(
                f'兌換比例：'
                f'{rule["points_required"]:,} 點 '
                f'= {rule["miles_received"]:,} 哩'
            )

        else:

            self.rate_var.set(
                "無可用兌換比例"
            )


    # ==========================================
    # 11. 更新換算模式
    # ==========================================

    def update_mode(self):

        if self.mode_var.get() == "points":

            self.amount_label.config(
                text="輸入目前擁有的點數"
            )

        else:

            self.amount_label.config(
                text="輸入希望取得的哩程"
            )

        self.amount_var.set("")

        self.show_result("")


    # ==========================================
    # 12. 顯示計算結果
    # ==========================================

    def show_result(self, text):

        self.result_text.config(
            state="normal"
        )

        self.result_text.delete(
            "1.0",
            tk.END
        )

        self.result_text.insert(
            tk.END,
            text
        )

        self.result_text.config(
            state="disabled"
        )


    # ==========================================
    # 13. 執行計算
    # ==========================================

    def calculate(self):

        rule = self.get_selected_rule()

        if rule is None:

            messagebox.showwarning(
                "缺少資料",
                "請先選擇點數類型與航空公司"
            )

            return

        try:

            amount = int(
                self.amount_var.get().replace(",", "").strip()
            )

            if amount <= 0:

                raise ValueError

        except ValueError:

            messagebox.showwarning(
                "輸入錯誤",
                "請輸入大於 0 的整數"
            )

            return

        point_type = rule["point_type"]

        airline = rule["airline"]

        ratio = (
            f'{rule["points_required"]:,} 點 '
            f'= {rule["miles_received"]:,} 哩'
        )

        # --------------------------------------
        # 模式 A：點數換哩程
        # --------------------------------------

        if self.mode_var.get() == "points":

            result = points_to_miles(
                amount,
                rule
            )

            if result["success"]:

                output = (
                    "✅ 符合兌換門檻\n\n"
                    f"點數類型：{point_type}\n"
                    f"航空公司：{airline}\n"
                    f"兌換比例：{ratio}\n\n"
                    f"目前點數：{amount:,} 點\n"
                    f"可兌換哩程："
                    f'{result["exchange_miles"]:,} 哩\n'
                    f"實際扣除點數："
                    f'{result["used_points"]:,} 點\n'
                    f"剩餘點數："
                    f'{result["remaining_points"]:,} 點'
                )

            else:

                output = (
                    "❌ 目前無法兌換\n\n"
                    f"點數類型：{point_type}\n"
                    f"航空公司：{airline}\n"
                    f"兌換比例：{ratio}\n\n"
                    f"目前點數：{amount:,} 點\n"
                    f"最低兌換門檻："
                    f'{result["minimum_miles"]:,} 哩\n'
                    f"最低所需點數："
                    f'{result["minimum_points"]:,} 點\n'
                    f"還差："
                    f'{result["missing_points"]:,} 點'
                )

        # --------------------------------------
        # 模式 B：哩程換點數
        # --------------------------------------

        else:

            result = miles_to_points(
                amount,
                rule
            )

            output = (
                "✅ 目標哩程換算結果\n\n"
                f"點數類型：{point_type}\n"
                f"航空公司：{airline}\n"
                f"兌換比例：{ratio}\n\n"
                f"目標哩程：{amount:,} 哩\n"
                f"實際兌換哩程："
                f'{result["exchange_miles"]:,} 哩\n'
                f"所需點數："
                f'{result["required_points"]:,} 點'
            )

            if result["adjusted"]:

                output += (
                    "\n\n⚠️ 因最低兌換門檻"
                    "或兌換單位限制，"
                    "已向上調整實際兌換哩程。"
                )

        self.show_result(output)


# ==================================================
# 14. 啟動程式
# ==================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = MileageCalculatorApp(root)

    root.mainloop()