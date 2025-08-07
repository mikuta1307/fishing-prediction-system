#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本牧海釣り施設 スクレイピング共通処理（Google Sheets版 - 追記機能対応）
ローカルとVercel両方で使用される共通ロジック + Google Sheets投入機能（重複防止対応）+ 詳細ログ
"""

import time
import os
import re
import csv
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Google Sheets関連のインポート
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("⚠️ Google Sheets関連ライブラリが見つかりません。以下を実行してください：")
    print("pip install gspread google-auth google-auth-oauthlib google-auth-httplib2")

class ScrapingCore:
    """スクレイピング共通処理クラス"""
    
    def __init__(self, headless=True):
        """初期化"""
        self.driver = None
        self.target_url = "https://yokohama-fishingpiers.jp/honmoku/fishing-history"
        self.headless = headless
        
        # 環境判定（ローカル or Vercel）
        self.is_vercel = os.environ.get('VERCEL') == '1'
        
        if self.is_vercel:
            # Vercel環境（自動WebDriver）
            print("🌐 Vercel環境で実行中")
        else:
            # ローカル環境（Chrome for Testing）
            print("🏠 ローカル環境で実行中")
            self.chrome_path = r"C:\Users\kataoka.akihito\Downloads\tools\chrome\chrome-win64_Stable_133.0.6943.98\chrome-win64\chrome.exe"
            self.chromedriver_path = r"C:\Users\kataoka.akihito\Downloads\tools\chrome\chromedriver-win64_Stable_133.0.6943.98\chromedriver-win64\chromedriver.exe"
    
    def setup_driver(self):
        """WebDriver初期化（環境自動判定）"""
        try:
            print("🔧 Chrome WebDriverを準備中...")
            
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            if self.is_vercel:
                # Vercel環境: 自動WebDriver
                self.driver = webdriver.Chrome(options=options)
            else:
                # ローカル環境: 手動パス指定
                options.binary_location = self.chrome_path
                service = Service(executable_path=self.chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            
            self.driver.implicitly_wait(10)
            print("✅ WebDriver初期化完了")
            return True
            
        except Exception as e:
            print(f"❌ WebDriver初期化エラー: {e}")
            return False
    
    def scrape_period(self, target_year_month):
        """指定年月の釣果データをスクレイピング実行"""
        try:
            # 年月解析
            year = int(target_year_month[:4])
            month = int(target_year_month[4:])
            
            print(f"🎣 釣果データ抽出開始: {year}年{month:02d}月")
            
            print(f"🗓️ {year}年{month:02d}月のデータを処理中...")
            
            # 検索フォームで年月を設定
            if not self._set_search_period(year, month):
                print(f"❌ {year}年{month:02d}月の検索設定に失敗")
                return {
                    'success': False,
                    'error': f'{year}年{month:02d}月の検索設定に失敗'
                }
            
            # 検索実行
            if not self._execute_search():
                print(f"❌ {year}年{month:02d}月の検索実行に失敗")
                return {
                    'success': False,
                    'error': f'{year}年{month:02d}月の検索実行に失敗'
                }
            
            # 検索結果からデータ抽出（釣果とコメントを分離）
            fishing_data, comment_data = self._extract_monthly_data(year, month)
            if fishing_data:
                print(f"✅ {year}年{month:02d}月完了 - 釣果: {len(fishing_data)}件, コメント: {len(comment_data)}件")
                
                # CSVファイル出力
                fishing_csv = f"fishing_results_{target_year_month}.csv"
                comment_csv = f"daily_comments_{target_year_month}.csv"
                
                # 釣果データCSV
                fishing_headers = ['日付', '天気', '水温', '潮', '来場者数', '魚種', '釣果数', 'サイズ', '釣り場']
                self._save_to_csv(fishing_data, fishing_headers, fishing_csv)
                
                # コメントデータCSV
                comment_headers = ['日付', '天気', '水温', '潮', '来場者数', 'コメント']
                self._save_to_csv(comment_data, comment_headers, comment_csv)
                
                print(f"💾 釣果データCSV出力完了: {fishing_csv}")
                print(f"💾 コメントCSV出力完了: {comment_csv}")
                
                return {
                    'success': True,
                    'total_records': len(fishing_data),
                    'fishing_csv': fishing_csv,
                    'comment_csv': comment_csv,
                    'period': f"{year}年{month:02d}月"
                }
            else:
                print(f"⚠️ {year}年{month:02d}月 - データなし")
                return {
                    'success': True,
                    'total_records': 0,
                    'fishing_csv': None,
                    'comment_csv': None,
                    'period': f"{year}年{month:02d}月"
                }
            
        except Exception as e:
            print(f"❌ 釣果データ抽出エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def access_site(self):
        """サイトアクセス"""
        try:
            print(f"🌐 サイトアクセス中: {self.target_url}")
            self.driver.get(self.target_url)
            
            # ページロード完了を待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            title = self.driver.title
            current_url = self.driver.current_url
            
            print(f"✅ サイトアクセス成功")
            print(f"📄 ページタイトル: {title}")
            print(f"🔗 現在のURL: {current_url}")
            
            return True
            
        except Exception as e:
            print(f"❌ サイトアクセスエラー: {e}")
            return False

    def _set_search_period(self, year, month):
        """検索フォームで年月を設定"""
        try:
            print(f"📅 検索期間設定: {year}年{month:02d}月")
            
            # 年選択
            year_dropdown = self.driver.find_element(By.CSS_SELECTOR, ".v-select__menu-icon")
            year_dropdown.click()
            time.sleep(1)
            
            year_option = self.driver.find_element(By.XPATH, f"//div[contains(@class, 'v-list-item') and text()='{year}']")
            year_option.click()
            time.sleep(1)
            
            # 月選択
            month_dropdowns = self.driver.find_elements(By.CSS_SELECTOR, ".v-select__menu-icon")
            month_dropdowns[1].click()
            time.sleep(1)
            
            month_str = f"{month:02d}"
            month_option = self.driver.find_element(By.XPATH, f"//div[contains(@class, 'v-list-item') and text()='{month_str}']")
            month_option.click()
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ 検索期間設定エラー: {e}")
            return False
            
    def _execute_search(self):
        """検索ボタンをクリックして結果を待機"""
        try:
            # 検索ボタンをクリック
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fish-search-btn"))
            )
            search_button.click()
            print("🔍 検索実行中...")
            
            # 検索結果の出現を待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.searched-item"))
            )
            time.sleep(2)  # 追加待機
            
            print("✅ 検索結果ロード完了")
            return True
            
        except TimeoutException:
            print("⚠️ 検索結果の読み込みがタイムアウト")
            return False
        except Exception as e:
            print(f"❌ 検索実行エラー: {e}")
            return False

    def _extract_monthly_data(self, year, month):
        """検索結果から月次データを抽出（釣果とコメントを分離）"""
        try:
            fishing_data_list = []  # 釣果データ用
            comment_data_list = []  # コメントデータ用
            
            # searched-itemを取得
            searched_items = self.driver.find_elements(By.CSS_SELECTOR, "div.searched-item")
            
            for item in searched_items:
                # 日付を抽出
                date_text = item.text.split('\n')[0].strip()
                
                # 環境情報を抽出（共通）
                env_data = self._extract_environment_data(item)
                base_data = {
                    '日付': date_text,
                    **env_data
                }
                
                # 釣果テーブルを抽出
                fishing_data = self._extract_fishing_table(item)
                
                # コメントを抽出
                comment = self._extract_comment(item)
                
                # 釣果データ作成（各魚種ごとに行を作成、コメントは除外）
                for fish in fishing_data:
                    fishing_row = {**base_data, **fish}
                    # コメントキーが含まれている場合は除外
                    fishing_row.pop('コメント', None)
                    fishing_data_list.append(fishing_row)
                
                # コメントデータ作成（1日1行、コメントがある場合のみ）
                if comment.strip():
                    comment_row = {**base_data, 'コメント': comment}
                    comment_data_list.append(comment_row)
            
            return fishing_data_list, comment_data_list
            
        except Exception as e:
            print(f"❌ 月次データ抽出エラー: {e}")
            return [], []

    def _extract_environment_data(self, item):
        """環境情報（天気、水温など）を抽出"""
        try:
            env_data = {'天気': '', '水温': '', '潮': '', '来場者数': ''}
            
            status_chips = item.find_elements(By.CSS_SELECTOR, "span.status-chip")
            
            for chip in status_chips:
                text = chip.text.strip()
                if '天気 :' in text:
                    env_data['天気'] = text.replace('天気 :', '').split('/')[0].strip()
                elif '水温 :' in text:
                    env_data['水温'] = text.replace('水温 :', '').split('/')[0].strip()
                elif '潮 :' in text:
                    env_data['潮'] = text.replace('潮 :', '').split('/')[0].strip()
                elif '来場者数 :' in text:
                    env_data['来場者数'] = text.replace('来場者数 :', '').split('/')[0].strip()
            
            return env_data
            
        except Exception as e:
            print(f"❌ 環境データ抽出エラー: {e}")
            return {'天気': '', '水温': '', '潮': '', '来場者数': ''}

    def _extract_fishing_table(self, item):
        """釣果テーブルからデータを抽出"""
        try:
            fishing_data = []
            
            # テーブルの行を取得
            rows = item.find_elements(By.CSS_SELECTOR, "table.fish-list-tabel tbody tr")
            
            i = 0
            while i < len(rows):
                row = rows[i]
                
                # メインの釣果データ行
                if not 'sp-place' in row.get_attribute('class'):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        # 魚種名
                        fish_name = cells[0].text.strip()
                        
                        # 釣果数（正規表現で数値抽出）
                        count_text = cells[1].text.strip()
                        count_match = re.search(r'(\d+)', count_text)
                        fish_count = count_match.group(1) if count_match else '0'
                        
                        # サイズ
                        fish_size = cells[2].text.strip()
                        
                        # 釣り場（テキストをそのまま取得）
                        fishing_area = cells[3].text.strip()
                        
                        fishing_data.append({
                            '魚種': fish_name,
                            '釣果数': fish_count,
                            'サイズ': fish_size,
                            '釣り場': fishing_area
                        })
                
                i += 1
            
            return fishing_data
            
        except Exception as e:
            print(f"❌ 釣果テーブル抽出エラー: {e}")
            return []

    def _extract_comment(self, item):
        """コメントテキストを抽出"""
        try:
            comment_elements = item.find_elements(By.CSS_SELECTOR, "div.sentence")
            if comment_elements:
                return comment_elements[0].text.strip()
            return ""
        except Exception as e:
            print(f"❌ コメント抽出エラー: {e}")
            return ""

    def _save_to_csv(self, data, headers, filename):
        """データをCSVファイルに保存"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            print(f"💾 {len(data)}件のデータを{filename}に保存しました")
        except Exception as e:
            print(f"❌ CSV保存エラー: {e}")
    
    def cleanup(self):
        """クリーンアップ"""
        try:
            if self.driver:
                self.driver.quit()
                print("✅ WebDriverクリーンアップ完了")
        except Exception as e:
            print(f"❌ クリーンアップエラー: {e}")

