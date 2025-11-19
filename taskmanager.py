import json
import argparse
import sys
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
    
    def add_task(self, name: str, deadline: str, priority: int = 3):
        if priority < 1 or priority > 5:
            priority = max(1, min(5, priority))
            print(f"優先度を {priority} に調整しました（範囲: 1-5）")
        
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
        print(f"タスクを追加しました: [ID: {task['id']}] {task['name']} (期限: {task['deadline']}, 優先度: {task['priority']})")
        return task
    
    def delete_task(self, task_id: int) -> bool:
        original_count = len(self.tasks['tasks'])
        self.tasks['tasks'] = [t for t in self.tasks['tasks'] if t['id'] != task_id]
        
        if len(self.tasks['tasks']) < original_count:
            self.save_tasks()
            print(f"タスク {task_id} を削除しました")
            return True
        else:
            print(f"タスク {task_id} が見つかりません")
            return False
    
    def complete_task(self, task_id: int) -> bool:
        task_found = False
        
        for task in self.tasks['tasks']:
            if task['id'] == task_id:
                if not task['completed']:
                    task['completed'] = True
                    task_found = True
                    self.save_tasks()
                    print(f"タスク {task_id} を完了しました")
                else:
                    print(f"タスク {task_id} は既に完了しています")
                return True
        
        print(f"タスク {task_id} が見つかりません")
        return False
    
    def list_tasks(self, show_all: bool = False):
        if show_all:
            tasks_to_show = self.tasks['tasks']
            print("タスク一覧:")
        else:
            tasks_to_show = [t for t in self.tasks['tasks'] if not t['completed']]
            print("残りのタスク一覧:")
        
        if not tasks_to_show:
            print("タスクがありません")
            return
        
        tasks_to_show.sort(key=lambda t: t['priority'])
        
        for task in tasks_to_show:
            status = "✓" if task['completed'] else "○"
            print(f"  {status} [ID: {task['id']}] {task['name']} (期限: {task['deadline']}, 優先度: {task['priority']})")

class TaskCLI:
    def __init__(self):
        self.manager = TaskManager()
    
    def run(self, args):
        parser = argparse.ArgumentParser(description='大学生向けタスク管理システム')
        subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
        
        add_parser = subparsers.add_parser('add', help='新しいタスクを追加')
        add_parser.add_argument('name', help='タスク名')
        add_parser.add_argument('deadline', help='期限 (YYYY-MM-DD)')
        add_parser.add_argument('--priority', '-p', type=int, default=3, help='優先度 (1-5, デフォルト: 3)')
        
        list_parser = subparsers.add_parser('list', help='タスク一覧を表示')
        list_parser.add_argument('--all', action='store_true', help='完了済みタスクも表示')
        
        complete_parser = subparsers.add_parser('complete', help='タスクを完了')
        complete_parser.add_argument('id', type=int, help='タスクID')
        
        delete_parser = subparsers.add_parser('delete', help='タスクを削除')
        delete_parser.add_argument('id', type=int, help='タスクID')
        
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return
        
        try:
            if parsed_args.command == 'add':
                self.manager.add_task(parsed_args.name, parsed_args.deadline, parsed_args.priority)
            elif parsed_args.command == 'list':
                self.manager.list_tasks(parsed_args.all)
            elif parsed_args.command == 'complete':
                self.manager.complete_task(parsed_args.id)
            elif parsed_args.command == 'delete':
                self.manager.delete_task(parsed_args.id)
        except Exception as e:
            print(f"エラー: {e}")

if __name__ == '__main__':
    cli = TaskCLI()
    cli.run(sys.argv[1:])
