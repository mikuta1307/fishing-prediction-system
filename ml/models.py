#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アジ釣果予測モデル

本牧海釣り施設のアジ釣果を予測する機械学習モデル
- Random Forest回帰モデル
- XGBoost回帰モデル
- モデル訓練・予測・評価・保存機能
- 自動モデル管理機能（最新2つ保持）
"""

import os
import glob
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

import xgboost as xgb

class AjiPredictor:
    """アジ釣果予測クラス"""
    
    def __init__(self, model_type='xgboost'):
        """
        初期化
        
        Args:
            model_type (str): モデルタイプ ('random_forest' or 'xgboost')
        """
        self.model_type = model_type
        self.model = None
        self.feature_columns = None
        self.is_trained = False
        
        # モデル保存用ディレクトリ
        self.model_dir = "models"
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
            print(f"📁 モデル保存ディレクトリ作成: {self.model_dir}")
        
        # 訓練履歴
        self.training_history = {}
        
        # モデル初期化
        self._initialize_model()
    
    def _initialize_model(self):
        """モデルの初期化"""
        if self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            print(f"🌲 Random Forestモデル初期化完了")
            
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            print(f"🚀 XGBoostモデル初期化完了")
            
        else:
            raise ValueError(f"サポートされていないモデル: {self.model_type}")
    
    def fit(self, X, y, validation_split=0.2):
        """
        モデルの訓練
        
        Args:
            X (pd.DataFrame): 特徴量
            y (pd.Series): ターゲット変数
            validation_split (float): 検証用データの割合
        
        Returns:
            dict: 訓練結果
        """
        print(f"🎯 {self.model_type}モデル訓練開始")
        print("=" * 50)
        
        # 入力データの確認
        print(f"📊 訓練データ: X{X.shape}, y{y.shape}")
        print(f"📈 釣果数統計: 平均{y.mean():.1f}, 範囲{y.min()}-{y.max()}")
        
        # 特徴量名を保存
        self.feature_columns = X.columns.tolist()
        
        # 時系列分割（過去→未来の順序を保持）
        train_size = int(len(X) * (1 - validation_split))
        X_train = X.iloc[:train_size]
        X_val = X.iloc[train_size:]
        y_train = y.iloc[:train_size]
        y_val = y.iloc[train_size:]
        
        print(f"📅 時系列分割: 訓練{len(X_train)}行, 検証{len(X_val)}行")
        
        # モデル訓練
        print(f"🔧 {self.model_type}モデル訓練中...")
        start_time = datetime.now()
        
        self.model.fit(X_train, y_train)
        
        training_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ 訓練完了（{training_time:.2f}秒）")
        
        # 予測実行
        y_train_pred = self.model.predict(X_train)
        y_val_pred = self.model.predict(X_val)
        
        # 評価指標計算
        train_metrics = self._calculate_metrics(y_train, y_train_pred, "訓練")
        val_metrics = self._calculate_metrics(y_val, y_val_pred, "検証")
        
        # 訓練履歴保存
        self.training_history = {
            'model_type': self.model_type,
            'training_time': training_time,
            'train_size': len(X_train),
            'val_size': len(X_val),
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'feature_columns': self.feature_columns,
            'trained_at': datetime.now().isoformat()
        }
        
        self.is_trained = True
        
        # 結果表示
        self._print_training_results()
        
        # 特徴量重要度表示
        self._print_feature_importance()
        
        return self.training_history
    
    def _calculate_metrics(self, y_true, y_pred, dataset_name):
        """評価指標の計算"""
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mean_actual': float(y_true.mean()),
            'mean_predicted': float(y_pred.mean())
        }
        
        return metrics
    
    def _print_training_results(self):
        """訓練結果の表示"""
        print(f"\n📊 {self.model_type}モデル評価結果")
        print("=" * 50)
        
        train_metrics = self.training_history['train_metrics']
        val_metrics = self.training_history['val_metrics']
        
        print(f"🎯 訓練データ評価:")
        print(f"  MAE:  {train_metrics['mae']:.1f}匹")
        print(f"  RMSE: {train_metrics['rmse']:.1f}匹")
        print(f"  R²:   {train_metrics['r2']:.3f}")
        
        print(f"\n🔍 検証データ評価:")
        print(f"  MAE:  {val_metrics['mae']:.1f}匹")
        print(f"  RMSE: {val_metrics['rmse']:.1f}匹")
        print(f"  R²:   {val_metrics['r2']:.3f}")
        
        # 過学習チェック
        mae_diff = val_metrics['mae'] - train_metrics['mae']
        r2_diff = train_metrics['r2'] - val_metrics['r2']
        
        print(f"\n🔍 過学習チェック:")
        print(f"  MAE差分: {mae_diff:+.1f}匹 ({'⚠️過学習' if mae_diff > 50 else '✅良好'})")
        print(f"  R²差分:  {r2_diff:+.3f} ({'⚠️過学習' if r2_diff > 0.1 else '✅良好'})")
    
    def _print_feature_importance(self):
        """特徴量重要度の表示"""
        if not hasattr(self.model, 'feature_importances_'):
            return
        
        importance = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            '特徴量': self.feature_columns,
            '重要度': importance
        }).sort_values('重要度', ascending=False)
        
        print(f"\n🔍 特徴量重要度 (上位5位):")
        for i, (_, row) in enumerate(feature_importance.head(5).iterrows(), 1):
            print(f"  {i}. {row['特徴量']}: {row['重要度']:.3f}")
    
    def predict(self, X):
        """
        予測実行
        
        Args:
            X (pd.DataFrame or np.array): 特徴量
        
        Returns:
            np.array: 予測値
        """
        if not self.is_trained:
            raise ValueError("モデルが訓練されていません。先にfit()を実行してください")
        
        # DataFrameの場合は特徴量順序をチェック
        if isinstance(X, pd.DataFrame):
            if list(X.columns) != self.feature_columns:
                print("⚠️ 特徴量の順序を調整しています")
                X = X[self.feature_columns]
        
        predictions = self.model.predict(X)
        
        # 負の値を0にクリップ（釣果数は非負）
        predictions = np.maximum(predictions, 0)
        
        return predictions
    
    def predict_single(self, month, season, weather, temp, tide, visitors):
        """
        単一条件での予測（便利関数）- 削減版6特徴量対応
        
        Args:
            month (int): 月 (1-12)
            season (int): 季節エンコード (0=春, 1=夏, 2=秋, 3=冬)
            weather (int): 天気エンコード (0=晴れ, 1=曇り, 2=雨, 3=雪)
            temp (float): 水温 (℃)
            tide (int): 潮エンコード (0=大潮, 1=中潮, 2=小潮, 3=長潮, 4=若潮)
            visitors (int): 来場者数 (人)
        
        Returns:
            float: 予測アジ釣果数
        """
        # 特徴量ベクトル作成（6個の特徴量）
        features = np.array([[month, season, weather, temp, tide, visitors]])
        
        # 予測実行
        prediction = self.predict(features)[0]
        
        return prediction
    
    def cross_validate(self, X, y, cv_folds=5):
        """
        交差検証の実行
        
        Args:
            X (pd.DataFrame): 特徴量
            y (pd.Series): ターゲット変数
            cv_folds (int): 交差検証の分割数
        
        Returns:
            dict: 交差検証結果
        """
        print(f"🔄 {cv_folds}-fold交差検証実行中...")
        
        # 時系列交差検証
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        
        # MAEスコア
        mae_scores = -cross_val_score(
            self.model, X, y, 
            cv=tscv, 
            scoring='neg_mean_absolute_error',
            n_jobs=-1
        )
        
        # R²スコア
        r2_scores = cross_val_score(
            self.model, X, y,
            cv=tscv,
            scoring='r2',
            n_jobs=-1
        )
        
        cv_results = {
            'mae_mean': mae_scores.mean(),
            'mae_std': mae_scores.std(),
            'r2_mean': r2_scores.mean(),
            'r2_std': r2_scores.std(),
            'mae_scores': mae_scores.tolist(),
            'r2_scores': r2_scores.tolist()
        }
        
        print(f"✅ 交差検証完了:")
        print(f"  MAE: {cv_results['mae_mean']:.1f} ± {cv_results['mae_std']:.1f}匹")
        print(f"  R²:  {cv_results['r2_mean']:.3f} ± {cv_results['r2_std']:.3f}")
        
        return cv_results
    
    def cleanup_old_models(self, keep_count=2):
        """
        古いモデルファイルを削除し、最新のkeep_count個のみ保持
        
        Args:
            keep_count (int): 保持するモデル数（デフォルト: 2）
        
        Returns:
            dict: 削除・保持結果
        """
        # モデル種別別のファイルパターン
        pattern = os.path.join(self.model_dir, f"aji_{self.model_type}_*.pkl")
        model_files = glob.glob(pattern)
        
        if len(model_files) <= keep_count:
            return {
                'deleted_files': [],
                'kept_files': model_files,
                'message': f"保持対象{keep_count}個以下のため削除不要"
            }
        
        # ファイル名から日時を抽出してソート（新しい順）
        def extract_datetime(filepath):
            filename = os.path.basename(filepath)
            # aji_random_forest_20250730_163124.pkl → 20250730_163124
            try:
                datetime_part = filename.split('_')[-2] + '_' + filename.split('_')[-1].replace('.pkl', '')
                return datetime.strptime(datetime_part, '%Y%m%d_%H%M%S')
            except:
                # 日時抽出失敗時はファイル作成時刻を使用
                return datetime.fromtimestamp(os.path.getctime(filepath))
        
        # 日時順ソート（新しい順）
        model_files.sort(key=extract_datetime, reverse=True)
        
        # 保持・削除ファイルを決定
        files_to_keep = model_files[:keep_count]
        files_to_delete = model_files[keep_count:]
        
        deleted_files = []
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_files.append(os.path.basename(file_path))
                print(f"🗑️  削除: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️  削除失敗: {os.path.basename(file_path)} - {e}")
        
        return {
            'deleted_files': deleted_files,
            'kept_files': [os.path.basename(f) for f in files_to_keep],
            'message': f"{len(deleted_files)}個のファイルを削除、{len(files_to_keep)}個を保持"
        }
    
    def save_model(self, filename=None):
        """
        モデルの保存（自動クリーンアップ付き）
        
        Args:
            filename (str): 保存ファイル名（省略時は自動生成）
        
        Returns:
            str: 保存ファイルパス
        """
        if not self.is_trained:
            raise ValueError("訓練されていないモデルは保存できません")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"aji_{self.model_type}_{timestamp}.pkl"
        
        filepath = os.path.join(self.model_dir, filename)
        
        # モデルとメタデータを保存
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'feature_columns': self.feature_columns,
            'training_history': self.training_history,
            'is_trained': self.is_trained
        }
        
        joblib.dump(model_data, filepath)
        print(f"💾 モデル保存完了: {filepath}")
        
        # 古いモデルファイルのクリーンアップ
        print("🧹 古いモデルファイルをクリーンアップ中...")
        cleanup_result = self.cleanup_old_models(keep_count=2)
        
        if cleanup_result['deleted_files']:
            print(f"✅ クリーンアップ完了: {cleanup_result['message']}")
            print(f"   📁 保持ファイル: {', '.join(cleanup_result['kept_files'])}")
        else:
            print(f"ℹ️  {cleanup_result['message']}")
        
        return filepath
    
    def list_models(self):
        """
        保存済みモデルファイルの一覧表示
        
        Returns:
            list: モデルファイル情報のリスト
        """
        pattern = os.path.join(self.model_dir, "aji_*.pkl")
        model_files = glob.glob(pattern)
        
        model_info = []
        for filepath in model_files:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            # モデル種別を推定
            if 'random_forest' in filename:
                model_type = 'Random Forest'
            elif 'xgboost' in filename:
                model_type = 'XGBoost'
            else:
                model_type = 'Unknown'
            
            model_info.append({
                'filename': filename,
                'model_type': model_type,
                'size_mb': file_size / 1024 / 1024,
                'modified': modified_time,
                'filepath': filepath
            })
        
        # 更新日時順ソート（新しい順）
        model_info.sort(key=lambda x: x['modified'], reverse=True)
        
        print(f"\n📁 保存済みモデル一覧 ({len(model_info)}個)")
        print("=" * 80)
        for i, info in enumerate(model_info, 1):
            print(f"{i:2d}. {info['filename']}")
            print(f"    📊 種別: {info['model_type']}")
            print(f"    📂 サイズ: {info['size_mb']:.1f}MB")
            print(f"    📅 更新: {info['modified'].strftime('%Y/%m/%d %H:%M:%S')}")
            print()
        
        return model_info
    
    def load_model(self, filepath):
        """
        モデルの読み込み
        
        Args:
            filepath (str): モデルファイルパス
        
        Returns:
            bool: 読み込み成功フラグ
        """
        try:
            if not os.path.exists(filepath):
                print(f"❌ モデルファイルが見つかりません: {filepath}")
                return False
            
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.model_type = model_data['model_type']
            self.feature_columns = model_data['feature_columns']
            self.training_history = model_data['training_history']
            self.is_trained = model_data['is_trained']
            
            print(f"✅ モデル読み込み完了: {filepath}")
            print(f"📊 モデル: {self.model_type}")
            print(f"🎯 特徴量数: {len(self.feature_columns)}")
            
            return True
            
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {e}")
            return False
    
    def get_model_info(self):
        """モデル情報の取得"""
        if not self.is_trained:
            return {"status": "未訓練"}
        
        return {
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "feature_columns": self.feature_columns,
            "training_history": self.training_history
        }


def create_sample_prediction():
    """サンプル予測の実行例（削減版6特徴量対応）"""
    print("🎯 サンプル予測実行")
    print("=" * 40)
    
    # サンプル条件（8月1日土曜日、夏、晴れ、水温27℃、大潮、来場者200人）
    sample_conditions = {
        'month': 8,          # 8月
        'season': 1,         # 夏
        'weather': 0,        # 晴れ
        'temp': 27.0,        # 水温27℃
        'tide': 0,           # 大潮
        'visitors': 200      # 来場者200人
    }
    
    print("📅 予測条件:")
    print(f"  日付: 8月（夏・晴れ）")
    print(f"  水温: {sample_conditions['temp']}℃")
    print(f"  潮: 大潮, 来場者: {sample_conditions['visitors']}人")
    
    return sample_conditions


def select_model_type():
    """モデルタイプ選択"""
    print("🤖 使用するモデルを選択してください:")
    print("  1. Random Forest（安定性重視・解釈しやすい）")
    print("  2. XGBoost（高精度・競技向け）")
    
    while True:
        try:
            choice = input("\n選択 (1 or 2): ").strip()
            if choice == "1":
                return "random_forest"
            elif choice == "2":
                return "xgboost"
            else:
                print("❌ 1 または 2 を入力してください")
        except KeyboardInterrupt:
            print("\n\n👋 処理を中断しました")
            exit(0)
        except Exception:
            print("❌ 無効な入力です。1 または 2 を入力してください")


def main():
    """テスト実行"""
    print("🐟 アジ釣果予測モデル学習")
    print("=" * 60)
    
    try:
        # モデル選択
        model_type = select_model_type()
        model_name = "Random Forest" if model_type == "random_forest" else "XGBoost"
        
        print(f"\n✅ {model_name}モデルを選択")
        print("=" * 60)
        
        # データ読み込み
        from data_loader import load_all_data
        from feature_engineering import AjiFishingFeatureEngineer
        
        print("📊 データ読み込み中...")
        fishing_df, comment_df = load_all_data()
        
        if fishing_df is None:
            print("❌ データ読み込み失敗")
            return
        
        # 特徴量エンジニアリング
        print("🔧 特徴量エンジニアリング実行中...")
        feature_eng = AjiFishingFeatureEngineer()
        X, y = feature_eng.create_features(fishing_df)
        
        if X is None or y is None:
            print("❌ 特徴量作成失敗")
            return
        
        # 選択されたモデルで学習
        print(f"\n{'🌲' if model_type == 'random_forest' else '🚀'} {model_name}モデル学習開始")
        print("=" * 50)
        
        predictor = AjiPredictor(model_type=model_type)
        results = predictor.fit(X, y)
        
        # 交差検証
        print(f"\n🔄 {model_name}モデル交差検証中...")
        cv_results = predictor.cross_validate(X, y, cv_folds=3)
        
        # モデル保存（自動クリーンアップ付き）
        print(f"\n💾 {model_name}モデル保存中...")
        model_path = predictor.save_model()
        
        # 保存済みモデル一覧表示
        predictor.list_models()
        
        # サンプル予測
        sample_conditions = create_sample_prediction()
        prediction = predictor.predict_single(**sample_conditions)
        print(f"🎯 {model_name}予測アジ釣果: {prediction:.0f}匹")
        
        print(f"\n✅ {model_name}モデル学習完了!")
        print(f"💾 保存場所: {model_path}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()