#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本牧海釣り施設 Webスクレイピング処理（コマンドライン用）
api/scraping_core.py の共通処理を呼び出す - Google Sheets投入機能統合版
"""

import argparse
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加（api/scraping_core.pyをインポートできるように）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.scraping_core import run_scraping

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='本牧海釣り施設 スクレイピング処理 + Google Sheets投入')
    parser.add_argument('year_month', nargs='?', help='対象年月 (例: 202507, 省略時は当月)')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモード')
    parser.add_argument('--no-sheets', action='store_true', help='Google Sheets投入をスキップ（CSVのみ出力）')
    
    args = parser.parse_args()
    
    # 当月を取得
    current_date = datetime.now()
    current_year_month = current_date.strftime('%Y%m')
    
    # 引数が省略された場合の処理
    target_year_month = args.year_month if args.year_month else current_year_month
    
    # 年月形式の簡単なバリデーション
    if len(target_year_month) != 6:
        print("❌ 年月の形式が正しくありません。YYYYMM形式で入力してください（例: 202507）")
        sys.exit(1)
    
    try:
        int(target_year_month)
    except ValueError:
        print("❌ 年月は数字で入力してください（例: 202507）")
        sys.exit(1)
    
    # 自動選択された場合の表示
    auto_selected = not args.year_month
    
    print("🎣 本牧海釣り施設 Webスクレイピング（コマンドライン版）")
    print("=" * 60)
    if auto_selected:
        print(f"📅 自動選択: 当月 ({current_year_month})")
    print(f"対象年月: {target_year_month}")
    print(f"モード: {'ヘッドレス' if args.headless else '通常'}")
    print(f"Google Sheets投入: {'無効' if args.no_sheets else '有効'}")
    print("=" * 60)
    
    # Google Sheets投入フラグ（--no-sheetsが指定された場合はFalse）
    upload_to_sheets = not args.no_sheets
    
    # 共通スクレイピング処理を実行
    result = run_scraping(
        target_year_month=target_year_month,
        headless=args.headless,
        upload_to_sheets=upload_to_sheets
    )
    
    if result['success']:
        print("\n" + "=" * 60)
        print("✅ すべての処理が正常に完了しました")
        print("=" * 60)
        print(f"📊 処理結果: {result['period']}")
        print(f"📈 抽出件数: {result['total_records']}件")
        
        if result['fishing_csv']:
            print(f"💾 釣果データファイル: {result['fishing_csv']}")
        if result['comment_csv']:
            print(f"💾 コメントファイル: {result['comment_csv']}")
        
        # Google Sheets投入結果表示
        sheets_result = result.get('sheets_result', {})
        if upload_to_sheets:
            if sheets_result.get('success'):
                print(f"✅ Google Sheets投入: 成功")
                if 'message' in sheets_result:
                    print(f"   {sheets_result['message']}")
                if 'spreadsheet_url' in sheets_result:
                    print(f"🔗 スプレッドシートURL: {sheets_result['spreadsheet_url']}")
            else:
                print(f"❌ Google Sheets投入: 失敗")
                if 'error' in sheets_result:
                    print(f"   エラー: {sheets_result['error']}")
                print("💾 CSVファイルは保持されています")
        else:
            print("⚠️ Google Sheets投入: スキップ（--no-sheetsオプション指定）")
        
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"\n❌処理が失敗しました: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()