#!/usr/bin/env python3
"""
本牧海釣り施設 釣果予測システム - 統合学習パイプライン
スクレイピング → データ読み込み → 特徴量エンジニアリング → モデル訓練の完全自動化

使用方法:
    python scripts/train.py                    # 実行時にモデル選択（推奨）
    python scripts/train.py --model rf         # Random Forest指定
    python scripts/train.py --model xgb        # XGBoost指定
    python scripts/train.py --no-scraping      # スクレイピングをスキップ
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 既存モジュールのインポート
try:
    from ml.data_loader import load_all_data
    from ml.feature_engineering import AjiFishingFeatureEngineer
    from ml.models import AjiPredictor, select_model_type
    from api.scraping_core import run_scraping
except ImportError as e:
    print(f"❌ エラー: 必要なモジュールをインポートできません: {e}")
    print("プロジェクトルートから実行してください: python scripts/train.py")
    sys.exit(1)

class TrainingPipeline:
    """統合学習パイプラインクラス"""
    
    def __init__(self, target_fish='aji', model_type='auto', enable_scraping=True):
        self.target_fish = target_fish
        self.model_type = model_type
        self.enable_scraping = enable_scraping
        
        print("🎣 本牧海釣り施設 釣果予測システム - 統合学習パイプライン")
        print("=" * 60)
        print(f"📅 実行時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"🐟 対象魚種: {self.target_fish}")
        print(f"🤖 モデル種別: {self.model_type if self.model_type != 'auto' else '実行時選択'}")
        print(f"🌐 スクレイピング: {'有効' if self.enable_scraping else '無効'}")
        print("=" * 60)
    
    def step1_scraping(self):
        """Step 1: Webスクレイピング実行"""
        if not self.enable_scraping:
            print("⏭️  Step 1: Webスクレイピングをスキップします")
            return True
            
        print("🌐 Step 1: Webスクレイピングを実行中...")
        try:
            current_year_month = datetime.now().strftime('%Y%m')
            result = run_scraping(current_year_month, headless=True, upload_to_sheets=True)
            
            if result['success']:
                print("✅ Step 1完了: 最新データの取得が成功しました")
                if 'sheets_result' in result and result['sheets_result'].get('success'):
                    sheets_info = result['sheets_result']
                    fishing_count = sheets_info.get('fishing_count', 0)
                    comment_count = sheets_info.get('comment_count', 0)
                    if fishing_count + comment_count > 0:
                        print(f"   🆕 新規追加: 釣果{fishing_count}行, コメント{comment_count}行")
                    else:
                        print("   📊 新規データなし（既存データは最新状態）")
            else:
                print(f"⚠️  Step 1警告: スクレイピングエラーが発生しましたが続行します")
            return True
                
        except Exception as e:
            print(f"⚠️  Step 1警告: スクレイピング実行中にエラー: {e}")
            print("   既存データで学習を続行します")
            return True
    
    def step2_data_loading(self):
        """Step 2: データ読み込み"""
        print("📊 Step 2: Google Sheetsからデータを読み込み中...")
        try:
            self.fishing_data, self.comment_data = load_all_data()
            
            if self.fishing_data is None:
                print("❌ Step 2エラー: 釣果データの読み込みに失敗")
                return False
            
            print(f"✅ Step 2完了: データ読み込み成功")
            print(f"   📈 釣果データ: {len(self.fishing_data):,}行")
            if self.comment_data is not None:
                print(f"   💬 コメントデータ: {len(self.comment_data):,}行")
            
            # データ期間表示
            if not self.fishing_data.empty and '日付' in self.fishing_data.columns:
                start_date = self.fishing_data['日付'].min()
                end_date = self.fishing_data['日付'].max()
                print(f"   📅 データ期間: {start_date} ～ {end_date}")
            
            return True
            
        except Exception as e:
            print(f"❌ Step 2エラー: データ読み込みに失敗: {e}")
            return False
    
    def step3_feature_engineering(self):
        """Step 3: 特徴量エンジニアリング"""
        print(f"🔧 Step 3: {self.target_fish}特化特徴量エンジニアリングを実行中...")
        try:
            if self.target_fish == 'aji':
                self.feature_eng = AjiFishingFeatureEngineer()
                self.X, self.y = self.feature_eng.create_features(self.fishing_data)
                
                if self.X is None or self.y is None:
                    print("❌ Step 3エラー: 特徴量作成に失敗")
                    return False
                
                print(f"✅ Step 3完了: アジ特化特徴量作成成功")
                print(f"   📊 学習データ: X{self.X.shape}, y{self.y.shape}")
                print(f"   🎯 アジ総釣果: {self.y.sum():,.0f}匹")
                print(f"   📈 平均釣果: {self.y.mean():.1f}匹/日")
                print(f"   🏷️  特徴量: {', '.join(self.feature_eng.feature_columns)}")
                
            else:
                print(f"❌ Step 3エラー: {self.target_fish}は現在サポートされていません")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Step 3エラー: 特徴量エンジニアリングに失敗: {e}")
            return False
    
    def step4_model_training(self):
        """Step 4: モデル訓練・評価"""
        print("🤖 Step 4: モデル訓練を実行中...")
        try:
            # モデル選択
            if self.model_type == 'auto':
                selected_type = select_model_type()
            elif self.model_type == 'rf':
                selected_type = 'random_forest'
            elif self.model_type == 'xgb':
                selected_type = 'xgboost'
            else:
                print(f"❌ Step 4エラー: サポートされていないモデル: {self.model_type}")
                return False
            
            # モデル訓練
            self.predictor = AjiPredictor(model_type=selected_type)
            training_results = self.predictor.fit(self.X, self.y)
            
            if training_results is None:
                return False
            
            print(f"✅ Step 4完了: モデル訓練成功")
            return True
            
        except Exception as e:
            print(f"❌ Step 4エラー: モデル訓練中にエラー: {e}")
            return False
    
    def step5_model_saving(self):
        """Step 5: 学習済みモデル保存（自動クリーンアップ付き）"""
        print("💾 Step 5: 学習済みモデルを保存中...")
        try:
            model_path = self.predictor.save_model()
            if model_path:
                print(f"✅ Step 5完了: モデル保存成功")
                print(f"   📁 保存先: {model_path}")
                return True
            else:
                print("❌ Step 5エラー: モデル保存に失敗")
                return False
                
        except Exception as e:
            print(f"❌ Step 5エラー: モデル保存中にエラー: {e}")
            return False
    
    def step6_sample_prediction(self):
        """Step 6: サンプル予測実行"""
        print("🎯 Step 6: サンプル予測を実行中...")
        try:
            # 8月の予測条件（夏・晴れ・27℃・大潮・200人）
            prediction = self.predictor.predict_single(
                month=8, season=1, weather=0, temp=27.0, tide=0, visitors=200
            )
            
            print(f"✅ Step 6完了: サンプル予測実行成功")
            print("   📅 予測条件: 8月（夏・晴れ）、水温27℃、大潮、来場者200人")
            print(f"   🎯 {self.predictor.model_type.replace('_', ' ').title()}予測アジ釣果: {prediction:.0f}匹")
            
            return True
            
        except Exception as e:
            print(f"❌ Step 6エラー: サンプル予測中にエラー: {e}")
            return False
    
    def step7_model_management(self):
        """Step 7: モデル管理状況確認"""
        print("🧹 Step 7: モデル管理状況を確認中...")
        try:
            # 現在のモデル一覧表示
            model_info = self.predictor.list_models()
            
            print(f"✅ Step 7完了: モデル管理状況確認")
            print(f"   📊 総モデル数: {len(model_info)}個")
            
            # モデル種別別の統計
            rf_count = len([m for m in model_info if 'Random Forest' in m['model_type']])
            xgb_count = len([m for m in model_info if 'XGBoost' in m['model_type']])
            
            print(f"   🌲 Random Forest: {rf_count}個")
            print(f"   🚀 XGBoost: {xgb_count}個")
            
            # 最新モデル情報
            if model_info:
                latest = model_info[0]
                print(f"   🆕 最新モデル: {latest['filename']}")
                print(f"   📅 更新日時: {latest['modified'].strftime('%Y/%m/%d %H:%M:%S')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Step 7エラー: モデル管理状況確認中にエラー: {e}")
            return True  # 非致命的エラーなので続行
    
    def run_pipeline(self):
        """統合パイプラインの実行"""
        start_time = datetime.now()
        
        steps = [
            ("Webスクレイピング", self.step1_scraping),
            ("データ読み込み", self.step2_data_loading),
            ("特徴量エンジニアリング", self.step3_feature_engineering),
            ("モデル訓練・評価", self.step4_model_training),
            ("モデル保存", self.step5_model_saving),
            ("サンプル予測", self.step6_sample_prediction),
            ("モデル管理状況確認", self.step7_model_management)
        ]
        
        success_count = 0
        for i, (step_name, step_func) in enumerate(steps, 1):
            print(f"\n{'='*60}")
            print(f"Step {i}/7: {step_name}")
            print('='*60)
            
            if step_func():
                success_count += 1
            else:
                # Step 7（モデル管理状況確認）は非致命的
                if i == 7:
                    success_count += 1
                    continue
                print(f"\n❌ パイプライン中断: Step {i}で致命的エラーが発生しました")
                break
        
        # 実行結果サマリー
        elapsed_time = datetime.now() - start_time
        print(f"\n{'='*60}")
        print("🎯 統合学習パイプライン実行結果")
        print('='*60)
        print(f"📅 実行時刻: {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"⏱️  実行時間: {elapsed_time.total_seconds():.1f}秒")
        print(f"✅ 成功ステップ: {success_count}/7")
        
        if success_count >= 6:  # Step 7は非致命的なので6以上で成功
            print("🎉 パイプライン完了: アジ釣果予測システムの学習が成功しました！")
            print("\n📋 次のアクション:")
            print("   • 予測機能の実装 (ml/prediction.py)")
            print("   • 詳細評価の実装 (ml/evaluation.py)")
            print("   • Web UI開発への準備")
            print("\n🧹 モデル管理:")
            print("   • 古いモデルファイルは自動削除されます（最新2つ保持）")
            print("   • 定期的なモデル再訓練を推奨します")
            return True
        else:
            print("⚠️  一部ステップで問題が発生しました。ログを確認してください。")
            return False

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='本牧海釣り施設 釣果予測システム - 統合学習パイプライン',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--model', '-m',
        choices=['rf', 'xgb', 'auto'],
        default='auto',
        help='使用するモデル (rf: Random Forest, xgb: XGBoost, auto: 実行時選択 [デフォルト])'
    )
    
    parser.add_argument(
        '--target-fish', '-f',
        choices=['aji'],
        default='aji',
        help='対象魚種 (現在はajiのみサポート)'
    )
    
    parser.add_argument(
        '--no-scraping',
        action='store_true',
        help='Webスクレイピングをスキップ（既存データで学習）'
    )
    
    args = parser.parse_args()
    
    # パイプライン実行
    pipeline = TrainingPipeline(
        target_fish=args.target_fish,
        model_type=args.model,
        enable_scraping=not args.no_scraping
    )
    
    success = pipeline.run_pipeline()
    
    # 終了コード
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()