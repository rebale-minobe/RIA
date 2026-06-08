#!/usr/bin/env python3
"""
RIA 再TEST用：階層選択ロジック（新CSV形式対応版）

新CSV形式：各日付に対して date_maru, date_batsu 列を持つ
"""

import csv
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple

class AnswerLogPivot:
    """ピボット化されたanswer_log.csvを扱うクラス"""
    
    def __init__(self):
        self.data = []
        self.chapters = None
        self.lessons_by_chapter = None
        self.questions_by_lesson = None
    
    @classmethod
    def load_csv(cls, csv_path: str) -> 'AnswerLogPivot':
        """CSVを読み込む"""
        instance = cls()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            instance.data = list(reader)
        
        instance._build_hierarchy()
        return instance
    
    def _build_hierarchy(self):
        """章 → lesson_title → 問題の階層を構築"""
        
        chapters = {}
        lessons_by_chapter = defaultdict(dict)
        questions_by_lesson = defaultdict(list)
        
        for row in self.data:
            page = row.get('page_num', '')
            lesson_title = row.get('lesson_title', '')
            chapter_title = row.get('chapter_title', '')
            
            # 章を登録（chapter_title をキーとして使用）
            if chapter_title:
                chapters[chapter_title] = chapter_title
                
                # lesson_title を登録（重複排除）
                lesson_key = f"{page}|{lesson_title}"
                lessons_by_chapter[chapter_title][lesson_key] = {
                    'page': page,
                    'lesson_title': lesson_title
                }
            
            # 問題を登録
            if lesson_title:
                questions_by_lesson[f"{page}|{lesson_title}"].append(row)
        
        self.chapters = chapters
        self.lessons_by_chapter = lessons_by_chapter
        self.questions_by_lesson = questions_by_lesson
    
    def get_chapters(self) -> List[Tuple[str, str]]:
        """
        章一覧を返す（出現順）
        戻り値: [(chapter_title, chapter_title), ...]
        """
        if not self.chapters:
            return []
        
        # 重複を排除（OrderedDict の順序を保持）
        seen = set()
        result = []
        for chapter_title in self.chapters.keys():
            if chapter_title not in seen:
                result.append((chapter_title, chapter_title))
                seen.add(chapter_title)
        return result
    
    def get_lessons_in_chapter(self, chapter_title: str) -> List[Dict]:
        """
        指定章内のlesson_titleを返す（進捗情報付き）
        
        Args:
            chapter_title: 章のタイトル（第1章：大航海によって結びつく世界 など）
        
        戻り値:
          [
            {
              'lesson_key': '2|大航海によって結びつく世界',
              'lesson_title': '大航海によって結びつく世界',
              'page': '2',
              'total_count': 20,
              'maru_count': 18,
              'batsu_count': 2
            },
            ...
          ]
        """
        lessons = []
        
        # chapter_title に対応するレッスンを抽出
        for lesson_key, lesson_info in self.lessons_by_chapter.get(chapter_title, {}).items():
            page = lesson_info['page']
            lesson_title = lesson_info['lesson_title']
            
            # 進捗を計算
            questions = self.questions_by_lesson.get(lesson_key, [])
            total_count = len(questions)
            
            # 最新結果で集計
            maru_count = 0
            batsu_count = 0
            
            for q in questions:
                # 日付_maru, 日付_batsu 列から最新結果を抽出
                latest_result = None
                latest_date = None
                
                for col_name in q.keys():
                    if col_name.endswith('_maru') or col_name.endswith('_batsu'):
                        if q[col_name]:
                            date = col_name.replace('_maru', '').replace('_batsu', '')
                            if latest_date is None or date > latest_date:
                                latest_date = date
                                latest_result = 'maru' if col_name.endswith('_maru') else 'batsu'
                
                if latest_result == 'maru':
                    maru_count += 1
                elif latest_result == 'batsu':
                    batsu_count += 1
            
            lessons.append({
                'lesson_key': lesson_key,
                'lesson_title': lesson_title,
                'page': page,
                'total_count': total_count,
                'maru_count': maru_count,
                'batsu_count': batsu_count
            })
        
        # ページ順でソート
        lessons.sort(key=lambda x: int(x['page']))
        return lessons
    
    def get_questions_in_lesson(self, lesson_key: str, 
                               filter_batsu_only: bool = True) -> List[Dict]:
        """
        指定lesson内の問題を返す（新CSV形式対応）
        
        新CSV形式：date_maru, date_batsu 列から結果を抽出
        
        Args:
            lesson_key: lesson_key (page|lesson_title 形式)
            filter_batsu_only: Trueの場合、最新結果が batsu の問題のみ返す
        
        戻り値:
          [
            {
              'page': '2',
              'section_code': 'A',
              'q_label': '②',
              'answer': '十字軍',
              'latest_result': 'batsu',
              'history': ['batsu', 'maru', ...]  # 古い順
              'error_count': 2
              'workbook_ref': '本誌 P.2・3'
            },
            ...
          ]
        """
        questions = self.questions_by_lesson.get(lesson_key, [])
        
        result = []
        for q in questions:
            # 日付_maru, 日付_batsu 列から履歴を構築
            history = []
            
            # 日付を抽出して、chronological order で処理
            date_results = {}  # {date: [maru_count, batsu_count]}
            
            for col_name in q.keys():
                if col_name.endswith('_maru') or col_name.endswith('_batsu'):
                    value = q[col_name]
                    if not value:
                        continue
                    
                    try:
                        count = int(value)
                        date = col_name.replace('_maru', '').replace('_batsu', '')
                        
                        if date not in date_results:
                            date_results[date] = [0, 0]
                        
                        if col_name.endswith('_maru'):
                            date_results[date][0] = count
                        else:  # _batsu
                            date_results[date][1] = count
                    except ValueError:
                        pass
            
            # 日付順にソートして履歴を構築
            for date in sorted(date_results.keys()):
                maru_count, batsu_count = date_results[date]
                history.extend(['maru'] * maru_count)
                history.extend(['batsu'] * batsu_count)
            
            # 最新の結果を取得
            latest_result = history[-1] if history else None
            
            # filter_batsu_only の処理
            if filter_batsu_only and latest_result != 'batsu':
                continue
            
            result.append({
                'page': q['page_num'],
                'section_code': q['section_code'],
                'q_label': q['q_label'],
                'answer': q['answer'],
                'latest_result': latest_result,
                'history': history,
                'error_count': history.count('batsu'),
                'workbook_ref': q.get('workbook_ref', '')
            })
        
        return result
