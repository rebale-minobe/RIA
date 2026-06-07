#!/usr/bin/env python3
"""
RIA 再TEST用：階層選択ロジック（修正版）

CSV に chapter_number/chapter_title がない場合、
lesson_title から自動抽出する
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
        
        # 章を取得（lesson_titleから自動抽出）
        chapters = {}
        lessons_by_chapter = defaultdict(dict)
        questions_by_lesson = defaultdict(list)
        
        for row in self.data:
            page = row.get('page', '')
            lesson_title = row.get('lesson_title', '')
            
            # 章情報を推測（lesson_titleから）
            # ※ 本来は JSON から取得するが、CSV のみの場合は lesson_title で代用
            chapter_num = f"Chapter_{page}"  # 簡易版：ページから生成
            chapter_title = lesson_title  # 簡易版：lesson_titleを使用
            
            # 実装注：本格化したら、JSON から正式な章情報を取得すること
            
            # 章を登録
            if lesson_title:
                chapters[chapter_num] = chapter_title
                
                # lesson_title を登録（重複排除）
                lesson_key = f"{page}|{lesson_title}"
                lessons_by_chapter[chapter_num][lesson_key] = {
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
        章一覧を返す（ページ順でソート）
        戻り値: [(chapter_number, chapter_title), ...]
        """
        if not self.chapters:
            return []
        
        # Chapter_N の N を抽出してソート
        def extract_chapter_num(chapter_key):
            try:
                num = int(chapter_key.replace('Chapter_', ''))
                return num
            except:
                return 999
        
        sorted_chapters = sorted(self.chapters.items(), 
                                key=lambda x: extract_chapter_num(x[0]))
        return sorted_chapters
    
    def get_lessons_in_chapter(self, chapter_number: str) -> List[Dict]:
        """
        指定章内のlesson_titleを返す（進捗情報付き）
        
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
        
        if chapter_number not in self.lessons_by_chapter:
            return lessons
        
        for lesson_key, lesson_info in self.lessons_by_chapter[chapter_number].items():
            page = lesson_info['page']
            lesson_title = lesson_info['lesson_title']
            
            # 進捗を計算
            questions = self.questions_by_lesson.get(lesson_key, [])
            total_count = len(questions)
            
            # 最新結果で集計（各問題の最後の回答を見る）
            maru_count = 0
            batsu_count = 0
            
            for q in questions:
                # 日付カラムを右から見て、最初に見つかった結果を採用
                latest_result = None
                for col in reversed(list(q.keys())):
                    if col not in ['page', 'chapter_number', 'chapter_title', 
                                    'lesson_title', 'section_code', 'q_label', 'answer']:
                        if q[col]:  # 空でない
                            latest_result = q[col]
                            break
                
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
        指定lesson内の問題を返す
        
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
            },
            ...
          ]
        """
        questions = self.questions_by_lesson.get(lesson_key, [])
        
        result = []
        for q in questions:
            # 日付カラムを時系列で見て、結果履歴を作る
            history = []
            date_cols = [col for col in q.keys() 
                        if col not in ['page', 'chapter_number', 'chapter_title', 
                                       'lesson_title', 'section_code', 'q_label', 'answer']]
            
            for col in date_cols:
                if q[col]:
                    history.append(q[col])
            
            latest_result = history[-1] if history else None
            
            # filter_batsu_only の処理
            if filter_batsu_only and latest_result != 'batsu':
                continue
            
            result.append({
                'page': q['page'],
                'section_code': q['section_code'],
                'q_label': q['q_label'],
                'answer': q['answer'],
                'latest_result': latest_result,
                'history': history,
                'error_count': history.count('batsu')
            })
        
        return result


def main():
    """テスト実行"""
    csv_path = Path('/mnt/user-data/outputs/answer_log_social_pivot_v2.csv')
    
    print("📖 ピボットCSVを読み込み...\n")
    log = AnswerLogPivot.load_csv(str(csv_path))
    
    # 1. 章一覧
    print("【章一覧】")
    for chapter_num, chapter_title in log.get_chapters()[:5]:  # 最初の5つだけ表示
        print(f"  {chapter_num}: {chapter_title}")
    
    # 2. 最初の章 → lesson一覧
    chapters = log.get_chapters()
    if chapters:
        first_chapter = chapters[0]
        print(f"\n【{first_chapter[1]} のlesson一覧】")
        lessons = log.get_lessons_in_chapter(first_chapter[0])
        for lesson in lessons[:3]:
            total = lesson['total_count']
            maru = lesson['maru_count']
            batsu = lesson['batsu_count']
            progress = f"⭕{maru}/{total}" if maru > 0 else f"❌{total}"
            print(f"  📖 {lesson['lesson_title']} (p{lesson['page']}) 【{progress}】")
    
    # 3. lesson を選択 → 問題取得（×のみ）
    if lessons:
        first_lesson = lessons[0]
        print(f"\n【{first_lesson['lesson_title']} の未解決問題】")
        questions = log.get_questions_in_lesson(first_lesson['lesson_key'], 
                                               filter_batsu_only=True)
        print(f"  未解決: {len(questions)} 問")
        for q in questions[:3]:
            print(f"    p{q['page']} [{q['section_code']}] {q['q_label']}: {q['answer']}")
            print(f"      誤答回数: {q['error_count']}, 履歴: {q['history'][-3:]}")

if __name__ == '__main__':
    main()
