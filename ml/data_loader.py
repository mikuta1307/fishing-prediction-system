#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheetsからの釣果データ読み込みモジュール
本牧海釣り施設の釣果データとコメントデータを取得し、機械学習用に前処理
"""

import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re

class FishingDataLoader:
    """釣果データ読み込みクラス"""
    
    def __init__(self, credentials_path=None):
        """
        初期化
        
        Args:
            credentials_path (str): Google Sheets認証ファイルパス
        """
        if credentials_path is None:
            # デフォルトの認証ファイルパス
            credentials_path = r"C:\Users\kataoka.akihito\Documents\MyPython\env313\choka-389510-1103575d64ab.json"
        
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self.spreadsheet_name = "本牧海釣り施設データ"
    
    def setup_client(self):
        """Google Sheetsクライアント初期化"""
        try:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"認証ファイルが見つかりません: {self.credentials_path}")
            
            # Google Sheets API のスコープ
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # サービスアカウント認証
            credentials = Credentials.from_service_account_file(self.credentials_path, scopes=scope)
            self.client = gspread.authorize(credentials)
            
            # スプレッドシート取得
            self.spreadsheet = self.client.open(self.spreadsheet_name)
            
            print(f"✅ Google Sheetsクライアント初期化完了")
            print(f"📊 スプレッドシート: {self.spreadsheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Google Sheets初期化エラー: {e}")
            return False
    
    def load_fishing_data(self):
        """
        釣果データを読み込み
        
        Returns:
            pd.DataFrame: 釣果データ（前処理済み）
        """
        try:
            if not self.client:
                if not self.setup_client():
                    return None
            
            print("📊 釣果データ読み込み中...")
            
            # 釣果データシートから読み込み
            fishing_sheet = self.spreadsheet.worksheet("釣果データ")
            fishing_records = fishing_sheet.get_all_records()
            
            if not fishing_records:
                print("⚠️ 釣果データが見つかりません")
                return None
            
            # DataFrameに変換
            df = pd.DataFrame(fishing_records)
            
            print(f"✅ 釣果データ読み込み完了: {len(df)}行")
            print(f"📅 期間: {df['日付'].min()} ～ {df['日付'].max()}")
            
            # 基本的な前処理
            df = self._preprocess_fishing_data(df)
            
            return df
            
        except Exception as e:
            print(f"❌ 釣果データ読み込みエラー: {e}")
            return None
    
    def load_comment_data(self):
        """
        コメントデータを読み込み
        
        Returns:
            pd.DataFrame: コメントデータ（前処理済み）
        """
        try:
            if not self.client:
                if not self.setup_client():
                    return None
            
            print("💬 コメントデータ読み込み中...")
            
            # コメントシートから読み込み
            comment_sheet = self.spreadsheet.worksheet("コメント")
            comment_records = comment_sheet.get_all_records()
            
            if not comment_records:
                print("⚠️ コメントデータが見つかりません")
                return None
            
            # DataFrameに変換
            df = pd.DataFrame(comment_records)
            
            print(f"✅ コメントデータ読み込み完了: {len(df)}行")
            
            # 基本的な前処理
            df = self._preprocess_comment_data(df)
            
            return df
            
        except Exception as e:
            print(f"❌ コメントデータ読み込みエラー: {e}")
            return None
    
    def _preprocess_fishing_data(self, df):
        """釣果データの前処理"""
        try:
            print("🔧 釣果データ前処理中...")
            
            # 日付処理
            df['日付_parsed'] = df['日付'].apply(self._parse_date)
            df['年'] = df['日付_parsed'].dt.year
            df['月'] = df['日付_parsed'].dt.month
            df['日'] = df['日付_parsed'].dt.day
            df['曜日'] = df['日付_parsed'].dt.dayofweek  # 0=月曜日
            
            # 数値データの処理
            df['釣果数'] = pd.to_numeric(df['釣果数'], errors='coerce').fillna(0)
            
            # 水温の数値化（"26.0℃" -> 26.0）
            df['水温_数値'] = df['水温'].apply(self._extract_temperature)
            
            # 来場者数の数値化（"400名" -> 400）
            df['来場者数_数値'] = df['来場者数'].apply(self._extract_visitor_count)
            
            # 欠損値の処理
            df = df.dropna(subset=['日付_parsed'])
            
            print(f"✅ 釣果データ前処理完了: {len(df)}行")
            
            return df
            
        except Exception as e:
            print(f"❌ 釣果データ前処理エラー: {e}")
            return df
    
    def _preprocess_comment_data(self, df):
        """コメントデータの前処理"""
        try:
            print("🔧 コメントデータ前処理中...")
            
            # 日付処理
            df['日付_parsed'] = df['日付'].apply(self._parse_date)
            df['年'] = df['日付_parsed'].dt.year
            df['月'] = df['日付_parsed'].dt.month
            df['日'] = df['日付_parsed'].dt.day
            df['曜日'] = df['日付_parsed'].dt.dayofweek
            
            # 水温・来場者数の数値化
            df['水温_数値'] = df['水温'].apply(self._extract_temperature)
            df['来場者数_数値'] = df['来場者数'].apply(self._extract_visitor_count)
            
            # 欠損値の処理
            df = df.dropna(subset=['日付_parsed'])
            
            print(f"✅ コメントデータ前処理完了: {len(df)}行")
            
            return df
            
        except Exception as e:
            print(f"❌ コメントデータ前処理エラー: {e}")
            return df
    
    def _parse_date(self, date_str):
        """日付文字列をdatetimeに変換"""
        try:
            # "2025/07/28(月)" -> "2025/07/28"
            date_part = str(date_str).split('(')[0].strip()
            return pd.to_datetime(date_part, format='%Y/%m/%d')
        except:
            return pd.NaT
    
    def _extract_temperature(self, temp_str):
        """水温文字列から数値を抽出"""
        try:
            # "26.0℃" -> 26.0
            match = re.search(r'(\d+\.?\d*)', str(temp_str))
            if match:
                return float(match.group(1))
            return None
        except:
            return None
    
    def _extract_visitor_count(self, visitor_str):
        """来場者数文字列から数値を抽出"""
        try:
            # "400名" -> 400
            match = re.search(r'(\d+)', str(visitor_str))
            if match:
                return int(match.group(1))
            return None
        except:
            return None
    
    def get_data_summary(self):
        """データサマリー情報を取得"""
        try:
            fishing_df = self.load_fishing_data()
            comment_df = self.load_comment_data()
            
            if fishing_df is None and comment_df is None:
                return None
            
            summary = {}
            
            if fishing_df is not None:
                summary['fishing'] = {
                    'total_records': len(fishing_df),
                    'date_range': {
                        'start': fishing_df['日付'].min(),
                        'end': fishing_df['日付'].max()
                    },
                    'total_catch': fishing_df['釣果数'].sum(),
                    'unique_species': fishing_df['魚種'].nunique(),
                    'species_list': fishing_df['魚種'].unique().tolist()
                }
            
            if comment_df is not None:
                summary['comment'] = {
                    'total_records': len(comment_df),
                    'date_range': {
                        'start': comment_df['日付'].min(),
                        'end': comment_df['日付'].max()
                    }
                }
            
            return summary
            
        except Exception as e:
            print(f"❌ データサマリー取得エラー: {e}")
            return None

def load_all_data():
    """
    便利関数: 全データを一括読み込み
    
    Returns:
        tuple: (fishing_df, comment_df)
    """
    loader = FishingDataLoader()
    
    fishing_df = loader.load_fishing_data()
    comment_df = loader.load_comment_data()
    
    return fishing_df, comment_df

def main():
    """テスト実行用"""
    print("🎣 釣果データ読み込みテスト")
    print("=" * 50)
    
    loader = FishingDataLoader()
    
    # データサマリー表示
    summary = loader.get_data_summary()
    if summary:
        print("📊 データサマリー:")
        if 'fishing' in summary:
            fishing_info = summary['fishing']
            print(f"  釣果データ: {fishing_info['total_records']}行")
            print(f"  期間: {fishing_info['date_range']['start']} ～ {fishing_info['date_range']['end']}")
            print(f"  総釣果数: {fishing_info['total_catch']}匹")
            print(f"  魚種数: {fishing_info['unique_species']}種類")
            print(f"  魚種: {', '.join(fishing_info['species_list'][:5])}{'...' if len(fishing_info['species_list']) > 5 else ''}")
        
        if 'comment' in summary:
            comment_info = summary['comment']
            print(f"  コメントデータ: {comment_info['total_records']}行")
    
    print("\n✅ データ読み込みテスト完了")

if __name__ == "__main__":
    main()