# =============================================================================
# Google Sheets投入機能（追記機能対応版）
# =============================================================================

def setup_google_sheets_client():
    """Google Sheets クライアント初期化"""
    try:
        if not GOOGLE_SHEETS_AVAILABLE:
            return None, "Google Sheetsライブラリが利用できません"
        
        # 認証ファイルパス
        credentials_path = r"C:\Users\kataoka.akihito\Documents\MyPython\env313\choka-389510-1103575d64ab.json"
        
        if not os.path.exists(credentials_path):
            return None, f"認証ファイルが見つかりません: {credentials_path}"
        
        # Google Sheets API のスコープ
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # サービスアカウント認証
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(credentials)
        
        return client, None
        
    except Exception as e:
        return None, f"Google Sheetsクライアント初期化エラー: {e}"

def parse_date_for_sort(date_str):
    """日付文字列をソート用の日付オブジェクトに変換"""
    try:
        # "2025/07/28(月)" -> "2025/07/28"
        date_part = date_str.split('(')[0]
        return datetime.strptime(date_part, '%Y/%m/%d')
    except:
        # パースできない場合は最小日付を返す
        return datetime(1900, 1, 1)

def append_data_to_worksheet(worksheet, new_df, sheet_type="データ"):
    """ワークシートにデータを追記（重複チェック付き）"""
    try:
        print(f"📋 {sheet_type}の既存データをチェック中...")
        
        # 既存データを取得
        existing_data = worksheet.get_all_records()
        
        if existing_data:
            existing_df = pd.DataFrame(existing_data)
            print(f"📊 既存{sheet_type}: {len(existing_df)}行")
            
            # 重複チェック（日付ベース）
            if sheet_type == "釣果データ":
                # 釣果データの場合: 日付+魚種で重複チェック
                existing_keys = set(
                    existing_df['日付'].astype(str) + '_' + existing_df['魚種'].astype(str)
                )
                new_keys = new_df['日付'].astype(str) + '_' + new_df['魚種'].astype(str)
                mask = ~new_keys.isin(existing_keys)
            else:
                # コメントデータの場合: 日付のみで重複チェック
                existing_keys = set(existing_df['日付'].astype(str))
                new_keys = new_df['日付'].astype(str)
                mask = ~new_keys.isin(existing_keys)
            
            # 新規データのみを抽出
            unique_new_df = new_df[mask].copy()
            
            if len(unique_new_df) == 0:
                print(f"⚠️ 新規{sheet_type}なし（すべて既存データと重複）")
                return 0
            
            print(f"✅ 新規{sheet_type}: {len(unique_new_df)}行（重複除外: {len(new_df) - len(unique_new_df)}行）")
            
            # 既存データと新規データを結合
            combined_df = pd.concat([existing_df, unique_new_df], ignore_index=True)
        else:
            print(f"📝 {sheet_type}シートが空 - 全データを追加")
            combined_df = new_df.copy()
            unique_new_df = new_df.copy()
        
        # 日付順でソート
        print(f"🔄 {sheet_type}を日付順でソート中...")
        combined_df['_sort_date'] = combined_df['日付'].apply(parse_date_for_sort)
        combined_df = combined_df.sort_values('_sort_date').drop('_sort_date', axis=1)
        
        # シート全体を更新（ヘッダー含む）
        print(f"📤 {sheet_type}シート全体を更新中...")
        worksheet.clear()
        
        # ヘッダー + データを一括投入
        headers = combined_df.columns.tolist()
        all_data = [headers] + combined_df.values.tolist()
        
        worksheet.update('A1', all_data, value_input_option='USER_ENTERED')
        print(f"✅ {sheet_type}更新完了: 総計{len(combined_df)}行（新規追加: {len(unique_new_df)}行）")
        
        return len(unique_new_df)
        
    except Exception as e:
        print(f"❌ {sheet_type}追記エラー: {e}")
        import traceback
        traceback.print_exc()
        return 0

