import tkinter as tk
from tkinter import ttk, messagebox


class CampaignApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marketing Campaign Registration")
        self.root.geometry("900x520")
        self.root.minsize(820, 480)

        self.next_id = 1

        self.campaign_var = tk.StringVar()
        self.marketer_var = tk.StringVar()
        self.channel_var = tk.StringVar()
        self.priority_var = tk.StringVar()

        self.build_form()
        self.build_table()
        self.bind_events()
        # self.load_sample_data()
        self.update_add_button_state()

    def build_form(self):
        form_frame = ttk.LabelFrame(self.root, text="Campaign Registration", padding=15)
        form_frame.pack(fill="x", padx=12, pady=12)

        ttk.Label(form_frame, text="Campaign:").grid(row=0, column=0, sticky="w", padx=5, pady=6)
        self.campaign_entry = ttk.Entry(form_frame, textvariable=self.campaign_var, width=35)
        self.campaign_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=6)

        ttk.Label(form_frame, text="Marketer:").grid(row=0, column=2, sticky="w", padx=5, pady=6)
        self.marketer_entry = ttk.Entry(form_frame, textvariable=self.marketer_var, width=35)
        self.marketer_entry.grid(row=0, column=3, sticky="ew", padx=5, pady=6)

        ttk.Label(form_frame, text="Channel:").grid(row=1, column=0, sticky="w", padx=5, pady=6)
        self.channel_combo = ttk.Combobox(
            form_frame,
            textvariable=self.channel_var,
            state="readonly",
            values=["Email", "Social Media", "Ads"],
            width=32
        )
        self.channel_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=6)

        ttk.Label(form_frame, text="Priority:").grid(row=1, column=2, sticky="w", padx=5, pady=6)
        self.priority_combo = ttk.Combobox(
            form_frame,
            textvariable=self.priority_var,
            state="readonly",
            values=["Low", "Medium", "High"],
            width=32
        )
        self.priority_combo.grid(row=1, column=3, sticky="ew", padx=5, pady=6)

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(12, 0))

        self.add_button = ttk.Button(button_frame, text="Add", command=self.add_campaign)
        self.add_button.pack(side="left", padx=(0, 8))

        self.clear_button = ttk.Button(button_frame, text="Clear Form", command=self.clear_form)
        self.clear_button.pack(side="left")

        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

    def build_table(self):
        table_frame = ttk.LabelFrame(self.root, text="Registered Campaigns", padding=10)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("id", "campaign", "marketer", "channel", "priority", "status")

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
        self.tree.heading("id", text="ID")
        self.tree.heading("campaign", text="Campaign")
        self.tree.heading("marketer", text="Marketer")
        self.tree.heading("channel", text="Channel")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("campaign", width=220, anchor="w")
        self.tree.column("marketer", width=170, anchor="w")
        self.tree.column("channel", width=130, anchor="center")
        self.tree.column("priority", width=100, anchor="center")
        self.tree.column("status", width=100, anchor="center")

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

    def bind_events(self):
        self.campaign_var.trace_add("write", lambda *args: self.update_add_button_state())
        self.marketer_var.trace_add("write", lambda *args: self.update_add_button_state())
        self.channel_var.trace_add("write", lambda *args: self.update_add_button_state())
        self.priority_var.trace_add("write", lambda *args: self.update_add_button_state())

        self.root.bind("<Return>", lambda event: self.add_campaign() if self.is_form_valid() else None)

    def is_form_valid(self):
        return all([
            self.campaign_var.get().strip(),
            self.marketer_var.get().strip(),
            self.channel_var.get().strip(),
            self.priority_var.get().strip()
        ])

    def update_add_button_state(self):
        if self.is_form_valid():
            self.add_button.config(state="normal")
        else:
            self.add_button.config(state="disabled")

    def add_campaign(self):
        if not self.is_form_valid():
            messagebox.showwarning("Validation", "Please fill in all required fields.")
            return

        campaign = self.campaign_var.get().strip()
        marketer = self.marketer_var.get().strip()
        channel = self.channel_var.get().strip()
        priority = self.priority_var.get().strip()
        status = "New"

        self.tree.insert(
            "",
            "end",
            values=(self.next_id, campaign, marketer, channel, priority, status)
        )

        self.next_id += 1
        self.clear_form()

    def clear_form(self):
        self.campaign_var.set("")
        self.marketer_var.set("")
        self.channel_var.set("")
        self.priority_var.set("")
        self.campaign_entry.focus_set()
        self.update_add_button_state()

    def insert_campaign(self, campaign, marketer, channel, priority):
        self.tree.insert(
            "",
            "end",
            values=(self.next_id, campaign, marketer, channel, priority, "New")
        )
        self.next_id += 1

    def load_sample_data(self):
        sample_data = [
            ("Spring Sale 2026", "Ivan Petrov", "Email", "High"),
            ("Instagram Promo", "Anna Smirnova", "Social Media", "Medium"),
            ("Google Ads Launch", "Dmitry Orlov", "Ads", "Low"),
            ("Newsletter Q2", "Olga Ivanova", "Email", "High"),
            ("TikTok Campaign", "Sergey Kuznetsov", "Social Media", "Medium"),
        ]

        for row in sample_data:
            self.insert_campaign(*row)


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    app = CampaignApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()