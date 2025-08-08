// lib/api.js - 本牧海釣り施設釣果予測API クライアントライブラリ

// 🌐 環境対応API URL設定 (Phase 12)
let API_BASE_URL;

if (process.env.NODE_ENV === 'production') {
  API_BASE_URL = 'https://fishing-prediction-system.onrender.com';
} else {
  API_BASE_URL = 'http://localhost:8000';
}

console.log('🔧 API Base URL:', API_BASE_URL, '(Environment:', process.env.NODE_ENV, ')');

/**
 * API呼び出し基盤関数
 * @param {string} endpoint - APIエンドポイント
 * @param {Object} options - fetchオプション
 * @returns {Promise<Object>} APIレスポンス
 */
async function apiCall(endpoint, options = {}) {
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API Call Failed:', error);
    throw error;
  }
}

/**
 * 過去データ取得API
 * @param {Object} params - フィルターパラメータ
 * @param {string} params.fish - 魚種フィルター
 * @param {string} params.weather - 天気フィルター
 * @param {string} params.tide - 潮フィルター
 * @param {string} params.start_date - 開始日 (YYYY-MM-DD)
 * @param {string} params.end_date - 終了日 (YYYY-MM-DD)
 * @param {number} params.limit - 取得件数制限
 * @returns {Promise<Object>} 釣果データとサマリー
 */
export async function getHistoricalData(params = {}) {
  // 空の値を除外してクエリパラメータを構築
  const filteredParams = Object.entries(params)
    .filter(([key, value]) => value !== '' && value !== null && value !== undefined)
    .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});

  const queryString = new URLSearchParams(filteredParams).toString();
  const endpoint = `/api/historical${queryString ? `?${queryString}` : ''}`;
  
  return await apiCall(endpoint);
}

/**
 * 来場者数分析データ取得
 * @returns {Promise<Object>} 天気×曜日別来場者数平均
 */
export async function getVisitorAverages() {
  try {
    const response = await apiCall('/api/visitor-averages');
    return response;
  } catch (error) {
    console.error('来場者数分析データ取得エラー:', error);
    throw error;
  }
}

// ===== Phase 6: 釣果予測機能 =====

/**
 * アジ釣果予測API
 * @param {Object} predictionData - 予測条件
 * @param {string} predictionData.date - 予測日 (YYYY/MM/DD)
 * @param {string} predictionData.weather - 天気 (晴れ, 曇り, 雨, 雪)
 * @param {number} predictionData.visitors - 来場者数
 * @param {number} predictionData.water_temp - 水温 (℃)
 * @param {string} predictionData.tide - 潮回り (大潮, 中潮, 小潮, 長潮, 若潮)
 * @returns {Promise<Object>} 予測結果
 */
export async function predictAjiCatch(predictionData) {
  try {
    console.log('🎣 アジ釣果予測API呼び出し:', predictionData);
    
    const response = await apiCall('/api/predict-aji', {
      method: 'POST',
      body: JSON.stringify({
        date: predictionData.date,
        weather: predictionData.weather,
        visitors: predictionData.visitors,
        water_temp: predictionData.water_temp,
        tide: predictionData.tide,
      }),
    });

    console.log('✅ 予測API成功:', response);
    return response;
    
  } catch (error) {
    console.error('❌ アジ釣果予測エラー:', error);
    throw error;
  }
}

/**
 * API状態確認
 * @returns {Promise<Object>} API動作状況
 */
export async function getApiStatus() {
  try {
    const response = await apiCall('/api/status');
    return response;
  } catch (error) {
    console.error('API状態確認エラー:', error);
    throw error;
  }
}

// ===== ユーティリティ関数 =====

/**
 * 日付フォーマット変換 (YYYY-MM-DD → YYYY/MM/DD)
 * @param {string|Date} date - 変換対象の日付
 * @returns {string} YYYY/MM/DD形式の日付
 */
