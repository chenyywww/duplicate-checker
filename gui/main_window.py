import os
import csv
import threading
import send2trash
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# 从 core.file_utils 导入功能函数
from core.file_utils import ( # pyright: ignore[reportMissingImports]
    extract_ignore_keywords,
    normalize,
    is_version_variant,
    collect_files,
    build_duplicate_groups,
)

class DuplicateCheckerGUI:
    def __init__(self, master):
        self.master = master
        master.title("重复文件检测器")

        self.folder_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=0.8)
        self.depth_var = tk.IntVar(value=1)
        self.keyword_var = tk.StringVar()
        self.checkbox_refs = []
        self.duplicate_groups = []

        self.setup_ui()

    def setup_ui(self):
        frame_top = tk.Frame(self.master)
        frame_top.pack(fill='x', padx=10, pady=5)

        tk.Label(frame_top, text="目标路径:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame_top, textvariable=self.folder_var, width=60).grid(row=0, column=1, sticky='ew')
        tk.Button(frame_top, text="选择", command=self.select_folder).grid(row=0, column=2)

        tk.Label(frame_top, text="相似度(0.6-1.0):").grid(row=1, column=0, sticky='w')
        tk.Scale(frame_top, variable=self.threshold_var, from_=0.6, to=1.0, resolution=0.01, orient='horizontal').grid(row=1, column=1, sticky='w')

        tk.Label(frame_top, text="遍历层级:").grid(row=1, column=2, sticky='e')
        tk.Spinbox(frame_top, from_=0, to=10, textvariable=self.depth_var, width=5).grid(row=1, column=3)

        tk.Label(frame_top, text="忽略关键词(用【】或()包裹):").grid(row=2, column=0, sticky='w')
        tk.Entry(frame_top, textvariable=self.keyword_var, width=60).grid(row=2, column=1, columnspan=2, sticky='ew')

        btn_frame = tk.Frame(self.master)
        btn_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(btn_frame, text="开始检测", command=self.run_detection).pack(side='left', padx=5)
        tk.Button(btn_frame, text="导出报告", command=self.export_report).pack(side='left', padx=5)
        tk.Button(btn_frame, text="删除勾选项", command=self.delete_selected).pack(side='left', padx=5)

        self.progress = ttk.Progressbar(self.master, orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', padx=10, pady=(0, 5))

        self.result_text = scrolledtext.ScrolledText(self.master, height=10)
        self.result_text.pack(fill='x', padx=10, pady=5)

        # 滚动区域容纳所有Checkbutton
        canvas_frame = tk.Frame(self.master)
        canvas_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(canvas_frame)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.check_frame = self.scrollable_frame


    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def update_progress(self, current, total):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress['value'] = percent
            self.master.update_idletasks()

    def run_detection(self):
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)
        for w in self.check_frame.winfo_children():
            w.destroy()
        self.checkbox_refs.clear()
        self.duplicate_groups.clear()
        self.progress['value'] = 0

        folder = self.folder_var.get()
        if not os.path.isdir(folder):
            messagebox.showerror("错误", "请选择有效的文件夹路径。")
            return

        def worker():
            entries = collect_files(
                folder,
                max_depth=self.depth_var.get(),
                progress_callback=self.update_progress
            )
            user_keywords = extract_ignore_keywords(self.keyword_var.get())
            groups = build_duplicate_groups(
                entries,
                threshold=self.threshold_var.get(),
                user_keywords=user_keywords
            )
            self.duplicate_groups = groups

            if not groups:
                self.result_text.insert(tk.END, "未发现任何重复项。\n")
            else:
                self.result_text.insert(tk.END, f"检测到 {len(groups)} 组重复:\n\n")
                for idx, group in enumerate(groups, start=1):
                    core = normalize(group[0][0])
                    self.result_text.insert(tk.END, f"组 {idx} • 相似核心: {core}\n")
                    for name, path in group:
                        var = tk.BooleanVar()
                        cb = tk.Checkbutton(self.check_frame, text=path, variable=var, anchor='w', justify='left')
                        cb.pack(fill='x', anchor='w')
                        self.checkbox_refs.append((var, path))
                        self.result_text.insert(tk.END, f"   • {name}\n")
                    self.result_text.insert(tk.END, "\n")

            self.progress['value'] = 0
            self.result_text.configure(state='disabled')

        threading.Thread(target=worker, daemon=True).start()

    def export_report(self):
        if not self.duplicate_groups:
            messagebox.showinfo("提示", "没有可导出的重复项。")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            title="保存报告"
        )
        if not save_path:
            return

        try:
            with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["组编号", "文件名", "完整路径"])
                for idx, group in enumerate(self.duplicate_groups, start=1):
                    for name, path in group:
                        writer.writerow([idx, name, path])
            messagebox.showinfo("导出成功", f"报告已保存到: {save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"发生错误: {e}")

    def delete_selected(self):
        deleted, failed = [], []
        for var, path in self.checkbox_refs:
            if var.get():
                try:
                    send2trash.send2trash(path)
                    deleted.append(path)
                except Exception as e:
                    failed.append(f"{path} ({e})")

        msg = f"成功删除 {len(deleted)} 项。"
        if failed:
            msg += f"\n失败 {len(failed)} 项：\n" + "\n".join(failed)
        messagebox.showinfo("删除结果", msg)
        self.run_detection()

if __name__ == '__main__':
    root = tk.Tk()
    app = DuplicateCheckerGUI(root)
    root.mainloop()

