import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  getVisitorAverages, 
  predictAjiCatch, 
  formatDateForAPI, 
  getWeekday, 
  getConfidenceText, 
  getErrorMessage,
  weatherJaToEn,
  getApiStatus
} from '../lib/api';

export default function PredictPage() {
  // 基本条件
  const [selectedDate, setSelectedDate] = useState(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}`;
  });
  const [selectedWeather, setSelectedWeather] = useState('晴れ');
  
  // 釣果予測用条件
  const [fishingConditions, setFishingConditions] = useState({
    waterTemp: 20.0,
    tide: '大潮'
  });
  
  // 来場者数関連
  const [visitorData, setVisitorData] = useState({});
  const [estimatedVisitors, setEstimatedVisitors] = useState(135);
  
  // 状態管理
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState(null);
  
  // システム状態
  const [apiStatus, setApiStatus] = useState(null);

  // 選択肢定義
  const weatherOptions = ['晴れ', '曇り', '雨', '雪'];
  const tideOptions = ['大潮', '中潮', '小潮', '長潮', '若潮'];

  // API状態確認
  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        const status = await getApiStatus();
        setApiStatus(status);
      } catch (err) {
        console.error('API状態確認エラー:', err);
      }
    };
    
    checkApiStatus();
  }, []);

  // 来場者数データ読み込み
  useEffect(() => {
    const fetchVisitorData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('📊 来場者数データ取得開始');
        const response = await getVisitorAverages();
        console.log('🔍 APIレスポンス:', response);
        
        if (response.status === 'success' || response.status === 'fallback') {
          // データ形式を統一（天気_曜日 → 来場者数平均）
          const dataByCondition = {};
          
          if (response.data && Array.isArray(response.data)) {
            // 新形式: dataプロパティにArray
            console.log('📋 データ配列を処理:', response.data);
            response.data.forEach(item => {
              console.log('🔍 処理中のアイテム:', item);
              const key = `${item.weather}_${item.weekday}`;
              dataByCondition[key] = item;
              console.log(`✅ 設定: ${key} = ${item.average}人`);
            });
          } else if (response.averages) {
            // 旧形式: averagesプロパティにObject
            console.log('📋 averagesオブジェクトを処理:', response.averages);
            Object.entries(response.averages).forEach(([key, value]) => {
              dataByCondition[key] = { average: value.average || value };
              console.log(`✅ 設定: ${key} = ${value.average || value}人`);
            });
          } else {
            console.error('❌ 予期しないデータ形式:', response);
            throw new Error('データ形式が不正です');
          }
          
          console.log('📊 最終的な来場者数データ:', dataByCondition);
          setVisitorData(dataByCondition);
        } else {
          throw new Error('来場者数データの取得に失敗しました');
        }
      } catch (err) {
        console.error('❌ 来場者数データ取得エラー:', err);
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchVisitorData();
  }, []);

  // 日付・天気変更時の来場者数更新
  useEffect(() => {
    console.log('🔄 useEffect実行 - データ変更検知');
    console.log('📊 visitorDataキー数:', Object.keys(visitorData).length);
    console.log('📅 selectedDate:', selectedDate);
    console.log('🌤️ selectedWeather:', selectedWeather);
    
    if (Object.keys(visitorData).length > 0) {
      console.log('✅ データが存在するため自動計算実行');
      updateEstimatedVisitors();
    } else {
      console.log('⚠️ visitorDataが空のため自動計算スキップ');
    }
  }, [selectedDate, selectedWeather, visitorData]);

  const updateEstimatedVisitors = () => {
    console.log('🔍 来場者数自動計算開始');
    console.log('📅 現在の日付:', selectedDate);
    console.log('🌤️ 現在の天気:', selectedWeather);
    
    // 天気を英語に変換
    const weatherMapping = {
      '晴れ': 'sunny',
      '曇り': 'cloudy', 
      '雨': 'rainy',
      '雪': 'snowy'
    };
    
    const weatherEn = weatherMapping[selectedWeather] || 'sunny';
    console.log('🌤️ 変換後天気:', weatherEn);
    
    // 曜日を英語に変換
    const weekdayJa = getWeekday(selectedDate);
    const weekdayMapping = {
      '日': 'sunday',
      '月': 'monday',
      '火': 'tuesday', 
      '水': 'wednesday',
      '木': 'thursday',
      '金': 'friday',
      '土': 'saturday'
    };
    
    const weekdayEn = weekdayMapping[weekdayJa] || 'monday';
    console.log('📅 曜日変換:', weekdayJa, '→', weekdayEn);
    
    // API形式のキーを作成
    const apiKey = `${weatherEn}_${weekdayEn}`;
    console.log('🔑 APIキー:', apiKey);
    console.log('📊 利用可能なキー:', Object.keys(visitorData));
    
    if (visitorData[apiKey]) {
      const newVisitors = Math.round(visitorData[apiKey].average);
      console.log('✅ APIキーで発見:', apiKey, '=', newVisitors);
      setEstimatedVisitors(newVisitors);
      return;
    }
    
    // 実際のAPIデータキー形式を確認して試行
    const availableKeys = Object.keys(visitorData);
    console.log('🔍 利用可能キーの詳細分析:');
    availableKeys.forEach(key => {
      console.log(`  - ${key}: ${visitorData[key].average}人`);
    });
    
    // 部分マッチを試行（天気が含まれるキー）
    const weatherMatchKeys = availableKeys.filter(key => key.includes(weatherEn));
    console.log('🌤️ 天気マッチキー:', weatherMatchKeys);
    
    if (weatherMatchKeys.length > 0) {
      // 曜日もマッチするキーを優先
      const exactMatch = weatherMatchKeys.find(key => key.includes(weekdayEn));
      const matchKey = exactMatch || weatherMatchKeys[0];
      const newVisitors = Math.round(visitorData[matchKey].average);
      console.log('✅ 部分マッチで発見:', matchKey, '=', newVisitors);
      setEstimatedVisitors(newVisitors);
      return;
    }
    
    // 最終フォールバック
    const weatherDefaults = {
      '晴れ': 400,  // 晴れの平均的な値
      '曇り': 350,  // 曇りの平均的な値
      '雨': 200,    // 雨の平均的な値
      '雪': 130     // 雪の推定値
    };
    const defaultVisitors = weatherDefaults[selectedWeather] || 300;
    console.log('🔄 フォールバック値使用:', defaultVisitors);
    setEstimatedVisitors(defaultVisitors);
  };

  // 釣果予測実行
  const handlePredictCatch = async () => {
    try {
      setPredictionLoading(true);
      setPredictionError(null);
      setPredictionResult(null);

      console.log('🎣 釣果予測開始');
      
      // API用データ準備
      const predictionData = {
        date: selectedDate,
        weather: selectedWeather,
        visitors: estimatedVisitors,
        water_temp: fishingConditions.waterTemp,
        tide: fishingConditions.tide
      };

      console.log('📝 予測条件:', predictionData);

      // 予測API呼び出し
      const response = await predictAjiCatch(predictionData);
      
      if (response.success) {
        setPredictionResult(response.prediction);
        console.log('✅ 予測成功:', response.prediction);
      } else {
        throw new Error(response.error || '予測に失敗しました');
      }
      
    } catch (err) {
      console.error('❌ 予測エラー:', err);
      setPredictionError(getErrorMessage(err));
    } finally {
      setPredictionLoading(false);
    }
  };

  // 信頼度に応じたスタイル
  const getConfidenceStyle = (confidence) => {
    switch (confidence) {
      case 'High':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'Low':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // 精度グレードに応じたスタイル
  const getAccuracyStyle = (grade) => {
    switch (grade) {
      case 'excellent':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'good':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'fair':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'poor':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'perfect':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // 精度グレードのテキスト
  const getAccuracyText = (grade) => {
    const gradeMapping = {
      'excellent': '優秀',
      'good': '良好',
      'fair': '普通',
      'poor': '要改善',
      'perfect': '完璧'
    };
    return gradeMapping[grade] || '不明';
  };

  // 過去日付かどうかを判定
  const isPastDate = (dateStr) => {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      const targetDate = new Date(dateStr.replace(/\//g, '-'));
      targetDate.setHours(0, 0, 0, 0);
      
      return targetDate < today;
    } catch {
      return false;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">データを読み込んでいます...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center text-red-600">
          <p className="text-lg font-semibold">エラーが発生しました</p>
          <p className="mt-2">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            再読み込み
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* ヘッダー */}
        <div className="text-center mb-8">
          {/* 戻るボタン追加 */}
          <div className="flex justify-start mb-4">
            <Link href="/">
              <button className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center">
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                トップに戻る
              </button>
            </Link>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">🎣 アジ釣果予測システム</h1>
          <p className="text-gray-600">本牧海釣り施設のアジ釣果を機械学習で予測します</p>
          
          {/* API状態表示 */}
          {apiStatus && (
            <div className="mt-4 inline-flex items-center space-x-2 text-sm">
              <span className={`inline-block w-2 h-2 rounded-full ${
                apiStatus.success && apiStatus.status.model === 'loaded' 
                  ? 'bg-green-500' 
                  : 'bg-yellow-500'
              }`}></span>
              <span className="text-gray-600">
                API: {apiStatus.success ? '正常' : 'エラー'} | 
                モデル: {apiStatus.status?.model === 'loaded' ? '読み込み済み' : '未読み込み'}
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 左側: 予測条件設定 */}
          <div className="space-y-6">
            {/* 予測条件カード */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <div className="flex items-center mb-6">
                <span className="text-2xl mr-3">📅</span>
                <h2 className="text-xl font-semibold text-gray-800">予測条件</h2>
                {isPastDate(selectedDate) && (
                  <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                    過去日付
                  </span>
                )}
              </div>

              {/* 予測日 */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <span className="text-lg mr-2">📅</span>
                  <label className="text-sm font-medium text-gray-700">予測日</label>
                </div>
                <input
                  type="date"
                  value={selectedDate.replace(/\//g, '-')}
                  onChange={(e) => setSelectedDate(e.target.value.replace(/-/g, '/'))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="mt-1 text-sm text-gray-500">
                  {selectedDate} ({getWeekday(selectedDate)})
                  {isPastDate(selectedDate) && (
                    <span className="ml-2 text-blue-600 font-medium">
                      → 実績データとの比較が可能
                    </span>
                  )}
                </p>
              </div>

              {/* 天気 */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <span className="text-lg mr-2">🌤️</span>
                  <label className="text-sm font-medium text-gray-700">天気</label>
                </div>
                <select
                  value={selectedWeather}
                  onChange={(e) => setSelectedWeather(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {weatherOptions.map(weather => (
                    <option key={weather} value={weather}>
                      {weather === '雪' && '❄️ '}
                      {weather === '雨' && '🌧️ '}
                      {weather === '曇り' && '☁️ '}
                      {weather === '晴れ' && '☀️ '}
                      {weather}
                    </option>
                  ))}
                </select>
              </div>

              {/* 来場者数（自動推定） */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <span className="text-lg mr-2">👥</span>
                  <label className="text-sm font-medium text-gray-700">来場者数 (自動推定)</label>
                </div>
                <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-2xl font-bold text-green-700">{estimatedVisitors}人</span>
                    <span className="text-sm text-green-600">
                      {selectedWeather} • {getWeekday(selectedDate)}の平均
                    </span>
                  </div>
                  
                  <div className="relative">
                    <input
                      type="range"
                      min="50"
                      max="800"
                      step="5"
                      value={estimatedVisitors}
                      onChange={(e) => setEstimatedVisitors(parseInt(e.target.value))}
                      className="w-full h-2 bg-green-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>50人</span>
                      <span className="text-center">手動調整可能</span>
                      <span>800人</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 水温 */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <span className="text-lg mr-2">🌡️</span>
                  <label className="text-sm font-medium text-gray-700">水温</label>
                </div>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="10"
                    max="30"
                    step="0.5"
                    value={fishingConditions.waterTemp}
                    onChange={(e) => setFishingConditions(prev => ({
                      ...prev,
                      waterTemp: parseFloat(e.target.value)
                    }))}
                    className="flex-1 h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <span className="text-lg font-semibold text-blue-600 min-w-[60px]">
                    {fishingConditions.waterTemp}°C
                  </span>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>10°C</span>
                  <span>最適: 22°C</span>
                  <span>30°C</span>
                </div>
              </div>

              {/* 潮回り */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <span className="text-lg mr-2">🌊</span>
                  <label className="text-sm font-medium text-gray-700">潮回り</label>
                </div>
                <select
                  value={fishingConditions.tide}
                  onChange={(e) => setFishingConditions(prev => ({
                    ...prev,
                    tide: e.target.value
                  }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {tideOptions.map(tide => (
                    <option key={tide} value={tide}>{tide}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 予測実行ボタン */}
            <button
              onClick={handlePredictCatch}
              disabled={predictionLoading}
              className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-all duration-200 ${
                predictionLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg'
              }`}
            >
              {predictionLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  予測中...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <span className="text-xl mr-2">🎣</span>
                  {isPastDate(selectedDate) ? 'アジ釣果を予測・検証する' : 'アジ釣果を予測する'}
                </div>
              )}
            </button>
          </div>

          {/* 右側: 予測結果 */}
          <div className="space-y-6">
            {/* 予測結果カード */}
            {predictionResult && (
              <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <div className="flex items-center mb-6">
                  <span className="text-2xl mr-3">🎯</span>
                  <h3 className="text-xl font-semibold text-gray-800">
                    {predictionResult.is_historical ? '予測結果 vs 実績' : '予測結果'}
                  </h3>
                </div>

                {/* 予測 vs 実績の比較表示 */}
                {predictionResult.is_historical && predictionResult.actual_catch !== null ? (
                  <div className="space-y-6">
                    {/* 予測値と実績値の並列表示 */}
                    <div className="grid grid-cols-2 gap-4">
                      {/* 予測値 */}
                      <div className="bg-blue-50 rounded-lg p-4 text-center border border-blue-200">
                        <div className="text-sm text-blue-600 mb-1">AI予測</div>
                        <div className="text-3xl font-bold text-blue-700">
                          {predictionResult.catch_count}匹
                        </div>
                      </div>
                      
                      {/* 実績値 */}
                      <div className="bg-green-50 rounded-lg p-4 text-center border border-green-200">
                        <div className="text-sm text-green-600 mb-1">実績</div>
                        <div className="text-3xl font-bold text-green-700">
                          {predictionResult.actual_catch}匹
                        </div>
                      </div>
                    </div>

                    {/* 精度分析 */}
                    {predictionResult.accuracy_metrics && (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-semibold text-gray-700 mb-3 flex items-center">
                          <span className="text-lg mr-2">📊</span>
                          予測精度分析
                        </h4>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <span className="text-sm text-gray-600">誤差量:</span>
                            <span className="ml-1 font-semibold text-gray-800">
                              {predictionResult.accuracy_metrics.error_amount}匹
                            </span>
                          </div>
                          <div>
                            <span className="text-sm text-gray-600">誤差率:</span>
                            <span className="ml-1 font-semibold text-gray-800">
                              {predictionResult.accuracy_metrics.error_percent}%
                            </span>
                          </div>
                        </div>
                        
                        <div className="mt-3">
                          <span className="text-sm text-gray-600">精度評価:</span>
                          <span className={`ml-1 px-2 py-1 rounded text-xs font-semibold border ${getAccuracyStyle(predictionResult.accuracy_metrics.accuracy_grade)}`}>
                            {getAccuracyText(predictionResult.accuracy_metrics.accuracy_grade)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* 通常の予測結果表示 */
                  <div className="bg-blue-50 rounded-lg p-6 mb-6 text-center">
                    <div className="text-4xl font-bold text-blue-700 mb-2">
                      {predictionResult.catch_count}匹
                    </div>
                    <div className="text-lg text-blue-600 mb-3">アジの予測釣果数</div>
                    <div className="flex items-center justify-center space-x-4 text-sm">
                      <div className="flex items-center">
                        <span className="text-gray-600">信頼度:</span>
                        <span className={`ml-1 px-2 py-1 rounded text-xs font-semibold border ${getConfidenceStyle(predictionResult.confidence)}`}>
                          {getConfidenceText(predictionResult.confidence)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 過去日付で実績が見つからない場合の警告 */}
                {predictionResult.is_historical && predictionResult.actual_catch === null && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center">
                      <span className="text-yellow-600 mr-2">⚠️</span>
                      <span className="text-yellow-800 text-sm">
                        この日付の実績データが見つかりませんでした。予測値のみ表示しています。
                      </span>
                    </div>
                  </div>
                )}

                {/* 入力条件確認 */}
                <div className="bg-gray-50 rounded-lg p-4 mb-6">
                  <h4 className="font-semibold text-gray-700 mb-3">予測条件</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-600">日付:</span>
                      <span className="ml-1 font-medium">{predictionResult.input_conditions.date}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">天気:</span>
                      <span className="ml-1 font-medium">{predictionResult.input_conditions.weather}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">水温:</span>
                      <span className="ml-1 font-medium">{predictionResult.input_conditions.water_temp}°C</span>
                    </div>
                    <div>
                      <span className="text-gray-600">潮:</span>
                      <span className="ml-1 font-medium">{predictionResult.input_conditions.tide}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-gray-600">来場者数:</span>
                      <span className="ml-1 font-medium">{predictionResult.input_conditions.visitors}人</span>
                    </div>
                  </div>
                </div>

                {/* 推奨条件 */}
                {predictionResult.recommendations && predictionResult.recommendations.length > 0 && (
                  <div className="bg-yellow-50 rounded-lg p-4">
                    <h4 className="font-semibold text-yellow-800 mb-3 flex items-center">
                      <span className="text-lg mr-2">💡</span>
                      釣行アドバイス
                    </h4>
                    <ul className="space-y-2">
                      {predictionResult.recommendations.map((rec, index) => (
                        <li key={index} className="text-sm text-yellow-700 flex items-start">
                          <span className="text-yellow-500 mr-2 mt-1">•</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* エラー表示 */}
            {predictionError && (
              <div className="bg-white rounded-lg shadow-md p-6 border border-red-200">
                <div className="flex items-center mb-4">
                  <span className="text-2xl mr-3">⚠️</span>
                  <h3 className="text-xl font-semibold text-red-800">予測エラー</h3>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-red-700">{predictionError}</p>
                  <p className="text-sm text-red-600 mt-2">
                    APIサーバーが起動しているか確認し、再試行してください。
                  </p>
                </div>
              </div>
            )}

            {/* 初期状態のプレースホルダー */}
            {!predictionResult && !predictionError && !predictionLoading && (
              <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">🎣</div>
                  <h3 className="text-xl font-semibold text-gray-700 mb-2">予測結果</h3>
                  <p className="text-gray-500">
                    条件を設定して「アジ釣果を予測する」ボタンを押してください
                  </p>
                  {isPastDate(selectedDate) && (
                    <p className="text-blue-600 text-sm mt-2">
                      💡 過去日付が選択されています - 予測と実績の比較が可能です
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* システム情報 */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <div className="flex items-center mb-4">
                <span className="text-2xl mr-3">ℹ️</span>
                <h3 className="text-lg font-semibold text-gray-800">システム情報</h3>
              </div>
              <div className="text-sm text-gray-600 space-y-2">
                <p>• 機械学習モデル: Random Forest</p>
                <p>• 学習データ: 過去6ヶ月の釣果データ (2,897件)</p>
                <p>• 予測対象: アジの釣果数</p>
                <p>• 特徴量: 月・季節・天気・水温・潮・来場者数</p>
                <p>• 更新: 2025年8月版</p>
                <p className="text-blue-600">• <strong>新機能</strong>: 過去日付での予測vs実績表示</p>
              </div>
            </div>
          </div>
        </div>

        {/* フッター */}
        <div className="text-center mt-12 pt-8 border-t border-gray-200">
          <p className="text-gray-500">
            🎣 本牧海釣り施設 釣果予測システム | 
            <a href="/historical" className="text-blue-600 hover:underline ml-1">過去データ閲覧</a>
          </p>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
        }
        
        .slider::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}