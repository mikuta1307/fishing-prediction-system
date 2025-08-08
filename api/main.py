#!/usr/bin/env python3
"""
本牧海釣り施設 釣果予測システム - FastAPI メインサーバー
- 過去データ取得API
- 来場者数分析API  
- アジ釣果予測API（過去日付実績表示機能付き）
- システム状態確認API
"""

import os
import sys
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from ml.data_loader import load_all_data
    from ml.models import AjiPredictor
    from api.visitor_analysis import VisitorAnalyzer
    from api.historical import get_historical_data  # 既存関数を直接インポート
except ImportError as e:
    print(f"❌ モジュールインポートエラー: {e}")
    sys.exit(1)

# FastAPIアプリケーション初期化
app = FastAPI(
    title="本牧海釣り施設 釣果予測API",
    description="機械学習による釣果予測と来場者数分析",
    version="1.0.0"
)

# CORS設定（Next.jsフロントエンド対応）- Phase 13修正
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://fishing-prediction-system.vercel.app"  # 🔧 Phase 13追加
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数
visitor_analyzer = None
aji_predictor = None

# Pydanticモデル定義
class PredictionRequest(BaseModel):
    date: str  # YYYY/MM/DD or YYYY-MM-DD
    weather: str  # 晴れ, 曇り, 雨, 雪
    visitors: int  # 来場者数
    water_temp: float  # 水温
    tide: str  # 大潮, 中潮, 小潮, 長潮, 若潮

