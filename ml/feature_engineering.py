"""
アジ釣果予測のための特徴量エンジニアリング（特徴量削減版）

本牧海釣り施設のデータを機械学習用に前処理
- アジに特化した特徴量作成
- カテゴリエンコーディング
- 時間特徴量生成
- 過学習防止のため6つの重要特徴量に削減
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class AjiFishingFeatureEngineer:
    """アジ釣果予測用特徴量エンジニアリング"""
    
    def __init__(self):
        """初期化"""
        self.target_species = 'アジ'
        self.categorical_encoders = {}
        self.feature_columns = []
        
    def analyze_aji_data(self, fishing_df):
        """アジデータの分析・統計情報出力"""
        print(f"🐟 {self.target_species}データ分析")
        print("=" * 50)
        
        # アジデータの抽出
        aji_data = fishing_df[fishing_df['魚種'] == self.target_species].copy()
        
        if len(aji_data) == 0:
            print(f"❌ {self.target_species}のデータが見つかりません")
            return None
        
        # 日付データの確認
        print(f"🔍 日付データサンプル:")
        print(aji_data['日付'].head(5).tolist())
        
        # 日付から曜日部分を除去してdatetime型に変換
        def clean_date(date_str):
            if isinstance(date_str, str):
                # '2025/01/31(金)' → '2025/01/31'
                return date_str.split('(')[0]
            return date_str
        
        aji_data['日付_クリーン'] = aji_data['日付'].apply(clean_date)
        aji_data['日付'] = pd.to_datetime(aji_data['日付_クリーン'], errors='coerce')
        
        # NaTの確認
        nat_count = aji_data['日付'].isna().sum()
        if nat_count > 0:
            print(f"⚠️ 変換できない日付: {nat_count}行")
        
        # 有効な日付のみで統計計算
        valid_dates = aji_data['日付'].dropna()
        if len(valid_dates) == 0:
            print("❌ 有効な日付データがありません")
            return None
            
        print(f"📊 {self.target_species}データ数: {len(aji_data)}行")
        print(f"📅 期間: {valid_dates.min().strftime('%Y/%m/%d(%a)')} ～ {valid_dates.max().strftime('%Y/%m/%d(%a)')}")
        print(f"🎣 総釣果数: {aji_data['釣果数'].sum():,}匹")
        print(f"📈 平均釣果数: {aji_data['釣果数'].mean():.1f}匹/日")
        print(f"📊 最大釣果数: {aji_data['釣果数'].max()}匹")
        print(f"📊 最小釣果数: {aji_data['釣果数'].min()}匹")
        
        # 釣り場別統計
        print(f"\n🏖️ 釣り場別{self.target_species}釣果:")
        place_stats = aji_data.groupby('釣り場')['釣果数'].agg(['count', 'sum', 'mean']).round(1)
        for place, stats in place_stats.iterrows():
            print(f"  {place}: {stats['count']}日, 総数{stats['sum']}匹, 平均{stats['mean']}匹")
        
        # 月別統計（有効な日付のみ）
        if len(valid_dates) > 0:
            print(f"\n📅 月別{self.target_species}釣果:")
            aji_data_valid = aji_data[aji_data['日付'].notna()].copy()
            aji_data_valid['月'] = aji_data_valid['日付'].dt.month
            month_stats = aji_data_valid.groupby('月')['釣果数'].agg(['count', 'sum', 'mean']).round(1)
            for month, stats in month_stats.iterrows():
                print(f"  {month}月: {stats['count']}日, 総数{stats['sum']}匹, 平均{stats['mean']}匹")
            
        return aji_data
    
    def create_time_features(self, df):
        """時間関連特徴量の作成"""
        df = df.copy()
        
        # 日付から曜日部分を除去してdatetime型に変換
        def clean_date(date_str):
            if isinstance(date_str, str):
                # '2025/01/31(金)' → '2025/01/31'
                return date_str.split('(')[0]
            return date_str
        
        df['日付_クリーン'] = df['日付'].apply(clean_date)
        df['日付'] = pd.to_datetime(df['日付_クリーン'], errors='coerce')
        
        # 基本時間特徴量
        df['年'] = df['日付'].dt.year
        df['月'] = df['日付'].dt.month
        df['日'] = df['日付'].dt.day
        df['曜日'] = df['日付'].dt.dayofweek  # 月曜=0, 日曜=6
        
        # 季節特徴量
        def get_season(month):
            if month in [3, 4, 5]:
                return '春'
            elif month in [6, 7, 8]:
                return '夏'
            elif month in [9, 10, 11]:
                return '秋'
            else:
                return '冬'
        
        df['季節'] = df['月'].apply(get_season)
        
        # 休日フラグ（土日を休日とする）
        df['休日フラグ'] = (df['曜日'] >= 5).astype(int)  # 土曜=5, 日曜=6
        
        return df
    
    def encode_categorical_features(self, df):
        """カテゴリ特徴量のエンコーディング"""
        df = df.copy()
        
        # 天気のエンコーディング
        weather_mapping = {
            '晴れ': 0, '晴': 0,
            '曇り': 1, '曇': 1,
            '雨': 2,
            '雪': 3
        }
        if '天気' in df.columns:
            df['天気_エンコード'] = df['天気'].map(weather_mapping)
            df['天気_エンコード'] = df['天気_エンコード'].fillna(1)  # 不明は曇りとする
        
        # 潮のエンコーディング（カラム名は'潮'）
        tide_mapping = {
            '大潮': 0,
            '中潮': 1,
            '小潮': 2,
            '長潮': 3,
            '若潮': 4
        }
        if '潮' in df.columns:
            df['潮_エンコード'] = df['潮'].map(tide_mapping)
            df['潮_エンコード'] = df['潮_エンコード'].fillna(1)  # 不明は中潮とする
        
        # 季節のエンコーディング
        season_mapping = {'春': 0, '夏': 1, '秋': 2, '冬': 3}
        df['季節_エンコード'] = df['季節'].map(season_mapping)
        
        # エンコーディング情報を保存
        self.categorical_encoders = {
            '天気': weather_mapping,
            '潮': tide_mapping,
            '季節': season_mapping
        }
        
        return df
    
    def create_environmental_features(self, df):
        """環境関連特徴量の作成"""
        df = df.copy()
        
        # 水温を数値型に変換してから階級化
        if '水温' in df.columns:
            # 文字列の場合は数値に変換
            df['水温'] = pd.to_numeric(df['水温'], errors='coerce')
            # 水温の階級化（5度刻み） - 削除対象なのでコメントアウト
            # df['水温_階級'] = (df['水温'] // 5) * 5
        
        return df
    
    def create_target_variable(self, df):
        """ターゲット変数（アジ釣果数）の作成"""
        # アジデータのみ抽出
        aji_df = df[df['魚種'] == self.target_species].copy()
        
        if len(aji_df) == 0:
            raise ValueError(f"{self.target_species}のデータが見つかりません")
        
        # データフレームのカラム名を確認
        print(f"🔍 利用可能なカラム名:")
        print(aji_df.columns.tolist())
        
        # 日付から曜日部分を除去してdatetime型に変換
        def clean_date(date_str):
            if isinstance(date_str, str):
                # '2025/01/31(金)' → '2025/01/31'
                return date_str.split('(')[0]
            return date_str
        
        aji_df['日付_クリーン'] = aji_df['日付'].apply(clean_date)
        aji_df['日付'] = pd.to_datetime(aji_df['日付_クリーン'], errors='coerce')
        
        # 存在するカラムのみでグループ化
        agg_dict = {'釣果数': 'sum'}
        
        # 存在するカラムを確認して追加（数値化されたカラムを優先使用）
        column_mapping = {
            '天気': '天気',
            '水温': '水温_数値' if '水温_数値' in aji_df.columns else '水温',
            '潮': '潮',
            '来場者数': '来場者数_数値' if '来場者数_数値' in aji_df.columns else '来場者数'
        }
        
        for original_col, actual_col in column_mapping.items():
            if actual_col in aji_df.columns:
                agg_dict[original_col] = 'first'
                print(f"✅ カラム '{actual_col}' を '{original_col}' として追加")
            else:
                print(f"⚠️ カラム '{actual_col}' は存在しません")
        
        # 日付でグループ化して、1日あたりの合計釣果数を計算
        # 数値化カラムを元のカラム名にリネーム
        for original_col, actual_col in column_mapping.items():
            if actual_col in aji_df.columns and actual_col != original_col:
                aji_df[original_col] = aji_df[actual_col]
        
        daily_aji = aji_df.groupby('日付').agg(agg_dict).reset_index()
        
        print(f"✅ 日別データ作成完了: {len(daily_aji)}行")
        print(f"📋 作成されたカラム: {daily_aji.columns.tolist()}")
        
        return daily_aji
    
    def create_features(self, fishing_df, target_only=False):
        """
        特徴量作成のメインパイプライン（削減版）
        
        Args:
            fishing_df: 釣果データフレーム
            target_only: Trueの場合、アジデータのみを対象とする
        
        Returns:
            X: 特徴量行列（6個の特徴量に削減）
            y: ターゲット変数（アジ釣果数）
        """
        print(f"🔧 {self.target_species}特徴量エンジニアリング開始（削減版）")
        print("=" * 50)
        
        # アジデータ分析
        aji_data = self.analyze_aji_data(fishing_df)
        if aji_data is None:
            return None, None
        
        # アジの日別集計データを作成
        print(f"\n📊 日別{self.target_species}データ集計中...")
        daily_aji = self.create_target_variable(fishing_df)
        print(f"✅ 日別データ作成完了: {len(daily_aji)}行")
        
        # 時間特徴量作成
        print(f"\n📅 時間特徴量作成中...")
        daily_aji = self.create_time_features(daily_aji)
        
        # カテゴリエンコーディング
        print(f"🏷️ カテゴリエンコーディング中...")
        daily_aji = self.encode_categorical_features(daily_aji)
        
        # 環境特徴量作成
        print(f"🌡️ 環境特徴量作成中...")
        daily_aji = self.create_environmental_features(daily_aji)
        
        # 特徴量列の定義（削減版 - 6個の重要特徴量）
        feature_columns = [
            # 時間特徴量（重要なもののみ）
            '月', '季節_エンコード',
            
            # 環境特徴量（釣りに重要なもの）
            '天気_エンコード', '水温', '潮_エンコード', '来場者数'
        ]
        
        # 特徴量行列とターゲット変数の作成
        X = daily_aji[feature_columns].copy()
        y = daily_aji['釣果数'].copy()
        
        self.feature_columns = feature_columns
        
        # 欠損値処理
        X = X.fillna(X.mean())
        
        print(f"\n✅ 特徴量エンジニアリング完了（削減版）")
        print(f"📊 特徴量数: {X.shape[1]} （10個→6個に削減）")
        print(f"📊 サンプル数: {X.shape[0]}")
        print(f"🎯 ターゲット: {self.target_species}釣果数")
        print(f"📈 平均釣果数: {y.mean():.1f}匹")
        print(f"📊 釣果数範囲: {y.min()}-{y.max()}匹")
        print(f"📊 サンプル/特徴量比: {X.shape[0]/X.shape[1]:.1f}:1 （大幅改善）")
        
        # 特徴量名表示
        print(f"\n🔍 使用特徴量（削減版）:")
        for i, col in enumerate(feature_columns, 1):
            print(f"  {i:2d}. {col}")
        
        # 削除した特徴量の説明
        print(f"\n❌ 削除した特徴量（過学習防止）:")
        removed_features = ['日', '曜日', '休日フラグ', '水温_階級']
        for i, col in enumerate(removed_features, 1):
            print(f"  {i:2d}. {col}")
        
        return X, y
    
    def get_feature_info(self):
        """特徴量情報の取得"""
        return {
            'target_species': self.target_species,
            'feature_columns': self.feature_columns,
            'categorical_encoders': self.categorical_encoders,
            'n_features': len(self.feature_columns)
        }


def main():
    """テスト実行"""
    print("🐟 アジ特化特徴量エンジニアリングテスト（削減版）")
    print("=" * 60)
    
    try:
        # データ読み込み
        from data_loader import load_all_data
        print("📊 データ読み込み中...")
        fishing_df, comment_df = load_all_data()
        
        # 特徴量エンジニアリング実行
        feature_eng = AjiFishingFeatureEngineer()
        X, y = feature_eng.create_features(fishing_df)
        
        if X is not None and y is not None:
            print(f"\n🎉 テスト成功!")
            print(f"特徴量行列: {X.shape}")
            print(f"ターゲット: {y.shape}")
            
            # サンプルデータ表示
            print(f"\n📋 サンプルデータ（最初の3行）:")
            print(X.head(3))
            print(f"\n🎯 対応するアジ釣果数:")
            print(y.head(3).values)
            
            # 特徴量情報表示
            info = feature_eng.get_feature_info()
            print(f"\n📋 特徴量情報:")
            print(f"対象魚種: {info['target_species']}")
            print(f"特徴量数: {info['n_features']}個（削減版）")
        else:
            print("❌ アジデータが見つかりませんでした")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()