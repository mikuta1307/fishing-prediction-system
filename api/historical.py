#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
過去データ取得API
Google Sheetsから釣果データを取得してフィルタリング・集計処理
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

# Google Sheets設定（既存システムと統一）
SPREADSHEET_NAME = "本牧海釣り施設データ"
SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

def get_google_sheets_client():
    """Google Sheets クライアントを取得（ハイブリッド認証）"""
    try:
        # 1. まず環境変数を試す（Render対応）
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        
        if credentials_json:
            # 環境変数からの認証（Render環境）
            try:
                credentials_dict = json.loads(credentials_json)
                credentials = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
                client = gspread.authorize(credentials)
                logger.info("Google Sheets client initialized successfully (環境変数認証)")
                return client
            except Exception as env_error:
                logger.warning(f"環境変数認証でエラー: {env_error}")
        
        # 2. ファイルパス認証（ローカル環境）
        credentials_path = "credentials/choka-389510-1103575d64ab.json"
        if os.path.exists(credentials_path):
            credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
            client = gspread.authorize(credentials)
            logger.info("Google Sheets client initialized successfully (ファイル認証)")
            return client
        
        # 3. どちらも失敗した場合
        raise FileNotFoundError("認証ファイルも環境変数も利用できません")
        
    except Exception as e:
        logger.error(f"Google Sheets client initialization failed: {str(e)}")
        raise

