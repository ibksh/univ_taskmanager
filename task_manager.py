import json
import os
from datetime import datetime

class TaskManager:
    def __init__(self, json_file='student_tasks.json'):
        self.json_file = json_file
        self.tasks = self.load_tasks()
    
    def load_tasks(self):
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'tasks': [], 'next_id': 1}
    
    def save_tasks(self):
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add_task(self, name: str, deadline: str, priority: int = 2, deadline_time: str = '23:59'):
        if priority < 1 or priority > 3:
            priority = max(1, min(3, priority))
        
        # 日付と時刻を結合
        if ' ' not in deadline:  # 時刻が含まれていない場合
            deadline = f"{deadline} {deadline_time}"
        
        task = {
            'id': self.tasks['next_id'],
            'name': name,
            'deadline': deadline,
            'priority': priority,
            'completed': False
        }
        
        self.tasks['tasks'].append(task)
        self.tasks['next_id'] += 1
        self.save_tasks()
        return task
    
    def delete_task(self, task_id: int) -> bool:
        original_count = len(self.tasks['tasks'])
        self.tasks['tasks'] = [t for t in self.tasks['tasks'] if t['id'] != task_id]
        
        if len(self.tasks['tasks']) < original_count:
            self.save_tasks()
            return True
        return False
    
    def complete_task(self, task_id: int) -> bool:
        for task in self.tasks['tasks']:
            if task['id'] == task_id:
                if not task['completed']:
                    task['completed'] = True
                    self.save_tasks()
                    return True
        return False
    
    def get_active_tasks(self):
        return [t for t in self.tasks['tasks'] if not t['completed']]
    
    def get_all_tasks(self):
        return self.tasks['tasks']
