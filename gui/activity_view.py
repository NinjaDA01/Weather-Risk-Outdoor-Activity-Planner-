import tkinter as tk

class ActivityView(tk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="3. Activity Recommendation", font=("Arial", 10, "bold"), bg="white", padx=15, pady=10)
        self.text = tk.Text(self, height=15, width=40, font=("Arial", 10), bg="#f0fdf4", wrap="word", relief="flat")
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", "Recommendations will appear here")
        self.text.config(state="disabled")

    def display_recommendation(self, result):
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        packing_items = result.get("packing", [])

if isinstance(packing_items, list):
    packing = "\n".join(f"- {item}" for item in packing_items)
else:
    packing = str(packing_items)
        info = f"RISK: {result.get('risk')}\n\nBEST TIME: {result.get('best_time')}\n\nEXPLANATION: {result.get('explanation')}\n\nSAFETY: {result.get('safety')}\n\nPACKING:\n{packing}"
        self.text.insert("1.0", info)
        self.text.config(state="disabled")
