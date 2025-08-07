#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Next.js API Route for スクレイピング処理
共通処理を呼び出してスクレイピングを実行
"""

import json
from http.server import BaseHTTPRequestHandler

# 共通スクレイピング処理をインポート
from .scraping_core import run_scraping

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # リクエストボディの読み取り
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            start_year = data.get('startYear', '2024')
            start_month = data.get('startMonth', '1')
            end_year = data.get('endYear', '2024') 
            end_month = data.get('endMonth', '12')
            
            # 年月形式変換
            start_year_month = f"{start_year}{start_month.zfill(2)}"
            end_year_month = f"{end_year}{end_month.zfill(2)}"
            
            print(f"📋 スクレイピング要求受信:")
            print(f"   期間: {start_year}年{start_month}月 〜 {end_year}年{end_month}月")
            
            # 共通スクレイピング処理を実行
            result = run_scraping(
                start_year_month=start_year_month,
                end_year_month=end_year_month,
                headless=True  # Vercel上では常にヘッドレス
            )
            
            if result['success']:
                # 成功
                response_data = {
                    'success': True,
                    'message': 'スクレイピング処理が正常に完了しました',
                    'data': {
                        'period': result['period'],
                        'total_months': result['total_months'],
                        'processed_months': result['processed_months'],
                        'status': 'completed'
                    }
                }
            else:
                # エラー
                response_data = {
                    'success': False,
                    'message': f'スクレイピング処理でエラーが発生しました: {result["error"]}',
                    'error': result['error']
                }
            
            # レスポンス送信
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(response_data, ensure_ascii=False)
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ API処理エラー: {e}")
            self.send_error(500, f'内部エラー: {str(e)}')
    
    def do_OPTIONS(self):
        # CORS プリフライトリクエスト対応
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()