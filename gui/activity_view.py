import tkinter as tk


class ActivityView(tk.LabelFrame):

    def __init__(self, parent):

        super().__init__(
            parent,
            text="3. Activity Recommendation",
            font=("Arial", 10, "bold"),
            bg="white",
            padx=15,
            pady=10
        )

        self.text = tk.Text(
            self,
            height=15,
            width=40,
            font=("Arial", 10),
            bg="#f0fdf4",
            wrap="word",
            relief="flat"
        )

        self.text.pack(
            fill="both",
            expand=True
        )

        self.text.insert(
            "1.0",
            "Activity recommendations will appear here."
        )

        self.text.config(state="disabled")

    def display_recommendation(self, result):

        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)

        # Get packing checklist
        packing_items = result.get("packing", [])

        if isinstance(packing_items, list):
            packing = "\n".join(
                f"- {item}" for item in packing_items
            )
        else:
            packing = str(packing_items)

        # Prepare recommendation information
        info = (
            f"RISK LEVEL: {result.get('risk', 'Unknown')}\n\n"

            f"BEST TIME:\n"
            f"{result.get('best_time', 'Unavailable')}\n\n"

            f"EXPLANATION:\n"
            f"{result.get('explanation', 'No explanation available.')}\n\n"

            f"SAFETY ADVICE:\n"
            f"{result.get('safety', 'No additional warnings.')}\n\n"

            f"PACKING CHECKLIST:\n"
            f"{packing if packing else 'No checklist available.'}"
        )

        self.text.insert("1.0", info)

        self.text.config(state="disabled")
