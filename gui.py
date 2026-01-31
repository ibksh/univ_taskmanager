import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import Calendar
from task_manager import TaskManager
import threading
import time
from PIL import Image, ImageDraw
import pystray
import platform

class TaskManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("学生タスク管理ツール")
        self.root.geometry("1400x700")
        
        self.manager = TaskManager()
        self.selected_tasks = set()
        self.view_mode = 'active'
        self.sort_by = None
        self.sort_reverse = False
        self.tray_icon = None
        self.is_closing = False
        self.notified_tasks = {}  # {task_id: {'6h': bool, '3h': bool, '1h': bool}}
        
        # ウィンドウを閉じる時の処理を上書き
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.setup_ui()
        self.load_task_list()
        
        # 起動時の通知
        self.root.after(1000, self.show_startup_notification)
        
        # システムトレイアイコンをバックグラウンドで起動
        threading.Thread(target=self.setup_tray_icon, daemon=True).start()
        
        # 定期的なタスクチェック（1時間ごと）
        self.start_periodic_check()
    
    def setup_ui(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10, padx=10, anchor='w')
        
        add_button = tk.Button(button_frame, text="追加する", 
                               command=self.add_task_dialog,
                               bg="#1e5a7d", fg="white",
                               font=("Arial", 14, "bold"),
                               width=12, height=2)
        add_button.pack(side=tk.LEFT, padx=8)
        
        completed_button = tk.Button(button_frame, text="完了済み表示",
                                     command=self.show_completed_tasks,
                                     bg="#4a7c59", fg="white",
                                     font=("Arial", 14, "bold"),
                                     width=14, height=2)
        completed_button.pack(side=tk.LEFT, padx=8)
        
        expired_button = tk.Button(button_frame, text="期限切れ表示",
                                   command=self.show_expired_tasks,
                                   bg="#8b4513", fg="white",
                                   font=("Arial", 14, "bold"),
                                   width=14, height=2)
        expired_button.pack(side=tk.LEFT, padx=8)
        
        active_button = tk.Button(button_frame, text="通常表示",
                                  command=self.show_active_tasks,
                                  bg="#1e5a7d", fg="white",
                                  font=("Arial", 14, "bold"),
                                  width=12, height=2)
        active_button.pack(side=tk.LEFT, padx=8)
        
        button_frame_right = tk.Frame(self.root)
        button_frame_right.pack(pady=0, padx=10, anchor='e')
        
        complete_button = tk.Button(button_frame_right, text="完了にする",
                                    command=self.complete_selected_tasks,
                                    bg="#1e5a7d", fg="white",
                                    font=("Arial", 14, "bold"),
                                    width=12, height=2)
        complete_button.pack(side=tk.LEFT, padx=8)
        
        delete_button = tk.Button(button_frame_right, text="削除する",
                                  command=self.delete_selected_tasks,
                                  bg="#1e5a7d", fg="white",
                                  font=("Arial", 14, "bold"),
                                  width=12, height=2)
        delete_button.pack(side=tk.LEFT, padx=8)
        
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ('選択', '番号', 'タイトル', '期限', '優先度', '操作')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                 yscrollcommand=scrollbar.set, height=15)
        
        self.tree.heading('選択', text='')
        self.tree.heading('番号', text='番号')
        self.tree.heading('タイトル', text='タイトル')
        self.tree.heading('期限', text='期限')
        self.tree.heading('優先度', text='優先度')
        self.tree.heading('操作', text='')
        
        self.tree.column('選択', width=50, anchor='center')
        self.tree.column('番号', width=70, anchor='center')
        self.tree.column('タイトル', width=750, anchor='w')
        self.tree.column('期限', width=150, anchor='center')
        self.tree.column('優先度', width=100, anchor='center')
        self.tree.column('操作', width=60, anchor='center')
        
        scrollbar.config(command=self.tree.yview)
        
        style = ttk.Style()
        style.configure("Treeview.Heading", background="black", foreground="white", 
                       font=("Arial", 14, "bold"))
        style.configure("Treeview", rowheight=40, font=("Arial", 13))
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.heading('期限', text='期限', command=lambda: self.sort_by_column('deadline'))
        self.tree.heading('優先度', text='優先度', command=lambda: self.sort_by_column('priority'))
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="編集", command=self.edit_task_from_menu)
        self.context_menu.add_command(label="完了", command=self.complete_task_from_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="削除", command=self.delete_task_from_menu)
        
        self.current_menu_item = None
    
    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell":
            item = self.tree.identify_row(event.y)
            if item:
                if column == '#1':
                    if item in self.selected_tasks:
                        self.selected_tasks.remove(item)
                    else:
                        self.selected_tasks.add(item)
                    self.update_tree_display()
                elif column == '#6':
                    self.current_menu_item = item
                    self.context_menu.post(event.x_root, event.y_root)
        elif region == "nothing" or region == "":
            self.tree.selection_remove(self.tree.selection())
    
    def show_context_menu(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            if item:
                self.current_menu_item = item
                self.context_menu.post(event.x_root, event.y_root)
    
    def sort_by_column(self, column):
        if self.sort_by == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_by = column
            self.sort_reverse = False
        self.load_task_list()
    
    def load_task_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.selected_tasks.clear()
        
        now = datetime.now()
        
        if self.view_mode == 'active':
            # 通常表示: 未完了かつ期限が過ぎていないタスク
            tasks_to_show = []
            for t in self.manager.get_active_tasks():
                try:
                    task_deadline = datetime.strptime(t['deadline'], '%Y-%m-%d %H:%M')
                    if task_deadline >= now:
                        tasks_to_show.append(t)
                except:
                    # 日付の解析に失敗した場合は表示
                    tasks_to_show.append(t)
        elif self.view_mode == 'completed':
            tasks_to_show = [t for t in self.manager.get_all_tasks() if t['completed']]
        elif self.view_mode == 'expired':
            # 期限切れ表示: 未完了かつ期限が過ぎたタスク
            tasks_to_show = []
            for t in self.manager.get_all_tasks():
                if t['completed']:
                    continue
                try:
                    task_deadline = datetime.strptime(t['deadline'], '%Y-%m-%d %H:%M')
                    if task_deadline < now:
                        tasks_to_show.append(t)
                except:
                    if t['deadline'] < now.strftime('%Y-%m-%d'):
                        tasks_to_show.append(t)
        else:
            tasks_to_show = self.manager.get_active_tasks()
        
        active_tasks = tasks_to_show
        
        if self.sort_by == 'deadline':
            active_tasks = sorted(active_tasks, key=lambda t: t['deadline'], reverse=self.sort_reverse)
        elif self.sort_by == 'priority':
            priority_order = {'低': 1, '中': 3, '高': 5}
            active_tasks = sorted(active_tasks, key=lambda t: t['priority'], reverse=not self.sort_reverse)
        
        for task in active_tasks:
            task_id = str(task['id']).zfill(3)
            
            deadline = task['deadline']
            is_completed = task.get('completed', False)
            
            try:
                # 時刻を含む形式で解析（時刻は必須）
                deadline_dt = datetime.strptime(deadline, '%Y-%m-%d %H:%M')
                has_time = True
                
                today_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                days_diff = (deadline_dt.replace(hour=0, minute=0, second=0, microsecond=0) - today_date).days
                
                # 色分け判定用（時刻追加前）
                is_today = (days_diff == 0)
                is_tomorrow = (days_diff == 1)
                
                if days_diff < 0:
                    deadline_display = deadline_dt.strftime('%m/%d')
                elif days_diff == 0:
                    deadline_display = "本日"
                elif days_diff == 1:
                    deadline_display = "明日"
                else:
                    deadline_display = deadline_dt.strftime('%m/%d')
                
                # 時刻を追加表示
                if has_time and deadline_dt.strftime('%H:%M') != '23:59':
                    deadline_display += f" {deadline_dt.strftime('%H:%M')}"
            except:
                deadline_display = deadline
                is_today = False
                is_tomorrow = False
            
            priority_map = {1: '低', 2: '中', 3: '高'}
            priority_display = priority_map.get(task['priority'], '中')
            
            is_high_priority = task['priority'] == 3
            
            tag_name = f"task_{task['id']}"
            
            if is_today:
                tag_name = f"{tag_name}_today"
            elif is_tomorrow or is_high_priority:
                tag_name = f"{tag_name}_yellow"
            
            values = ('☐', task_id, task['name'], deadline_display, priority_display, '...')
            item_id = self.tree.insert('', tk.END, values=values, tags=(str(task['id']), tag_name))
            
            if is_today:
                self.tree.tag_configure(tag_name, background='#ffcccc', foreground='black')
            elif is_tomorrow or is_high_priority:
                self.tree.tag_configure(tag_name, background='#ffffcc', foreground='black')
    
    def update_tree_display(self):
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            
            if item in self.selected_tasks:
                values[0] = '☑'
            else:
                values[0] = '☐'
            
            self.tree.item(item, values=values)
    
    def add_task_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("タスク追加")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#d3d3d3')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="タスク名", bg='#d3d3d3', font=("Arial", 10)).grid(row=0, column=0, sticky='w', pady=10)
        name_entry = tk.Entry(frame, width=30, bg='white', fg='black', font=("Arial", 10))
        name_entry.grid(row=0, column=1, pady=10, padx=10)
        
        tk.Label(frame, text="期限日", bg='#d3d3d3', font=("Arial", 10)).grid(row=1, column=0, sticky='w', pady=10)
        deadline_frame = tk.Frame(frame, bg='#d3d3d3')
        deadline_frame.grid(row=1, column=1, pady=10, padx=10, sticky='w')
        deadline_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        deadline_entry = tk.Entry(deadline_frame, textvariable=deadline_var, width=23, bg='white', fg='black', font=("Arial", 10), state='readonly')
        deadline_entry.pack(side=tk.LEFT)
        
        def open_calendar():
            cal_window = tk.Toplevel(dialog)
            cal_window.title("期限を選択")
            cal_window.geometry("300x300")
            cal_window.transient(dialog)
            cal_window.grab_set()
            
            cal = Calendar(cal_window, selectmode='day', date_pattern='yyyy-mm-dd',
                          year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                          background='white', foreground='black',
                          headersbackground='#1e5a7d', headersforeground='white',
                          selectbackground='#4a90d9', selectforeground='white',
                          normalbackground='white', normalforeground='black',
                          weekendbackground='#f0f0f0', weekendforeground='black')
            cal.pack(pady=20, padx=20)
            
            def select_date():
                deadline_var.set(cal.get_date())
                cal_window.destroy()
            
            tk.Button(cal_window, text="選択", command=select_date, font=("Arial", 10), width=10).pack(pady=10)
        
        cal_button = tk.Button(deadline_frame, text="📅", command=open_calendar,
                              bg='#1e5a7d', fg='white', font=("Arial", 10, "bold"), width=3)
        cal_button.pack(side=tk.LEFT, padx=2)
        
        tk.Label(frame, text="時刻", bg='#d3d3d3', font=("Arial", 10)).grid(row=2, column=0, sticky='w', pady=10)
        time_frame = tk.Frame(frame, bg='#d3d3d3')
        time_frame.grid(row=2, column=1, pady=10, padx=10, sticky='w')
        time_var = tk.StringVar(value="23:59")
        time_values = [f"{h:02d}:00" for h in range(1, 24)] + ["23:59"]
        time_combo = ttk.Combobox(time_frame, textvariable=time_var,
                                 values=time_values,
                                 width=23, state='readonly')
        time_combo.pack(side=tk.LEFT)
        
        tk.Label(frame, text="優先度", bg='#d3d3d3', font=("Arial", 10)).grid(row=3, column=0, sticky='w', pady=10)
        priority_frame = tk.Frame(frame, bg='#d3d3d3')
        priority_frame.grid(row=3, column=1, pady=10, padx=10, sticky='w')
        priority_var = tk.StringVar(value="中")
        priority_combo = ttk.Combobox(priority_frame, textvariable=priority_var, 
                                     values=['低', '中', '高'], 
                                     width=23, state='readonly')
        priority_combo.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(frame, bg='#d3d3d3')
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        def on_add():
            name = name_entry.get().strip()
            deadline = deadline_var.get().strip()
            deadline_time = time_var.get().strip()
            priority_text = priority_var.get()
            
            priority_map = {'低': 1, '中': 2, '高': 3}
            priority = priority_map.get(priority_text, 2)
            
            if not name or not deadline:
                messagebox.showwarning("入力エラー", "タスク名と期限を入力してください")
                return
            
            self.manager.add_task(name, deadline, priority, deadline_time)
            self.load_task_list()
            dialog.destroy()
        
        add_btn = tk.Button(button_frame, text="追加する", command=on_add,
                           font=("Arial", 10), width=12)
        add_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(button_frame, text="キャンセル", command=dialog.destroy,
                              font=("Arial", 10), width=12)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def complete_selected_tasks(self):
        if not self.selected_tasks:
            messagebox.showinfo("情報", "タスクを選択してください")
            return
        
        for item in self.selected_tasks:
            task_id = int(self.tree.item(item)['tags'][0])
            self.manager.complete_task(task_id)
            # 通知済みリストから削除
            if task_id in self.notified_tasks:
                del self.notified_tasks[task_id]
        
        self.load_task_list()
        messagebox.showinfo("完了", "選択したタスクを完了にしました")
    
    def delete_selected_tasks(self):
        if not self.selected_tasks:
            messagebox.showinfo("情報", "タスクを選択してください")
            return
        
        result = messagebox.askyesno("確認", "選択したタスクを削除しますか？")
        if result:
            for item in self.selected_tasks:
                task_id = int(self.tree.item(item)['tags'][0])
                self.manager.delete_task(task_id)
                # 通知済みリストから削除
                if task_id in self.notified_tasks:
                    del self.notified_tasks[task_id]
            
            self.load_task_list()
            messagebox.showinfo("削除", "選択したタスクを削除しました")
    
    def show_active_tasks(self):
        self.view_mode = 'active'
        self.load_task_list()
    
    def show_completed_tasks(self):
        self.view_mode = 'completed'
        self.load_task_list()
    
    def show_expired_tasks(self):
        self.view_mode = 'expired'
        self.load_task_list()
    
    def edit_task_from_menu(self):
        if not self.current_menu_item:
            return
        
        task_id = int(self.tree.item(self.current_menu_item)['tags'][0])
        task = None
        for t in self.manager.get_all_tasks():
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            return
        
        # 現在の期限から日付と時刻を分離
        if ' ' in task['deadline']:
            current_date, current_time = task['deadline'].split(' ')
        else:
            current_date = task['deadline']
            current_time = '23:59'
        
        dialog = tk.Toplevel(self.root)
        dialog.title("タスク編集")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#d3d3d3')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="タスク名", bg='#d3d3d3', font=("Arial", 10)).grid(row=0, column=0, sticky='w', pady=10)
        name_entry = tk.Entry(frame, width=30, bg='white', fg='black', font=("Arial", 10))
        name_entry.insert(0, task['name'])
        name_entry.grid(row=0, column=1, pady=10, padx=10)
        
        tk.Label(frame, text="期限日", bg='#d3d3d3', font=("Arial", 10)).grid(row=1, column=0, sticky='w', pady=10)
        deadline_frame = tk.Frame(frame, bg='#d3d3d3')
        deadline_frame.grid(row=1, column=1, pady=10, padx=10, sticky='w')
        deadline_var = tk.StringVar(value=current_date)
        deadline_entry = tk.Entry(deadline_frame, textvariable=deadline_var, width=23, bg='white', fg='black', font=("Arial", 10), state='readonly')
        deadline_entry.pack(side=tk.LEFT)
        
        def open_calendar():
            cal_window = tk.Toplevel(dialog)
            cal_window.title("期限を選択")
            cal_window.geometry("300x300")
            cal_window.transient(dialog)
            cal_window.grab_set()
            
            cal = Calendar(cal_window, selectmode='day', date_pattern='yyyy-mm-dd',
                          year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                          background='white', foreground='black',
                          headersbackground='#1e5a7d', headersforeground='white',
                          selectbackground='#4a90d9', selectforeground='white',
                          normalbackground='white', normalforeground='black',
                          weekendbackground='#f0f0f0', weekendforeground='black')
            cal.pack(pady=20, padx=20)
            
            def select_date():
                deadline_var.set(cal.get_date())
                cal_window.destroy()
            
            tk.Button(cal_window, text="選択", command=select_date, font=("Arial", 10), width=10).pack(pady=10)
        
        cal_button = tk.Button(deadline_frame, text="📅", command=open_calendar,
                              bg='#1e5a7d', fg='white', font=("Arial", 10, "bold"), width=3)
        cal_button.pack(side=tk.LEFT, padx=2)
        
        tk.Label(frame, text="時刻", bg='#d3d3d3', font=("Arial", 10)).grid(row=2, column=0, sticky='w', pady=10)
        time_frame = tk.Frame(frame, bg='#d3d3d3')
        time_frame.grid(row=2, column=1, pady=10, padx=10, sticky='w')
        time_var = tk.StringVar(value=current_time)
        time_values = [f"{h:02d}:00" for h in range(1, 24)] + ["23:59"]
        time_combo = ttk.Combobox(time_frame, textvariable=time_var,
                                 values=time_values,
                                 width=23, state='readonly')
        time_combo.pack(side=tk.LEFT)
        
        tk.Label(frame, text="優先度", bg='#d3d3d3', font=("Arial", 10)).grid(row=3, column=0, sticky='w', pady=10)
        priority_frame = tk.Frame(frame, bg='#d3d3d3')
        priority_frame.grid(row=3, column=1, pady=10, padx=10, sticky='w')
        
        priority_map = {1: '低', 2: '中', 3: '高'}
        current_priority = priority_map.get(task['priority'], '中')
        priority_var = tk.StringVar(value=current_priority)
        priority_combo = ttk.Combobox(priority_frame, textvariable=priority_var, 
                                     values=['低', '中', '高'], 
                                     width=23, state='readonly')
        priority_combo.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(frame, bg='#d3d3d3')
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        def on_save():
            name = name_entry.get().strip()
            deadline = deadline_var.get().strip()
            deadline_time = time_var.get().strip()
            priority_text = priority_var.get()
            
            priority_map_reverse = {'低': 1, '中': 2, '高': 3}
            priority = priority_map_reverse.get(priority_text, 2)
            
            if not name or not deadline:
                messagebox.showwarning("入力エラー", "タスク名と期限を入力してください")
                return
            
            task['name'] = name
            task['deadline'] = f"{deadline} {deadline_time}"
            task['priority'] = priority
            self.manager.save_tasks()
            self.load_task_list()
            dialog.destroy()
        
        save_btn = tk.Button(button_frame, text="保存", command=on_save,
                           font=("Arial", 10), width=12)
        save_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = tk.Button(button_frame, text="キャンセル", command=dialog.destroy,
                              font=("Arial", 10), width=12)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def complete_task_from_menu(self):
        if not self.current_menu_item:
            return
        
        task_id = int(self.tree.item(self.current_menu_item)['tags'][0])
        self.manager.complete_task(task_id)
        # 通知済みリストから削除
        if task_id in self.notified_tasks:
            del self.notified_tasks[task_id]
        self.load_task_list()
        messagebox.showinfo("完了", "タスクを完了にしました")
    
    def delete_task_from_menu(self):
        if not self.current_menu_item:
            return
        
        result = messagebox.askyesno("確認", "このタスクを削除しますか？")
        if result:
            task_id = int(self.tree.item(self.current_menu_item)['tags'][0])
            self.manager.delete_task(task_id)
            # 通知済みリストから削除
            if task_id in self.notified_tasks:
                del self.notified_tasks[task_id]
            self.load_task_list()
            messagebox.showinfo("削除", "タスクを削除しました")
    
    def show_startup_notification(self):
        """起動時に明日までのタスクと優先度高のタスクを通知（期限切れは除外）"""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        
        tasks_to_notify = []
        
        for task in self.manager.get_active_tasks():
            try:
                # 期限をdatetimeに変換（時刻は必須）
                deadline_dt = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M')
                
                # 期限切れを除外（現在時刻より前は通知しない）
                if deadline_dt < now:
                    continue
                
                # 明日までのタスクまたは優先度高のタスク
                if deadline_dt <= tomorrow or task['priority'] == 3:
                    tasks_to_notify.append(task)
            except:
                continue
        
        if not tasks_to_notify:
            self.show_notification("学生タスク管理", "今日のタスクはありません👍")
            return
        
        # タスクを分類
        today_tasks = []
        tomorrow_tasks = []
        high_priority_tasks = []
        
        today_str = now.strftime('%Y-%m-%d')
        tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        
        for task in tasks_to_notify:
            deadline_date = task['deadline'].split(' ')[0]
            if deadline_date == today_str:
                today_tasks.append(task)
            elif deadline_date == tomorrow_str:
                tomorrow_tasks.append(task)
            if task['priority'] == 3 and task not in today_tasks:
                high_priority_tasks.append(task)
        
        # 通知メッセージを作成
        message_parts = []
        if today_tasks:
            message_parts.append(f"本日締め切り: {len(today_tasks)}件")
        if tomorrow_tasks:
            message_parts.append(f"明日締め切り: {len(tomorrow_tasks)}件")
        if high_priority_tasks:
            message_parts.append(f"優先度高: {len(high_priority_tasks)}件")
        
        self.show_notification("学生タスク管理 - 重要なタスク", "\n".join(message_parts))
        
        # 通知メッセージを作成
        message_parts = []
        if today_tasks:
            message_parts.append(f"本日締め切り: {len(today_tasks)}件")
        if tomorrow_tasks:
            message_parts.append(f"明日締め切り: {len(tomorrow_tasks)}件")
        if high_priority_tasks:
            message_parts.append(f"優先度高: {len(high_priority_tasks)}件")
        
        self.show_notification("学生タスク管理 - 重要なタスク", "\n".join(message_parts))
    
    def show_notification(self, title, message):
        """Windows/Linux両対応の通知を表示"""
        if platform.system() == 'Windows':
            try:
                from winotify import Notification, audio
                toast = Notification(
                    app_id="学生タスク管理",
                    title=title,
                    msg=message,
                    duration="long"
                )
                toast.set_audio(audio.Default, loop=False)
                toast.show()
            except Exception as e:
                # エラー時はメッセージボックスにフォールバック
                self.root.after(0, lambda: messagebox.showinfo(title, message))
        else:
            # Linux等ではメッセージボックス
            self.root.after(0, lambda: messagebox.showinfo(title, message))
    
    def start_periodic_check(self):
        """定期的にタスクをチェックして通知（バックグラウンドスレッド）"""
        def check_loop():
            print("[定期チェック] 開始")
            
            while not self.is_closing:
                # 現在時刻を取得
                now = datetime.now()
                
                # 次の毎時00分まで待つ
                next_check = now.replace(minute=0, second=0, microsecond=0)
                if now.minute > 0 or now.second > 0:
                    # 現在が00分を過ぎている場合は次の時間の00分
                    next_check = next_check + timedelta(hours=1)
                
                wait_seconds = (next_check - now).total_seconds()
                print(f"[定期チェック] 次回チェック: {next_check.strftime('%Y-%m-%d %H:%M')} ({wait_seconds:.0f}秒後)")
                
                # 次のチェック時刻まで待機
                time.sleep(wait_seconds)
                
                if not self.is_closing:
                    print(f"[定期チェック] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 締め切りチェック実行")
                    self.check_upcoming_deadlines()
        
        threading.Thread(target=check_loop, daemon=True).start()
    
    def check_upcoming_deadlines(self):
        """締め切りが近いタスクを通知（6時間、3時間、1時間前）"""
        now = datetime.now()
        active_tasks = self.manager.get_active_tasks()
        print(f"[締め切りチェック] アクティブなタスク数: {len(active_tasks)}")
        
        # 各時間帯でチェック（時間、キー、ラベル）
        time_windows = [
            (6, '6h', '6時間'),
            (3, '3h', '3時間'),
            (1, '1h', '1時間')
        ]
        
        for hours, key, label in time_windows:
            tasks_to_alert = []
            
            for task in active_tasks:
                task_id = task['id']
                
                # このタスクの通知状態を初期化
                if task_id not in self.notified_tasks:
                    self.notified_tasks[task_id] = {'6h': False, '3h': False, '1h': False}
                
                # すでにこの時間帯で通知済みならスキップ
                if self.notified_tasks[task_id][key]:
                    continue
                
                try:
                    # 期限をdatetimeに変換（時刻は必須）
                    deadline_dt = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M')
                    
                    # 締め切りまでの残り時間を計算
                    time_remaining = deadline_dt - now
                    hours_remaining = time_remaining.total_seconds() / 3600
                    
                    print(f"[締め切りチェック] タスク「{task['name']}」: 残り{hours_remaining:.2f}時間")
                    
                    # ちょうど指定時間前（1時間の範囲: hours-1 < 残り時間 <= hours）
                    if hours - 1 < hours_remaining <= hours:
                        tasks_to_alert.append(task)
                        self.notified_tasks[task_id][key] = True
                        print(f"[締め切りチェック] → {label}前通知対象に追加")
                except Exception as e:
                    print(f"[締め切りチェック] エラー: {e}")
                    continue
            
            if tasks_to_alert:
                # タスク名を列挙
                task_names = '\n'.join([f"・{t['name']}" for t in tasks_to_alert[:5]])
                if len(tasks_to_alert) > 5:
                    task_names += f"\n...他{len(tasks_to_alert) - 5}件"
                
                print(f"[通知] {label}前: {len(tasks_to_alert)}件")
                self.show_notification(
                    f"締め切り{label}前",
                    f"{len(tasks_to_alert)}件のタスクが{label}前です\n\n{task_names}"
                )
    
    def create_tray_image(self):
        """システムトレイ用のアイコンを作成"""
        # 簡単なアイコンを作成
        image = Image.new('RGB', (64, 64), color='white')
        dc = ImageDraw.Draw(image)
        dc.rectangle([16, 16, 48, 48], fill='#1e5a7d', outline='#1e5a7d')
        dc.rectangle([20, 20, 44, 28], fill='white')
        dc.rectangle([20, 32, 44, 40], fill='white')
        return image
    
    def setup_tray_icon(self):
        """システムトレイアイコンをセットアップ"""
        icon_image = self.create_tray_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("Open", self.show_window),
            pystray.MenuItem("Quit", self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("task_manager", icon_image, "Task Manager", menu)
        self.tray_icon.run()
    
    def show_window(self, icon=None, item=None):
        """ウィンドウを表示"""
        self.root.after(0, self._show_window)
    
    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """ウィンドウを隠してトレイに格納"""
        self.root.withdraw()
    
    def quit_app(self, icon=None, item=None):
        """アプリケーションを終了"""
        self.is_closing = True
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

def main():
    root = tk.Tk()
    app = TaskManagerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