export const formatDateForAPI = (date) => {
  if (date instanceof Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}`;
  }
  
  // YYYY-MM-DD → YYYY/MM/DD
  if (typeof date === 'string' && date.includes('-')) {
    return date.replace(/-/g, '/');
  }
  
  return date;
};

/**
 * 曜日取得
 * @param {string} dateString - 日付文字列
 * @returns {string} 曜日 (日本語)
 */
export const getWeekday = (dateString) => {
  const date = new Date(dateString);
  const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
  return weekdays[date.getDay()];
};

/**
 * 曜日取得（英語）
 * @param {string} dateString - 日付文字列
 * @returns {string} 曜日 (英語)
 */
export const getWeekdayEn = (dateString) => {
  const date = new Date(dateString);
  const weekdays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return weekdays[date.getDay()];
};

/**
 * 信頼度の日本語表示
 * @param {string} confidence - 信頼度 (High/Medium/Low)
 * @returns {string} 日本語の信頼度
 */
export const getConfidenceText = (confidence) => {
  const confidenceMap = {
    'High': '高',
    'Medium': '中',
    'Low': '低'
  };
  return confidenceMap[confidence] || confidence;
};

/**
 * エラーメッセージの日本語化
 * @param {Error} error - エラーオブジェクト
 * @returns {string} 日本語エラーメッセージ
 */
export const getErrorMessage = (error) => {
  if (error.message.includes('fetch')) {
    return 'サーバーに接続できません。APIサーバーが起動しているか確認してください。';
  } else if (error.message.includes('HTTP error')) {
    return 'サーバーでエラーが発生しました。しばらく待ってから再試行してください。';
  } else {
    return error.message || '予期しないエラーが発生しました。';
  }
};

/**
 * 天気の英語→日本語変換
 * @param {string} weatherEn - 英語の天気
 * @returns {string} 日本語の天気
 */
export const weatherEnToJa = (weatherEn) => {
  const weatherMap = {
    'sunny': '晴れ',
    'cloudy': '曇り',
    'rainy': '雨',
    'snowy': '雪'
  };
  return weatherMap[weatherEn] || weatherEn;
};

/**
 * 天気の日本語→英語変換
 * @param {string} weatherJa - 日本語の天気
 * @returns {string} 英語の天気
 */
export const weatherJaToEn = (weatherJa) => {
  const weatherMap = {
    '晴れ': 'sunny',
    '曇り': 'cloudy',
    '雨': 'rainy',
    '雪': 'snowy'
  };
  return weatherMap[weatherJa] || weatherJa;
};

// ===== 既存の統計関数群 =====

/**
 * 魚種別統計データ取得
 * @param {string} fish - 対象魚種
 * @param {number} limit - データ取得上限
 * @returns {Promise<Object>} 魚種別統計
 */
export async function getFishStatistics(fish, limit = 1000) {
  return await getHistoricalData({ fish, limit });
}

/**
 * 月別統計データ取得
 * @param {number} year - 対象年
 * @param {number} month - 対象月 (1-12)
 * @returns {Promise<Object>} 月別統計
 */
export async function getMonthlyStatistics(year, month) {
  const startDate = `${year}-${month.toString().padStart(2, '0')}-01`;
  const endDate = new Date(year, month, 0).toISOString().split('T')[0]; // 月末日
  
  return await getHistoricalData({ 
    start_date: startDate, 
    end_date: endDate,
    limit: 1000 
  });
}

/**
 * 天気別統計データ取得
 * @param {string} weather - 天気条件
 * @param {number} limit - データ取得上限
 * @returns {Promise<Object>} 天気別統計
 */
export async function getWeatherStatistics(weather, limit = 1000) {
  return await getHistoricalData({ weather, limit });
}

/**
 * 潮別統計データ取得  
 * @param {string} tide - 潮条件
 * @param {number} limit - データ取得上限
 * @returns {Promise<Object>} 潮別統計
 */
export async function getTideStatistics(tide, limit = 1000) {
  return await getHistoricalData({ tide, limit });
}

/**
 * 期間別統計データ取得
 * @param {string} startDate - 開始日 (YYYY-MM-DD)
 * @param {string} endDate - 終了日 (YYYY-MM-DD)
 * @param {number} limit - データ取得上限
 * @returns {Promise<Object>} 期間別統計
 */
export async function getPeriodStatistics(startDate, endDate, limit = 1000) {
  return await getHistoricalData({ 
    start_date: startDate, 
    end_date: endDate,
    limit 
  });
}

/**
 * 人気魚種ランキング取得
 * @param {number} topN - 上位N件取得
 * @returns {Promise<Array>} 魚種ランキング
 */
export async function getPopularFishRanking(topN = 10) {
  const data = await getHistoricalData({ limit: 5000 });
  
  if (!data.summary?.by_fish_type) {
    return [];
  }

  // 魚種別の平均釣果でソート
  const ranking = Object.entries(data.summary.by_fish_type)
    .map(([fish, stats]) => ({
      fish,
      avgCatch: stats.avg_catch,
      totalCatch: stats.total_catch,
      days: stats.days
    }))
    .sort((a, b) => b.avgCatch - a.avgCatch)
    .slice(0, topN);

  return ranking;
}

/**
 * 最新釣果データ取得
 * @param {number} limit - 取得件数
 * @returns {Promise<Array>} 最新釣果リスト
 */
export async function getLatestCatch(limit = 10) {
  const data = await getHistoricalData({ limit });
  return data.data?.records || [];
}

/**
 * API接続テスト
 * @returns {Promise<boolean>} 接続成功/失敗
 */
export async function testApiConnection() {
  try {
    await apiCall('/api/historical?limit=1');
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * 条件別釣果分析
 * @param {Object} analysisParams - 分析パラメータ
 * @param {string} analysisParams.fish - 対象魚種
 * @param {Array} analysisParams.conditions - 比較条件配列
 * @returns {Promise<Object>} 分析結果
 */
export async function analyzeConditions(analysisParams) {
  const { fish, conditions } = analysisParams;
  const results = [];

  for (const condition of conditions) {
    const data = await getHistoricalData({
      fish,
      ...condition,
      limit: 1000
    });
    
    results.push({
      condition,
      totalCatch: data.summary?.total_catch || 0,
      avgCatch: data.summary?.avg_catch || 0,
      records: data.data?.total_count || 0
    });
  }

  return {
    fish,
    analysis: results,
    best_condition: results.reduce((best, current) => 
      current.avgCatch > best.avgCatch ? current : best, results[0])
  };
}

/**
 * 統計サマリー取得（ダッシュボード用）
 * @returns {Promise<Object>} 全体統計
 */
export async function getOverallStatistics() {
  const data = await getHistoricalData({ limit: 5000 });
  
  if (!data.summary) {
    return null;
  }

  const summary = data.summary;
  
  // 月別平均釣果（サンプルデータから推定）
  const monthlyAvg = {
    1: 36.4, 2: 85.2, 3: 150.8, 4: 275.3, 5: 399.1,
    6: 320.7, 7: 209.8, 8: 180.5, 9: 210.2, 10: 165.8,
    11: 120.3, 12: 45.6
  };

  return {
    total_records: summary.total_records,
    total_catch: summary.total_catch,
    avg_catch: summary.avg_catch,
    fish_types: Object.keys(summary.by_fish_type || {}).length,
    top_fish: Object.entries(summary.by_fish_type || {})
      .sort(([,a], [,b]) => b.avg_catch - a.avg_catch)[0]?.[0],
    monthly_avg: monthlyAvg,
    best_month: Object.entries(monthlyAvg)
      .sort(([,a], [,b]) => b - a)[0]?.[0]
  };
}

/**
 * 条件推奨システム
 * @param {string} targetFish - 目標魚種
 * @param {string} targetDate - 釣行予定日
 * @returns {Promise<Object>} 推奨条件
 */
export async function getRecommendedConditions(targetFish, targetDate) {
  // 対象魚種の統計データ取得
  const fishData = await getFishStatistics(targetFish, 2000);
  
  if (!fishData.data?.records) {
    return { error: 'データが不足しています' };
  }

  const records = fishData.data.records;
  
  // 釣果が良い条件を分析
  const goodCatch = records.filter(r => r.釣果数 > fishData.summary.avg_catch);
  
  // 条件別の出現頻度と平均釣果を計算
  const weatherStats = {};
  const tideStats = {};
  
  goodCatch.forEach(record => {
    // 天気統計
    if (!weatherStats[record.天気]) {
      weatherStats[record.天気] = { count: 0, totalCatch: 0 };
    }
    weatherStats[record.天気].count++;
    weatherStats[record.天気].totalCatch += record.釣果数;
    
    // 潮統計
    if (!tideStats[record.潮]) {
      tideStats[record.潮] = { count: 0, totalCatch: 0 };
    }
    tideStats[record.潮].count++;
    tideStats[record.潮].totalCatch += record.釣果数;
  });

  // 推奨条件を算出
  const bestWeather = Object.entries(weatherStats)
    .map(([weather, stats]) => ({
      weather,
      avgCatch: stats.totalCatch / stats.count,
      frequency: stats.count
    }))
    .sort((a, b) => b.avgCatch - a.avgCatch)[0];

  const bestTide = Object.entries(tideStats)
    .map(([tide, stats]) => ({
      tide,
      avgCatch: stats.totalCatch / stats.count,
      frequency: stats.frequency
    }))
    .sort((a, b) => b.avgCatch - a.avgCatch)[0];

  return {
    target_fish: targetFish,
    target_date: targetDate,
    recommendations: {
      best_weather: bestWeather?.weather || '晴れ',
      best_tide: bestTide?.tide || '大潮',
      expected_catch: Math.round((bestWeather?.avgCatch || 0) * 0.8),
      confidence: Math.min(90, (goodCatch.length / 50) * 100)
    },
    analysis: {
      total_records: records.length,
      good_catch_records: goodCatch.length,
      avg_catch: Math.round(fishData.summary.avg_catch)
    }
  };
}

// 定数エクスポート
export const API_CONSTANTS = {
  BASE_URL: API_BASE_URL,
  ENDPOINTS: {
    HISTORICAL: '/api/historical',
    VISITOR_AVERAGES: '/api/visitor-averages',
    PREDICT_AJI: '/api/predict-aji',  // 新追加
    STATUS: '/api/status',            // 新追加
  },
  POPULAR_FISH: ['アジ', 'イワシ', 'サバ', 'メバル', 'カサゴ', 'スズキ', 'イナダ', 'ワカシ'],
  WEATHER_OPTIONS: ['晴れ', '曇り', '雨', '雪'],
  TIDE_OPTIONS: ['大潮', '中潮', '小潮', '長潮', '若潮'],
  MONTHS: [
    '1月', '2月', '3月', '4月', '5月', '6月',
    '7月', '8月', '9月', '10月', '11月', '12月'
  ]
};

// デフォルトエクスポート（名前付きインポート推奨）
export default {
  // 基本API関数
  getHistoricalData,
  getVisitorAverages,
  predictAjiCatch,        // 新追加
  getApiStatus,           // 新追加
  
  // 統計・分析関数
  getFishStatistics,
  getMonthlyStatistics,
  getWeatherStatistics,
  getTideStatistics,
  getPeriodStatistics,
  getPopularFishRanking,
  getLatestCatch,
  analyzeConditions,
  getOverallStatistics,
  getRecommendedConditions,
  
  // ユーティリティ関数
  formatDateForAPI,       // 新追加
  getWeekday,            // 新追加
  getWeekdayEn,          // 新追加
  getConfidenceText,     // 新追加
  getErrorMessage,       // 新追加
  weatherEnToJa,         // 新追加
  weatherJaToEn,         // 新追加
  
  // その他
  testApiConnection,
  API_CONSTANTS
};