def load_fishing_data():
    """釣果データをGoogle Sheetsから読み込み"""
    try:
        client = get_google_sheets_client()
        # 既存システムと同じ方法でスプレッドシートを開く
        spreadsheet = client.open("本牧海釣り施設データ")
        
        # 釣果データシート（既存システムと同じシート名を使用）
        worksheet = spreadsheet.worksheet('釣果データ')
        data = worksheet.get_all_records()
        
        # デバッグ情報
        logger.info(f"Worksheet name: {worksheet.title}")
        logger.info(f"Raw data count: {len(data)}")
        if len(data) > 0:
            logger.info(f"First record keys: {list(data[0].keys())}")
            logger.info(f"First record sample: {data[0]}")
        else:
            logger.warning("No data found in worksheet")
            # 全シート名を確認
            all_sheets = [ws.title for ws in spreadsheet.worksheets()]
            logger.info(f"Available sheets: {all_sheets}")
            # データが入っているシートを探す
            for sheet in spreadsheet.worksheets():
                try:
                    sheet_data = sheet.get_all_records()
                    logger.info(f"Sheet '{sheet.title}': {len(sheet_data)} records")
                except Exception as e:
                    logger.info(f"Sheet '{sheet.title}': Error reading - {str(e)}")
        
        if not data:
            raise ValueError("釣果データが空です")
        
        df = pd.DataFrame(data)
        
        # データ型変換・前処理（既存システムと同じ方法）
        if '日付' in df.columns:
            # "2025/01/31(金)" -> "2025/01/31" に変換してからdatetimeに
            df['日付_clean'] = df['日付'].astype(str).str.split('(').str[0]
            df['日付'] = pd.to_datetime(df['日付_clean'], format='%Y/%m/%d', errors='coerce')
        
        # 数値カラムの変換
        numeric_columns = ['釣果数']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 水温処理：'11.0℃' -> 11.0
        if '水温' in df.columns:
            df['水温'] = df['水温'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
        
        # 来場者数処理：'174名' -> 174  
        if '来場者数' in df.columns:
            df['来場者数'] = df['来場者数'].astype(str).str.extract(r'(\d+)').astype(int)
        
        # 欠損値・異常値の処理
        df = df.dropna(subset=['日付', '魚種'])
        df = df[df['釣果数'] >= 0]  # 負数を除外
        
        logger.info(f"Loaded {len(df)} fishing records from Google Sheets")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load fishing data: {str(e)}")
        raise

async def get_historical_data(
    fish: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    weather: Optional[str] = None,
    tide: Optional[str] = None
) -> Dict[str, Any]:
    """
    過去データを取得・フィルタリング・集計
    """
    try:
        # データ読み込み
        df = load_fishing_data()
        original_count = len(df)
        
        # フィルタリング
        filtered_df = df.copy()
        
        # 魚種フィルター
        if fish and fish.lower() != "all":
            filtered_df = filtered_df[filtered_df['魚種'] == fish]
            logger.info(f"Fish filter applied: {fish}, {len(filtered_df)} records")
        
        # 期間フィルター
        if start_date:
            start_dt = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['日付'] >= start_dt]
            logger.info(f"Start date filter applied: {start_date}, {len(filtered_df)} records")
        
        if end_date:
            end_dt = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df['日付'] <= end_dt]
            logger.info(f"End date filter applied: {end_date}, {len(filtered_df)} records")
        
        # 天気フィルター
        if weather:
            filtered_df = filtered_df[filtered_df['天気'] == weather]
            logger.info(f"Weather filter applied: {weather}, {len(filtered_df)} records")
        
        # 潮フィルター
        if tide:
            filtered_df = filtered_df[filtered_df['潮'] == tide]
            logger.info(f"Tide filter applied: {tide}, {len(filtered_df)} records")
        
        # 日付順ソート（最新優先）
        filtered_df = filtered_df.sort_values('日付', ascending=False)
        
        # 件数制限
        display_df = filtered_df.head(limit)
        
        # レスポンス用データ準備
        records = []
        for _, row in display_df.iterrows():
            record = {
                "日付": row['日付'].strftime('%Y-%m-%d') if pd.notna(row['日付']) else None,
                "天気": row.get('天気', ''),
                "水温": float(row['水温']) if pd.notna(row['水温']) else None,
                "潮": row.get('潮', ''),
                "来場者数": int(row['来場者数']) if pd.notna(row['来場者数']) else None,
                "魚種": row.get('魚種', ''),
                "釣果数": int(row['釣果数']) if pd.notna(row['釣果数']) else 0,
                "サイズ": row.get('サイズ', ''),
                "釣り場": row.get('釣り場', ''),
                "コメント": row.get('コメント', '')
            }
            records.append(record)
        
        # 集計データ生成
        summary = generate_summary(filtered_df, original_count)
        
        return {
            "success": True,
            "message": f"過去データを正常に取得しました（{len(filtered_df)}件中{len(records)}件を表示）",
            "data": {
                "records": records,
                "total_count": len(filtered_df),
                "returned_count": len(records)
            },
            "summary": summary,
            "filters": {
                "fish": fish,
                "start_date": start_date,
                "end_date": end_date,
                "weather": weather,
                "tide": tide,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Historical data processing error: {str(e)}")
        return {
            "success": False,
            "message": "データ取得エラー",
            "error": str(e),
            "data": {
                "records": [],
                "total_count": 0,
                "returned_count": 0
            }
        }

def generate_summary(df: pd.DataFrame, original_count: int) -> Dict[str, Any]:
    """データ集計サマリーを生成"""
    if len(df) == 0:
        return {
            "total_records": 0,
            "message": "条件に一致するデータがありません"
        }
    
    try:
        # 基本統計
        total_catch = df['釣果数'].sum() if '釣果数' in df.columns else 0
        avg_catch = df['釣果数'].mean() if '釣果数' in df.columns and len(df) > 0 else 0
        max_catch = df['釣果数'].max() if '釣果数' in df.columns else 0
        min_catch = df['釣果数'].min() if '釣果数' in df.columns else 0
        
        # 期間情報
        date_range = {}
        if '日付' in df.columns and len(df) > 0:
            date_range = {
                "start": df['日付'].min().strftime('%Y-%m-%d'),
                "end": df['日付'].max().strftime('%Y-%m-%d')
            }
        
        # 月別集計
        by_month = {}
        if '日付' in df.columns:
            monthly = df.groupby(df['日付'].dt.to_period('M'))['釣果数'].agg(['count', 'sum', 'mean']).round(1)
            by_month = {
                str(period): {
                    "days": int(stats['count']),
                    "total_catch": int(stats['sum']),
                    "avg_catch": float(stats['mean'])
                }
                for period, stats in monthly.iterrows()
            }
        
        # 魚種別集計
        by_fish_type = {}
        if '魚種' in df.columns:
            fish_stats = df.groupby('魚種')['釣果数'].agg(['count', 'sum', 'mean']).round(1)
            by_fish_type = {
                fish: {
                    "days": int(stats['count']),
                    "total_catch": int(stats['sum']),
                    "avg_catch": float(stats['mean'])
                }
                for fish, stats in fish_stats.iterrows()
            }
        
        # 天気別集計
        by_weather = {}
        if '天気' in df.columns:
            weather_stats = df.groupby('天気')['釣果数'].agg(['count', 'sum', 'mean']).round(1)
            by_weather = {
                weather: {
                    "days": int(stats['count']),
                    "total_catch": int(stats['sum']),
                    "avg_catch": float(stats['mean'])
                }
                for weather, stats in weather_stats.iterrows()
            }
        
        return {
            "total_records": len(df),
            "original_records": original_count,
            "total_catch": int(total_catch),
            "avg_catch": round(avg_catch, 1),
            "max_catch": int(max_catch),
            "min_catch": int(min_catch),
            "date_range": date_range,
            "by_month": by_month,
            "by_fish_type": by_fish_type,
            "by_weather": by_weather
        }
        
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        return {
            "total_records": len(df),
            "error": f"集計処理エラー: {str(e)}"
        }