def upload_to_google_sheets_func(fishing_csv_filename, comment_csv_filename):
    """Google Sheets投入（追記機能対応版）"""
    try:
        print(f"📤 Google Sheets投入開始（追記版）")
        print(f"  釣果データ: {fishing_csv_filename}")
        print(f"  コメント: {comment_csv_filename}")
        
        # Google Sheetsクライアント初期化
        client, error = setup_google_sheets_client()
        if error:
            print(f"❌ Google Sheetsクライアント初期化エラー: {error}")
            return {'success': False, 'error': error}
        
        print(f"✅ Google Sheetsクライアント初期化完了")
        
        # スプレッドシート取得・作成
        spreadsheet_name = "本牧海釣り施設データ"
        try:
            spreadsheet = client.open(spreadsheet_name)
            print(f"✅ 既存スプレッドシート使用: {spreadsheet_name}")
            
            # 既存スプレッドシートにも共有設定を適用
            try:
                spreadsheet.share(None, perm_type='anyone', role='writer')
                print(f"✅ 既存スプレッドシートを「リンクを知っている全員」に共有しました")
            except Exception as share_error:
                print(f"⚠️ 共有設定エラー: {share_error}")
                
        except:
            spreadsheet = client.create(spreadsheet_name)
            print(f"✅ 新規スプレッドシート作成: {spreadsheet_name}")
            
            # リンクを知っている全員がアクセス可能に設定
            try:
                spreadsheet.share(None, perm_type='anyone', role='writer')
                print(f"✅ スプレッドシートを「リンクを知っている全員」に共有しました")
            except Exception as share_error:
                print(f"⚠️ 共有設定エラー: {share_error}")
        
        results = {
            'success': True,
            'spreadsheet_url': f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}",
            'message': f"Google Sheets投入完了",
            'fishing_count': 0,
            'comment_count': 0
        }
        
        # 釣果データ処理（追記版）
        if fishing_csv_filename and os.path.exists(fishing_csv_filename):
            print("\n🎣 釣果データ処理開始...")
            new_fishing_df = pd.read_csv(fishing_csv_filename, encoding='utf-8')
            
            try:
                fishing_worksheet = spreadsheet.worksheet("釣果データ")
                print("📋 既存の釣果データシートを使用")
            except:
                fishing_worksheet = spreadsheet.add_worksheet(title="釣果データ", rows=1000, cols=20)
                print("✅ 新規釣果データシート作成")
            
            # 追記処理
            added_fishing = append_data_to_worksheet(fishing_worksheet, new_fishing_df, "釣果データ")
            results['fishing_count'] = added_fishing
        
        # コメントデータ処理（追記版）
        if comment_csv_filename and os.path.exists(comment_csv_filename):
            print("\n💬 コメントデータ処理開始...")
            new_comment_df = pd.read_csv(comment_csv_filename, encoding='utf-8')
            
            try:
                comment_worksheet = spreadsheet.worksheet("コメント")
                print("📋 既存のコメントシートを使用")
            except:
                comment_worksheet = spreadsheet.add_worksheet(title="コメント", rows=1000, cols=20)
                print("✅ 新規コメントシート作成")
            
            # 追記処理
            added_comment = append_data_to_worksheet(comment_worksheet, new_comment_df, "コメントデータ")
            results['comment_count'] = added_comment
        
        # 結果メッセージ更新
        total_added = results['fishing_count'] + results['comment_count']
        results['message'] = f"Google Sheets追記完了: 釣果{results['fishing_count']}行, コメント{results['comment_count']}行 (新規追加計{total_added}行)"
        
        print(f"\n📊 追記結果:")
        print(f"   - 釣果データ: {results['fishing_count']}行追加")
        print(f"   - コメントデータ: {results['comment_count']}行追加")
        print(f"   - 合計: {total_added}行追加")
        print(f"🔗 スプレッドシートURL: {results['spreadsheet_url']}")
        print(f"📋 ブラウザで確認してください")
        
        return results
        
    except Exception as e:
        error_msg = f"Google Sheets投入エラー: {e}"
        print(f"❌ {error_msg}")
        import traceback
        print("📋 エラー詳細:")
        traceback.print_exc()
        return {'success': False, 'error': error_msg}

