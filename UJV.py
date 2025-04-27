import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

reason_descriptions = {
    0x00000100: "Создание файла",
    0x00000102: "Изменение данных | Создание файла",
    0x80000102: "Изменение данных | Создание файла | Закрыть",
    0x00008000: "Изменение основных сведений",
    0x00008800: "Изменение безопасности | Изменение основных сведений",
    0x00001000: "Переименование: старое имя",
    0x00002000: "Переименование: новое имя",
    0x00009800: "Изменение безопасности | Переименование: старое имя | Изменение основных сведений",
    0x0000a800: "Изменение безопасности | Переименование: новое имя | Изменение основных сведений",
    0x80002000: "Переименование: новое имя | Закрыть",
    0x8000a800: "Изменение безопасности | Переименование: новое имя | Изменение основных сведений | Закрыть",
    0x80000200: "Удаление файла | Закрыть"
}

reason_categories = {
    "Удаление": [0x80000200],
    "Создание": [0x00000100, 0x00000102, 0x80000102],
    "Переименование": [0x00001000, 0x00002000, 0x00009800, 0x0000a800, 0x80002000, 0x8000a800],
    "Закрыто": [0x80000102, 0x80002000, 0x8000a800, 0x80000200],
    "Изменение данных": [0x00000102, 0x80000102, 0x00008000, 0x00008800]
}

class USNJournalViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("USN Journal Viewer")
        self.root.geometry("1030x400")
        self.current_page = 0
        self.page_size = 10
        self.filtered_data = []
        self.usn_data = []
        self.search_results = []

        self.create_widgets()

    def create_widgets(self):
        self.load_button = ttk.Button(self.root, text="Загрузить файл", command=self.start_loading)
        self.load_button.grid(row=0, column=0, padx=5, pady=5)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=0, column=1, padx=5, pady=5)

        self.search_label = ttk.Label(self.root, text="Поиск по имени файла:")
        self.search_label.grid(row=1, column=0, padx=5, pady=5)

        self.search_entry = ttk.Entry(self.root)
        self.search_entry.grid(row=1, column=1, padx=5, pady=5)

        self.search_button = ttk.Button(self.root, text="Поиск", command=self.search_file)
        self.search_button.grid(row=1, column=2, padx=5, pady=5)

        self.reason_label = ttk.Label(self.root, text="Сортировка по причине:")
        self.reason_label.grid(row=2, column=0, padx=5, pady=5)

        self.reason_var = tk.StringVar(value="Все")
        self.reason_menu = ttk.OptionMenu(self.root, self.reason_var, "Все", *(["Все"] + list(reason_categories.keys())), command=self.filter_by_reason)
        self.reason_menu.grid(row=2, column=1, padx=5, pady=5)

        self.page_label = ttk.Label(self.root, text="Перейти на страницу:")
        self.page_label.grid(row=2, column=2, padx=5, pady=5)

        self.page_entry = ttk.Entry(self.root, width=10)
        self.page_entry.grid(row=2, column=3, padx=5, pady=5)

        self.page_button = ttk.Button(self.root, text="Перейти", command=self.go_to_page)
        self.page_button.grid(row=2, column=4, padx=5, pady=5)

        self.tree_frame = ttk.Frame(self.root)
        self.tree_frame.grid(row=3, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")

        self.tree = ttk.Treeview(self.tree_frame, columns=("File Name", "File ID", "Parent ID", "Reason", "Timestamp"), show="headings")
        self.tree.heading("File Name", text="Имя файла")
        self.tree.heading("File ID", text="ИД файла")
        self.tree.heading("Parent ID", text="ИД родительского файла")
        self.tree.heading("Reason", text="Причина")
        self.tree.heading("Timestamp", text="Метка времени")
        self.tree.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать строку", command=self.copy_row)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.prev_button = ttk.Button(self.root, text="Назад", command=self.prev_page)
        self.prev_button.grid(row=4, column=0, padx=5, pady=5)

        self.next_button = ttk.Button(self.root, text="Дальше", command=self.next_page)
        self.next_button.grid(row=4, column=2, padx=5, pady=5)

    def start_loading(self):
        """Запускает фоновую загрузку файла."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return

        self.load_button.config(state="disabled")
        self.progress["value"] = 0

        threading.Thread(target=self.load_data, args=(file_path,), daemon=True).start()

    def load_data(self, file_path):
        """Загружает данные из файла в фоновом режиме."""
        try:
            self.usn_data = []
            total_lines = self.count_lines(file_path)
            with open(file_path, "r", encoding="IBM866") as file:
                entry = {}
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if line.startswith("USN:"):
                        if entry:
                            self.usn_data.append(entry)
                            entry = {}
                    elif line.startswith("Имя файла:"):
                        entry["file_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("ИД файла:"):
                        entry["file_id"] = line.split(":", 1)[1].strip()
                    elif line.startswith("ИД родительского файла:"):
                        entry["parent_id"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Причина:"):
                        reason_part = line.split(":", 1)[1].strip()
                        reason_code = int(reason_part.split(":")[0].strip(), 16)
                        entry["reason"] = reason_code
                    elif line.startswith("Метка времени:"):
                        entry["timestamp"] = line.split(":", 1)[1].strip()

                    if line_num % 100 == 0:
                        progress_value = (line_num / total_lines) * 100
                        self.root.after(10, self.update_progress, progress_value)

            if entry:
                self.usn_data.append(entry)

            self.usn_data.reverse()
            self.filtered_data = self.usn_data
            self.search_results = self.usn_data
            self.current_page = 0
            self.root.after(10, self.update_table)
        except Exception as e:
            self.root.after(10, messagebox.showerror, "Ошибка", f"Не удалось загрузить файл: {e}")
        finally:
            self.root.after(10, self.load_button.config, {"state": "normal"})

    def count_lines(self, file_path):
        """Подсчитывает количество строк в файле."""
        with open(file_path, "r", encoding="IBM866") as file:
            return sum(1 for _ in file)

    def update_progress(self, value):
        """Обновляет значение прогрессбара."""
        self.progress["value"] = value
        self.root.update_idletasks()

    def update_table(self):
        """Обновляет таблицу данными."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_data = self.filtered_data[start:end]

        for entry in page_data:
            reason_description = reason_descriptions.get(entry.get("reason", 0), "Неизвестная причина")
            self.tree.insert("", "end", values=(
                entry.get("file_name", ""),
                entry.get("file_id", ""),
                entry.get("parent_id", ""),
                reason_description,
                entry.get("timestamp", "")
            ))

    def search_file(self):
        """Выполняет поиск по имени файла."""
        search_term = self.search_entry.get().lower()
        self.search_results = [entry for entry in self.usn_data if search_term in entry.get("file_name", "").lower()]
        self.filtered_data = self.search_results
        self.current_page = 0
        self.update_table()

    def filter_by_reason(self, selected_reason):
        """Фильтрует данные по выбранной причине."""
        if selected_reason == "Все":
            self.filtered_data = self.search_results
        else:
            reason_codes = reason_categories.get(selected_reason, [])
            self.filtered_data = [entry for entry in self.search_results if entry.get("reason", 0) in reason_codes]
        self.current_page = 0
        self.update_table()

    def go_to_page(self):
        """Переход на указанную страницу."""
        try:
            page_num = int(self.page_entry.get()) - 1
            max_page = (len(self.filtered_data)) // self.page_size
            if 0 <= page_num <= max_page:
                self.current_page = page_num
                self.update_table()
            else:
                messagebox.showwarning("Ошибка", f"Номер страницы должен быть от 1 до {max_page + 1}")
        except ValueError:
            messagebox.showwarning("Ошибка", "Введите корректный номер страницы.")

    def show_context_menu(self, event):
        """Показывает контекстное меню."""
        self.tree.selection_set(self.tree.identify_row(event.y))
        self.context_menu.post(event.x_root, event.y_root)

    def copy_row(self):
        """Копирует данные выделенной строки в буфер обмена."""
        selected_item = self.tree.selection()
        if selected_item:
            row_data = self.tree.item(selected_item, "values")
            self.root.clipboard_clear()
            self.root.clipboard_append("\t".join(map(str, row_data)))
            messagebox.showinfo("Копирование", "Строка скопирована в буфер обмена.")

    def prev_page(self):
        """Переход на предыдущую страницу."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()

    def next_page(self):
        """Переход на следующую страницу."""
        if (self.current_page + 1) * self.page_size < len(self.filtered_data):
            self.current_page += 1
            self.update_table()

if __name__ == "__main__":
    root = tk.Tk()
    app = USNJournalViewer(root)
    root.mainloop()