class PredictionResponse(BaseModel):
    success: bool
    prediction: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化"""
    global visitor_analyzer, aji_predictor
    
    print("🚀 FastAPI サーバー起動中...")
    
    # 🔍 DEBUG: ファイル構成確認を追加
    print("📁 現在の作業ディレクトリ:", os.getcwd())
    print("📁 ルートディレクトリの内容:")
    for item in os.listdir("."):
        print(f"  - {item}")
    
    print("📁 modelsディレクトリの確認:")
    if os.path.exists("models"):
        print("  ✅ modelsディレクトリ存在")
        print("  📋 modelsディレクトリの内容:")
        for item in os.listdir("models"):
            print(f"    - {item}")
    else:
        print("  ❌ modelsディレクトリが存在しません")
    
    # 🔧 Phase 13修正: Renderでのモデルパス修正
    print("🔍 glob検索結果:")
    # Renderでは 'cd api' で実行されるため、親ディレクトリを参照
    model_files = glob.glob("../models/aji_random_forest_*.pkl")
    if not model_files:
        # ローカル環境用のパスも試行
        model_files = glob.glob("models/aji_random_forest_*.pkl")
        print("  📁 ローカルパスでファイル発見")
    else:
        print("  📁 ../models/ パスでファイル発見")
    
    print(f"  検索結果: {model_files}")
    
    try:
        # 来場者数分析器初期化
        print("👥 来場者数分析器初期化中...")
        visitor_analyzer = VisitorAnalyzer()
        print("✅ 来場者数分析器初期化完了")
        
        # アジ予測モデル初期化
        print("🎣 アジ予測モデル初期化中...")
        aji_predictor = AjiPredictor()
        
        # 最新モデルファイルを自動読み込み
        if model_files:
            # 最新のファイルを取得（ファイル名の日時部分でソート）
            latest_model = sorted(model_files, reverse=True)[0]
            print(f"📁 最新モデル読み込み試行: {latest_model}")
            
            if aji_predictor.load_model(latest_model):
                print(f"✅ アジ予測モデル読み込み完了: {os.path.basename(latest_model)}")
            else:
                print(f"⚠️ モデル読み込み失敗: {latest_model}")
                aji_predictor = None
        else:
            print("⚠️ 学習済みモデルが見つかりません")
            aji_predictor = None
            
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        import traceback
        traceback.print_exc()

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "本牧海釣り施設 釣果予測API",
        "version": "1.0.0",
        "endpoints": {
            "historical": "/api/historical",
            "visitor_averages": "/api/visitor-averages", 
            "predict_aji": "/api/predict-aji",
            "status": "/api/status",
            "docs": "/docs"
        }
    }

@app.get("/api/status")
async def get_api_status():
    """システム状態確認"""
    try:
        model_status = "loaded" if aji_predictor and aji_predictor.is_trained else "not_loaded"
        model_info = None
        
        if aji_predictor and aji_predictor.is_trained:
            model_info = {
                "type": aji_predictor.model_type,
                "features": len(aji_predictor.feature_columns) if aji_predictor.feature_columns else 0,
                "trained_at": aji_predictor.training_history.get('trained_at') if aji_predictor.training_history else None
            }
        
        return {
            "success": True,
            "status": {
                "api": "running",
                "model": model_status,
                "historical_data": "available",
                "visitor_analysis": "available" if visitor_analyzer else "unavailable"
            },
            "model_info": model_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/historical")
async def get_historical_data_endpoint(
    fish: Optional[str] = Query(None, description="魚種フィルター"),
    weather: Optional[str] = Query(None, description="天気フィルター"), 
    tide: Optional[str] = Query(None, description="潮フィルター"),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    limit: int = Query(50, description="取得件数制限")
):
    """過去データ取得API（既存関数を直接使用）"""
    try:
        # 既存のget_historical_data関数を直接呼び出し
        result = await get_historical_data(
            fish=fish or "all",
            weather=weather,
            tide=tide,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        print(f"❌ 過去データ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/visitor-averages")
async def get_visitor_averages():
    """来場者数分析データ取得"""
    try:
        if not visitor_analyzer:
            raise HTTPException(status_code=503, detail="来場者数分析器が初期化されていません")
        
        result = visitor_analyzer.calculate_visitor_averages()
        return result
        
    except Exception as e:
        print(f"❌ 来場者数分析エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_actual_aji_catch(target_date: str) -> Optional[int]:
    """指定日のアジ実績釣果を取得"""
    try:
        # 日付形式を統一 (YYYY/MM/DD)
        if '-' in target_date:
            target_date = target_date.replace('-', '/')
            
        print(f"🔍 実績釣果検索開始: {target_date}")
        
        # Google Sheetsから全データを読み込み
        data_result = load_all_data()
        
        # load_all_data()はタプル(fishing_df, comment_df)を返す
        if isinstance(data_result, tuple) and len(data_result) >= 1:
            df = data_result[0]  # 最初の要素が釣果データ
            print("📊 タプル形式のデータを検出")
        else:
            print("❌ 予期しないデータ形式")
            return None
        
        if df is None or df.empty:
            print("❌ データ読み込み失敗")
            return None
            
        print(f"📊 読み込みデータ数: {len(df)}行")
        
        # データの列名を確認
        print(f"📋 データ列名: {list(df.columns)}")
        
        # 日付列の確認（data_loader.pyでは'日付'列を使用）
        date_column = '日付' if '日付' in df.columns else 'date'
        fish_column = '魚種' if '魚種' in df.columns else 'fish'
        catch_column = '釣果数' if '釣果数' in df.columns else 'catch_count'
        
        print(f"📅 利用可能日付範囲: {df[date_column].min()} ～ {df[date_column].max()}")
        
        # アジデータをフィルタリング
        aji_data = df[df[fish_column] == 'アジ'].copy()
        if aji_data.empty:
            print("❌ アジデータが見つかりません")
            print("🔍 利用可能な魚種:")
            unique_fish = df[fish_column].unique()
            for fish in unique_fish[:10]:  # 最初の10種類を表示
                print(f"  - {fish}")
            return None
            
        print(f"🎣 アジデータ数: {len(aji_data)}行")
        
        # 指定日のデータを検索（複数の日付形式で試行）
        search_formats = [
            target_date,  # 2025/07/31
            target_date.replace('/', '-'),  # 2025-07-31
            f"{target_date}(木)" if target_date == "2025/07/31" else f"{target_date}({get_weekday_jp(target_date)})"  # 2025/07/31(木)
        ]
        
        target_data = None
        found_format = None
        
        for date_format in search_formats:
            print(f"🔍 検索中: {date_format}")
            temp_data = aji_data[aji_data[date_column] == date_format]
            if not temp_data.empty:
                target_data = temp_data
                found_format = date_format
                break
        
        if target_data is None or target_data.empty:
            print(f"❌ {target_date}のアジデータが見つかりません")
            print("📅 利用可能なアジデータ日付（最新10件）:")
            recent_dates = aji_data[date_column].drop_duplicates().sort_values(ascending=False).head(10)
            for date in recent_dates:
                print(f"  - {date}")
            return None
        
        # 実績釣果数を取得
        actual_catch = int(target_data[catch_column].iloc[0])
        print(f"✅ {found_format}のアジ実績: {actual_catch}匹")
        
        return actual_catch
        
    except Exception as e:
        print(f"❌ 実績釣果取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_weekday_jp(date_str: str) -> str:
    """日付文字列から日本語曜日を取得"""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y/%m/%d')
        weekdays = ['月', '火', '水', '木', '金', '土', '日']
        return weekdays[date_obj.weekday()]
    except:
        return '不明'

def calculate_accuracy_metrics(predicted: int, actual: int) -> Dict[str, Any]:
    """予測精度メトリクスを計算"""
    if actual == 0:
        # 実績が0の場合の特別処理
        error_percent = 100.0 if predicted > 0 else 0.0
        accuracy_grade = "poor" if predicted > 0 else "perfect"
    else:
        error_amount = abs(predicted - actual)
        error_percent = (error_amount / actual) * 100
        
        # 精度グレード判定
        if error_percent <= 15:
            accuracy_grade = "excellent"
        elif error_percent <= 25:
            accuracy_grade = "good"
        elif error_percent <= 40:
            accuracy_grade = "fair"
        else:
            accuracy_grade = "poor"
    
    return {
        "error_amount": abs(predicted - actual),
        "error_percent": round(error_percent, 1),
        "accuracy_grade": accuracy_grade,
        "direction_correct": (predicted > actual and predicted > 0) or 
                           (predicted < actual and actual > 0) or
                           (predicted == actual)
    }

def get_accuracy_grade_text(grade: str) -> str:
    """精度グレードの日本語テキスト"""
    grade_mapping = {
        "excellent": "優秀 (誤差15%以下)",
        "good": "良好 (誤差25%以下)", 
        "fair": "普通 (誤差40%以下)",
        "poor": "要改善 (誤差40%以上)",
        "perfect": "完璧"
    }
    return grade_mapping.get(grade, "不明")

@app.post("/api/predict-aji", response_model=PredictionResponse)
async def predict_aji_catch(request: PredictionRequest):
    """アジ釣果予測API（過去日付実績表示機能付き）"""
    try:
        print(f"🎣 アジ予測リクエスト受信: {request}")
        
        # モデル状態確認
        if not aji_predictor:
            raise HTTPException(
                status_code=503, 
                detail="予測モデルが初期化されていません。学習済みモデルを確認してください。"
            )
        
        if not aji_predictor.is_trained:
            raise HTTPException(
                status_code=503,
                detail="予測モデルが訓練されていません。最新のモデルファイルを確認してください。"
            )
        
        # 入力データの前処理
        prediction_data = prepare_prediction_data(request)
        print(f"📝 前処理後データ: {prediction_data}")
        
        # 予測実行
        catch_count = aji_predictor.predict_single(**prediction_data)
        predicted_catch = int(round(catch_count))
        print(f"🎯 予測結果: {predicted_catch}匹")
        
        # 過去日付の場合、実績データを取得
        actual_catch = None
        is_historical = False
        accuracy_metrics = None
        
        try:
            # 今日の日付と比較
            today = datetime.now()
            request_date = datetime.strptime(request.date.replace('-', '/'), '%Y/%m/%d')
            
            if request_date.date() < today.date():
                print(f"📅 過去日付検出: {request.date}")
                is_historical = True
                actual_catch = await get_actual_aji_catch(request.date)
                
                if actual_catch is not None:
                    accuracy_metrics = calculate_accuracy_metrics(predicted_catch, actual_catch)
                    print(f"📊 精度メトリクス: {accuracy_metrics}")
                
        except Exception as e:
            print(f"⚠️ 実績データ取得でエラー（予測は継続）: {e}")
        
        # レスポンス作成
        response_data = {
            "success": True,
            "prediction": {
                "catch_count": predicted_catch,
                "actual_catch": actual_catch,  # 新機能
                "is_historical": is_historical,  # 新機能
                "accuracy_metrics": accuracy_metrics,  # 新機能
                "confidence": get_prediction_confidence(prediction_data, catch_count),
                "input_conditions": {
                    "date": request.date,
                    "weather": request.weather,
                    "visitors": request.visitors,
                    "water_temp": request.water_temp,
                    "tide": request.tide
                },
                "model_info": {
                    "type": aji_predictor.model_type,
                    "features": aji_predictor.feature_columns
                },
                "recommendations": generate_recommendations(prediction_data, catch_count),
                "predicted_at": datetime.now().isoformat()
            }
        }
        
        print(f"✅ 予測レスポンス: {response_data}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 予測エラー: {e}")
        import traceback
        traceback.print_exc()
        
        return PredictionResponse(
            success=False,
            error=f"予測処理中にエラーが発生しました: {str(e)}"
        )

def prepare_prediction_data(request: PredictionRequest) -> Dict[str, Any]:
    """予測データの前処理"""
    
    # 日付処理
    date_str = request.date.replace('-', '/')  # YYYY-MM-DD → YYYY/MM/DD
    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
    month = date_obj.month
    
    # 季節エンコード
    if month in [3, 4, 5]:
        season = 0  # 春
    elif month in [6, 7, 8]:
        season = 1  # 夏
    elif month in [9, 10, 11]:
        season = 2  # 秋
    else:
        season = 3  # 冬
    
    # 天気エンコード
    weather_mapping = {
        '晴れ': 0, '晴': 0,
        '曇り': 1, '曇': 1,
        '雨': 2,
        '雪': 3
    }
    weather_encoded = weather_mapping.get(request.weather, 0)
    
    # 潮エンコード
    tide_mapping = {
        '大潮': 0,
        '中潮': 1,
        '小潮': 2,
        '長潮': 3,
        '若潮': 4
    }
    tide_encoded = tide_mapping.get(request.tide, 0)
    
    return {
        'month': month,
        'season': season,
        'weather': weather_encoded,
        'temp': float(request.water_temp),
        'tide': tide_encoded,
        'visitors': int(request.visitors)
    }

def get_prediction_confidence(prediction_data: Dict[str, Any], catch_count: float) -> str:
    """予測信頼度の算出"""
    
    # 基本信頼度（Medium）
    confidence = "Medium"
    
    # 条件による信頼度調整
    factors = []
    
    # 季節要因（春夏は信頼度高）
    if prediction_data['season'] in [0, 1]:  # 春・夏
        factors.append(1)
    else:
        factors.append(-1)
    
    # 天気要因（晴れ・曇りは信頼度高）
    if prediction_data['weather'] in [0, 1]:  # 晴れ・曇り
        factors.append(1)
    else:
        factors.append(-1)
    
    # 水温要因（15-25℃は信頼度高）
    if 15 <= prediction_data['temp'] <= 25:
        factors.append(1)
    else:
        factors.append(-1)
    
    # 来場者数要因（100-500人は信頼度高）
    if 100 <= prediction_data['visitors'] <= 500:
        factors.append(1)
    else:
        factors.append(-1)
    
    # 予測値要因（50-500匹は信頼度高）
    if 50 <= catch_count <= 500:
        factors.append(1)
    else:
        factors.append(-1)
    
    # 総合判定
    total_score = sum(factors)
    if total_score >= 3:
        confidence = "High"
    elif total_score <= -2:
        confidence = "Low"
    
    return confidence

def generate_recommendations(prediction_data: Dict[str, Any], catch_count: float) -> List[str]:
    """釣行アドバイス生成"""
    recommendations = []
    
    # 水温アドバイス
    temp = prediction_data['temp']
    if temp < 15:
        recommendations.append("水温が低いです。朝夕の時間帯が狙い目です。")
    elif temp > 25:
        recommendations.append("水温が高いです。朝夕の時間帯がお勧めです。")
    else:
        recommendations.append("水温が適温です。アジの活性が期待できます。")
    
    # 潮アドバイス
    tide = prediction_data['tide']
    if tide == 2:  # 小潮
        recommendations.append("小潮で潮の動きが少ない日です。静かなポイントを狙いましょう。")
    elif tide == 0:  # 大潮
        recommendations.append("大潮で潮の動きが活発です。潮目を意識した釣りを心がけましょう。")
    
    # 来場者数アドバイス
    visitors = prediction_data['visitors']
    if visitors > 400:
        recommendations.append("混雑が予想されます。早めの到着をお勧めします。")
    elif visitors < 100:
        recommendations.append("比較的空いている日です。ゆっくり釣りを楽しめそうです。")
    
    # 予測釣果に応じたアドバイス
    if catch_count > 300:
        recommendations.append("好釣果が期待できます。十分な仕掛けの準備をお勧めします。")
    elif catch_count < 100:
        recommendations.append("厳しい条件です。丁寧な釣りを心がけましょう。")
    
    return recommendations

if __name__ == "__main__":
    print("🚀 本牧海釣り施設 釣果予測API サーバー起動")
    print("📡 アクセス: http://localhost:8000")
    print("📚 API仕様: http://localhost:8000/docs")
    print("🎣 アジ予測: POST /api/predict-aji")
    print("👥 来場者分析: GET /api/visitor-averages")
    print("📊 過去データ: GET /api/historical")
    print("ℹ️  システム状態: GET /api/status")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "ml"]
    )