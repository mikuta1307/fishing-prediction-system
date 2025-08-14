import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { getHistoricalData, API_CONSTANTS } from '../lib/api';

// Next.js ページコンポーネント - lib/api.js使用シンプル版
export default function Historical() {
  // State管理
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    fish: '',
    weather: '',
    tide: '',
    start_date: '',
    end_date: '',
    limit: 50
  });

  // APIからデータ取得（lib/api.js使用）
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await getHistoricalData(filters);
      setData(result);
    } catch (err) {
      setError(`データ取得エラー: ${err.message}`);
      console.error('API Error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 初回データ読み込み
  useEffect(() => {
    fetchData();
  }, []);

  // フィルター変更ハンドラー
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // フィルター適用
  const applyFilters = () => {
    fetchData();
  };

  // フィルターリセット
  const resetFilters = () => {
    setFilters({
      fish: '',
      weather: '',
      tide: '',
      start_date: '',
      end_date: '',
      limit: 50
    });
  };

  // 定数をlib/api.jsから取得
  const { POPULAR_FISH, WEATHER_OPTIONS, TIDE_OPTIONS } = API_CONSTANTS;

  return (
    <>
      <Head>
        <title>過去データ閲覧 - 海釣り施設釣果予測システム</title>
        <meta name="description" content="海釣り施設の過去釣果データを閲覧・分析" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50">
        {/* ヘッダー */}
        <div className="bg-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {/* 戻るボタン */}
                <Link href="/">
                  <button className="mr-4 p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center">
                    <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    トップ
                  </button>
                </Link>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">🎣 過去データ閲覧</h1>
                  <p className="text-gray-600 mt-1">海釣り施設の釣果データ分析</p>
                </div>
              </div>
              <div className="text-right">
                {data && (
                  <div className="text-sm text-gray-500">
                    <p>総データ数: <span className="font-semibold text-blue-600">{data.data?.total_count?.toLocaleString()}件</span></p>
                    <p>総釣果: <span className="font-semibold text-green-600">{data.summary?.total_catch?.toLocaleString()}匹</span></p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* フィルター部分 */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">🔍 検索フィルター</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
              {/* 魚種選択 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">魚種</label>
                <select 
                  value={filters.fish} 
                  onChange={(e) => handleFilterChange('fish', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">全ての魚種</option>
                  {POPULAR_FISH.map(fish => (
                    <option key={fish} value={fish}>{fish}</option>
                  ))}
                </select>
              </div>

              {/* 天気選択 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">天気</label>
                <select 
                  value={filters.weather} 
                  onChange={(e) => handleFilterChange('weather', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">全ての天気</option>
                  {WEATHER_OPTIONS.map(weather => (
                    <option key={weather} value={weather}>{weather}</option>
                  ))}
                </select>
              </div>

              {/* 潮選択 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">潮</label>
                <select 
                  value={filters.tide} 
                  onChange={(e) => handleFilterChange('tide', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">全ての潮</option>
                  {TIDE_OPTIONS.map(tide => (
                    <option key={tide} value={tide}>{tide}</option>
                  ))}
                </select>
              </div>

              {/* 開始日 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">開始日</label>
                <input 
                  type="date" 
                  value={filters.start_date}
                  onChange={(e) => handleFilterChange('start_date', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* 終了日 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">終了日</label>
                <input 
                  type="date" 
                  value={filters.end_date}
                  onChange={(e) => handleFilterChange('end_date', e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* 表示件数とボタン */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">表示件数</label>
                  <select 
                    value={filters.limit} 
                    onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
                    className="p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={10}>10件</option>
                    <option value={25}>25件</option>
                    <option value={50}>50件</option>
                    <option value={100}>100件</option>
                    <option value={200}>200件</option>
                  </select>
                </div>
              </div>
              
              <div className="flex space-x-3">
                <button 
                  onClick={resetFilters}
                  className="px-4 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  リセット
                </button>
                <button 
                  onClick={applyFilters}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
                >
                  {loading ? '検索中...' : '検索'}
                </button>
              </div>
            </div>
          </div>

          {/* エラー表示 */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <div className="text-red-600 mr-3">⚠️</div>
                <div>
                  <h3 className="text-red-800 font-medium">エラーが発生しました</h3>
                  <p className="text-red-700 text-sm mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* 統計情報 */}
          {data?.summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="text-3xl mr-4">📊</div>
                  <div>
                    <p className="text-sm text-gray-600">総データ数</p>
                    <p className="text-2xl font-bold text-blue-600">{data.summary.total_records?.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="text-3xl mr-4">🐟</div>
                  <div>
                    <p className="text-sm text-gray-600">総釣果数</p>
                    <p className="text-2xl font-bold text-green-600">{data.summary.total_catch?.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="text-3xl mr-4">📈</div>
                  <div>
                    <p className="text-sm text-gray-600">平均釣果</p>
                    <p className="text-2xl font-bold text-purple-600">{data.summary.avg_catch?.toFixed(1)}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="text-3xl mr-4">🎣</div>
                  <div>
                    <p className="text-sm text-gray-600">魚種数</p>
                    <p className="text-2xl font-bold text-orange-600">{Object.keys(data.summary.by_fish_type || {}).length}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* データテーブル */}
          {loading ? (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <div className="text-6xl mb-4">🎣</div>
              <p className="text-lg text-gray-600">データを取得中...</p>
            </div>
          ) : data?.data?.records ? (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b">
                <h3 className="text-lg font-semibold text-gray-800">
                  📋 釣果データ ({data.data.returned_count}件表示 / 全{data.data.total_count}件)
                </h3>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日付</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">魚種</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">釣果数</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">サイズ</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">天気</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">潮</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">水温</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">来場者</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {data.data.records.map((record, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {new Date(record.日付).toLocaleDateString('ja-JP')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {record.魚種}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                          {record.釣果数?.toLocaleString()}匹
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{record.サイズ || '-'}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{record.天気}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{record.潮}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{record.水温}°C</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {record.来場者数?.toLocaleString()}人
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <div className="text-6xl mb-4">🤔</div>
              <p className="text-lg text-gray-600">データが見つかりませんでした</p>
              <p className="text-sm text-gray-500 mt-2">フィルター条件を変更してお試しください</p>
            </div>
          )}

          {/* フッターナビゲーション */}
          <div className="text-center mt-12 pt-8 border-t border-gray-200">
            <p className="text-gray-500 mb-4">
              🎣 海釣り施設 釣果予測システム
            </p>
            <div className="flex justify-center space-x-4">
              <Link href="/" className="text-blue-600 hover:underline">
                🏠 トップページ
              </Link>
              <Link href="/predict" className="text-blue-600 hover:underline">
                🎯 釣果予測
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}