def run_scraping(target_year_month, headless=True, upload_to_sheets=True):
    """スクレイピング実行（Google Sheets投入版）"""
    scraper = ScrapingCore(headless=headless)
    
    try:
        # WebDriver初期化
        if not scraper.setup_driver():
            return {'success': False, 'error': 'WebDriver初期化失敗'}
        
        # サイトアクセス
        if not scraper.access_site():
            return {'success': False, 'error': 'サイトアクセス失敗'}
        
        # スクレイピング実行
        result = scraper.scrape_period(target_year_month)
        
        if not result['success']:
            return result
        
        # Google Sheets投入処理
        if upload_to_sheets and result['total_records'] > 0:
            print("\n" + "="*60)
            print("📤 Google Sheets投入処理開始")
            print("="*60)
            
            sheets_result = upload_to_google_sheets_func(
                result['fishing_csv'], 
                result['comment_csv']
            )
            
            result['sheets_result'] = sheets_result
        elif upload_to_sheets and result['total_records'] == 0:
            print("⚠️ データが0件のためGoogle Sheets投入をスキップしました")
            result['sheets_result'] = {'success': True, 'message': 'データなしのためスキップ'}
        else:
            print("⚠️ Google Sheets投入がスキップされました（--no-sheetsオプション）")
            result['sheets_result'] = {'success': True, 'message': 'スキップ'}
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        scraper.cleanup()