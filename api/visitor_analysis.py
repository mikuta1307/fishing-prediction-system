"""
本牧海釣り施設 - 動的来場者数分析システム
Phase 5.6: Google Sheetsから天気×曜日別の来場者数平均をリアルタイム計算

毎日蓄積されるデータから常に最新の平均値を算出
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisitorAnalyzer:
    """来場者数動的分析クラス"""
    
    def __init__(self):
        """
        分析器初期化（環境変数認証版）
        """
        self.gc = None
        self.sheet = None
        
        # 曜日マッピング
        self.weekday_names = {
            0: 'monday',    # 月曜日
            1: 'tuesday',   # 火曜日
            2: 'wednesday', # 水曜日
            3: 'thursday',  # 木曜日
            4: 'friday',    # 金曜日
            5: 'saturday',  # 土曜日
            6: 'sunday'     # 日曜日
        }
        
        # 天気マッピング（日本語 → 英語）- 完全版
        self.weather_mapping = {
            '晴れ': 'sunny',
            '曇り': 'cloudy',
            '雨': 'rainy',
            '雪': 'snowy',
            '快晴': 'sunny',
            '薄曇り': 'cloudy',
            '小雨': 'rainy',
            '大雨': 'rainy',
            '暴風雨': 'rainy',
            # 複合天気パターン
            '曇り時々晴れ': 'cloudy',        # 主に曇り
            '晴れのち曇り': 'sunny',          # 前半が晴れ
            '曇りのち雨': 'rainy',           # 後半が雨
            '雨のち晴れ': 'sunny',           # 後半が晴れ
            '雨のち曇り': 'cloudy',          # 後半が曇り
            '曇りのち晴れ一時雨': 'cloudy',   # 複雑だが主に曇り
            '曇りのち晴れ': 'sunny',         # 後半が晴れ
            '雨一時曇り': 'rainy',           # 主に雨
            '雨時々曇り': 'rainy',           # 主に雨
            '雨のち曇り時々晴れ': 'cloudy',   # 複雑だが曇り寄り
            '晴れのち雨': 'rainy',           # 後半が雨
            '曇り時々雨': 'rainy'            # 雨を含む
        }
        
        self._initialize_sheets()
    
    def _initialize_sheets(self):
        """Google Sheets初期化（ハイブリッド認証版）"""
        try:
            # 認証情報設定
            scopes = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # 1. まず環境変数を試す（Render対応）
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            
            if credentials_json:
                # 環境変数からの認証（Render環境）
                try:
                    credentials_dict = json.loads(credentials_json)
                    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
                    self.gc = gspread.authorize(creds)
                    logger.info("Google Sheets接続成功（環境変数認証）")
                except Exception as env_error:
                    logger.warning(f"環境変数認証でエラー: {env_error}")
                    self.gc = None
            
            # 2. 環境変数が失敗した場合、ファイルパス認証（ローカル環境）
            if not self.gc:
                credentials_path = "credentials/choka-389510-1103575d64ab.json"
                if os.path.exists(credentials_path):
                    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
                    self.gc = gspread.authorize(creds)
                    logger.info("Google Sheets接続成功（ファイル認証）")
                else:
                    logger.error("認証ファイルも環境変数も利用できません")
                    self.gc = None
                    self.sheet = None
                    return
            
            # スプレッドシート接続（historical.pyと同じ名前を使用）
            spreadsheet = self.gc.open("本牧海釣り施設データ")
            self.sheet = spreadsheet.worksheet("釣果データ")
            
        except Exception as e:
            logger.error(f"Google Sheets初期化エラー: {e}")
            self.gc = None
            self.sheet = None
    
    def fetch_latest_data(self) -> pd.DataFrame:
        """
        Google Sheetsから最新データ取得
        
        Returns:
            最新データのDataFrame
        """
        try:
            if not self.sheet:
                raise Exception("Google Sheets未接続")
            
            logger.info("Google Sheetsから最新データ取得開始")
            
            # 全データ取得（ヘッダー重複対応）
            try:
                records = self.sheet.get_all_records()
            except Exception as header_error:
                logger.warning(f"標準的な取得でエラー: {header_error}")
                # ヘッダー重複エラーの場合、手動でヘッダーを指定
                logger.info("手動ヘッダー指定で再試行")
                all_values = self.sheet.get_all_values()
                if len(all_values) > 0:
                    # 最初の行をヘッダーとして使用し、空の列は無視
                    headers = [h if h.strip() else f"col_{i}" for i, h in enumerate(all_values[0])]
                    # 重複を避けるため、連番を追加
                    seen = {}
                    for i, header in enumerate(headers):
                        if header in seen:
                            seen[header] += 1
                            headers[i] = f"{header}_{seen[header]}"
                        else:
                            seen[header] = 0
                    
                    records = []
                    for row in all_values[1:]:
                        record = {}
                        for i, value in enumerate(row):
                            if i < len(headers):
                                record[headers[i]] = value
                        records.append(record)
                else:
                    records = []
            
            df = pd.DataFrame(records)
            
            logger.info(f"取得データ件数: {len(df)}")
            
            # データクリーニング
            df = self._clean_data(df)
            
            logger.info(f"クリーニング後件数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"データ取得エラー: {e}")
            return pd.DataFrame()
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        データクリーニング
        
        Args:
            df: 元DataFrame
            
        Returns:
            クリーニング済みDataFrame
        """
        try:
            # 必要な列が存在するかチェック
            required_columns = ['日付', '天気', '来場者数']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.warning(f"必要な列が不足: {missing_columns}")
                # 代替列名を試す
                column_mapping = {
                    '日付': ['date', 'Date', '日時'],
                    '天気': ['weather', 'Weather', '天候'],
                    '来場者数': ['visitors', 'Visitors', '人数', '来訪者数']
                }
                
                for required_col, alternatives in column_mapping.items():
                    if required_col not in df.columns:
                        for alt in alternatives:
                            if alt in df.columns:
                                df = df.rename(columns={alt: required_col})
                                logger.info(f"列名変更: {alt} → {required_col}")
                                break
            
            # 日付列の処理
            if '日付' in df.columns:
                # 日付から曜日部分を除去（例: "2025/01/31(金)" → "2025/01/31"）
                df['日付'] = df['日付'].astype(str).str.replace(r'\([月火水木金土日]\)', '', regex=True)
                df['日付'] = pd.to_datetime(df['日付'], errors='coerce')
                df = df.dropna(subset=['日付'])
                
                # 曜日追加
                df['曜日番号'] = df['日付'].dt.dayofweek
                df['曜日英語'] = df['曜日番号'].map(self.weekday_names)
            
            # 天気列の処理
            if '天気' in df.columns:
                # マッピング前の天気パターンをログ出力
                unique_weather = df['天気'].unique()
                logger.info(f"データ内の天気パターン: {unique_weather}")
                
                # 天気マッピング実行
                df['天気英語'] = df['天気'].map(self.weather_mapping)
                
                # マッピングされなかった天気をログ出力
                unmapped = df[df['天気英語'].isna()]['天気'].unique()
                if len(unmapped) > 0:
                    logger.warning(f"マッピングされていない天気パターン: {unmapped}")
                
                # マッピングされなかった値は警告してからcloudyにする
                df['天気英語'] = df['天気英語'].fillna('cloudy')
            
            # 来場者数の処理
            if '来場者数' in df.columns:
                # 来場者数から「名」「人」などの単位を除去
                df['来場者数'] = df['来場者数'].astype(str).str.replace(r'[名人]', '', regex=True)
                df['来場者数'] = pd.to_numeric(df['来場者数'], errors='coerce')
                df = df.dropna(subset=['来場者数'])
                # 異常値除外（0-2000人の範囲）
                df = df[(df['来場者数'] >= 0) & (df['来場者数'] <= 2000)]
            
            # 無効なデータを除外
            df = df.dropna(subset=['日付', '天気英語', '曜日英語', '来場者数'])
            
            logger.info("データクリーニング完了")
            return df
            
        except Exception as e:
            logger.error(f"データクリーニングエラー: {e}")
            return df
    
    def calculate_visitor_averages(self) -> Dict[str, Any]:
        """
        天気×曜日別の来場者数平均を計算
        
        Returns:
            平均値辞書と統計情報
        """
        try:
            # 最新データ取得
            df = self.fetch_latest_data()
            
            if df.empty:
                logger.warning("データが取得できませんでした")
                return self._get_fallback_averages()
            
            logger.info("天気×曜日別平均計算開始")
            
            # 結果格納用
            averages = {}
            statistics = {
                'total_records': len(df),
                'date_range': {
                    'start': df['日付'].min().isoformat() if not df.empty else None,
                    'end': df['日付'].max().isoformat() if not df.empty else None
                },
                'weather_counts': {},
                'weekday_counts': {},
                'pattern_counts': {}
            }
            
            # 天気別・曜日別の組み合わせごとに平均計算
            weather_types = ['sunny', 'cloudy', 'rainy', 'snowy']
            weekday_types = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for weather in weather_types:
                for weekday in weekday_types:
                    # 該当データ抽出
                    filtered_data = df[
                        (df['天気英語'] == weather) & 
                        (df['曜日英語'] == weekday)
                    ]
                    
                    key = f"{weather}_{weekday}"
                    
                    if len(filtered_data) > 0:
                        avg_visitors = filtered_data['来場者数'].mean()
                        std_visitors = filtered_data['来場者数'].std()
                        count = len(filtered_data)
                        
                        averages[key] = {
                            'average': round(avg_visitors, 1),
                            'std': round(std_visitors, 1) if not pd.isna(std_visitors) else 0,
                            'count': count,
                            'min': int(filtered_data['来場者数'].min()),
                            'max': int(filtered_data['来場者数'].max())
                        }
                        
                        statistics['pattern_counts'][key] = count
                        
                        logger.info(f"{weather}×{weekday}: {avg_visitors:.1f}人 (n={count})")
                        
                    else:
                        # データがない場合は推定値
                        estimated_avg = self._estimate_missing_pattern(weather, weekday, averages)
                        averages[key] = {
                            'average': estimated_avg,
                            'std': 0,
                            'count': 0,
                            'min': 0,
                            'max': 0,
                            'estimated': True
                        }
                        
                        logger.warning(f"{weather}×{weekday}: データなし、推定値 {estimated_avg}人")
            
            # 統計情報計算
            statistics['weather_counts'] = df['天気英語'].value_counts().to_dict()
            statistics['weekday_counts'] = df['曜日英語'].value_counts().to_dict()
            statistics['overall_average'] = round(df['来場者数'].mean(), 1)
            statistics['calculation_time'] = datetime.now().isoformat()
            
            logger.info(f"天気×曜日別平均計算完了: {len(averages)}パターン")
            
            return {
                'averages': averages,
                'statistics': statistics,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"平均計算エラー: {e}")
            return self._get_fallback_averages()
    
    def _estimate_missing_pattern(self, weather: str, weekday: str, existing_averages: Dict) -> float:
        """
        データが不足しているパターンの推定値計算
        
        Args:
            weather: 天気
            weekday: 曜日
            existing_averages: 既存の平均値
            
        Returns:
            推定来場者数
        """
        try:
            # 同じ天気の他の曜日の平均を使用
            same_weather_avgs = []
            for key, data in existing_averages.items():
                if key.startswith(f"{weather}_") and data['count'] > 0:
                    same_weather_avgs.append(data['average'])
            
            if same_weather_avgs:
                base_avg = np.mean(same_weather_avgs)
            else:
                # 全体的な基準値
                base_avg = 300
            
            # 曜日による調整
            weekday_factors = {
                'monday': 0.8,
                'tuesday': 0.85,
                'wednesday': 0.9,
                'thursday': 0.95,
                'friday': 1.0,
                'saturday': 1.3,
                'sunday': 1.25
            }
            
            # 天気による調整
            weather_factors = {
                'sunny': 1.1,
                'cloudy': 1.0,
                'rainy': 0.7,
                'snowy': 0.5
            }
            
            estimated = base_avg * weekday_factors.get(weekday, 1.0) * weather_factors.get(weather, 1.0)
            return round(estimated, 1)
            
        except Exception as e:
            logger.error(f"推定値計算エラー: {e}")
            return 300.0
    
    def _get_fallback_averages(self) -> Dict[str, Any]:
        """
        エラー時のフォールバック平均値
        （APIエラー時は空のデータで対応）
        
        Returns:
            エラー情報のみ
        """
        logger.error("データ取得に失敗しました")
        
        return {
            'averages': {},
            'statistics': {
                'total_records': 0,
                'status': 'error',
                'calculation_time': datetime.now().isoformat(),
                'error_message': 'データ取得に失敗しました'
            },
            'status': 'error'
        }
    
    def get_visitor_estimate(self, date: str, weather: str) -> Dict[str, Any]:
        """
        特定の日付・天気の来場者数推定
        
        Args:
            date: 日付 (YYYY-MM-DD)
            weather: 天気 (sunny/cloudy/rainy/snowy)
            
        Returns:
            推定結果
        """
        try:
            # 曜日計算
            target_date = datetime.strptime(date, '%Y-%m-%d')
            weekday_num = target_date.weekday()
            weekday_name = self.weekday_names[weekday_num]
            
            # 最新平均値取得
            averages_data = self.calculate_visitor_averages()
            averages = averages_data['averages']
            
            # 該当パターンの平均値取得
            key = f"{weather}_{weekday_name}"
            pattern_data = averages.get(key, {'average': 300, 'count': 0})
            
            return {
                'date': date,
                'weather': weather,
                'weekday': weekday_name,
                'estimated_visitors': pattern_data['average'],
                'data_count': pattern_data['count'],
                'confidence': 'high' if pattern_data['count'] >= 5 else 'medium' if pattern_data['count'] >= 2 else 'low',
                'pattern_key': key,
                'calculation_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"来場者数推定エラー: {e}")
            return {
                'date': date,
                'weather': weather,
                'estimated_visitors': 300,
                'confidence': 'low',
                'error': str(e)
            }


# グローバルアナライザーインスタンス
analyzer = None

def get_analyzer() -> VisitorAnalyzer:
    """アナライザーシングルトン取得"""
    global analyzer
    if analyzer is None:
        analyzer = VisitorAnalyzer()
    return analyzer

def get_visitor_averages() -> Dict[str, Any]:
    """
    来場者数平均取得（FastAPI用）
    
    Returns:
        天気×曜日別平均値辞書
    """
    analyzer_instance = get_analyzer()
    return analyzer_instance.calculate_visitor_averages()

def estimate_visitors(date: str, weather: str) -> Dict[str, Any]:
    """
    来場者数推定（FastAPI用）
    
    Args:
        date: 日付 (YYYY-MM-DD)
        weather: 天気 (sunny/cloudy/rainy/snowy)
        
    Returns:
        推定結果
    """
    analyzer_instance = get_analyzer()
    return analyzer_instance.get_visitor_estimate(date, weather)


if __name__ == "__main__":
    # テスト実行
    print("=== 来場者数分析テスト ===")
    
    result = get_visitor_averages()
    print(f"ステータス: {result['status']}")
    print(f"総データ数: {result['statistics']['total_records']}")
    
    # いくつかのパターンを表示
    averages = result['averages']
    test_patterns = ['sunny_saturday', 'rainy_monday', 'cloudy_friday']
    
    for pattern in test_patterns:
        if pattern in averages:
            data = averages[pattern]
            print(f"{pattern}: {data['average']}人 (n={data['count']})")
    
    # 推定テスト
    estimate = estimate_visitors('2024-08-10', 'sunny')  # 土曜日
    print(f"\n推定テスト: {estimate}")