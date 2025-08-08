import { useState, useEffect } from 'react'
import Link from 'next/link'
import Head from 'next/head'
import { getApiStatus } from '../lib/api' // 🔧 Phase 12追加

export default function Home() {
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 🌐 Phase 12修正: lib/api.jsのgetApiStatus関数を使用
    const checkSystemStatus = async () => {
      try {
        const data = await getApiStatus()
        setSystemStatus(data)
      } catch (err) {
        console.error('システム状態取得エラー:', err)
      } finally {
        setLoading(false)
      }
    }

    checkSystemStatus()
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100">
      <Head>
        <title>本牧海釣り施設 アジ釣果予測システム</title>
        <meta name="description" content="機械学習による釣果予測と過去データ分析システム" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="container mx-auto px-4 py-12">
        {/* ヘッダー */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-blue-800 mb-4">
            🎣 本牧海釣り施設
          </h1>
          <h2 className="text-3xl font-semibold text-blue-600 mb-2">
            アジ釣果予測システム
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            機械学習技術を活用した高精度な釣果予測と、過去データの詳細分析で
            あなたの釣行をサポートします
          </p>
        </div>

        {/* システム状態 */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8 max-w-4xl mx-auto">
          <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">⚡</span>
            システム状態
          </h3>
          
          {loading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-600">状態確認中...</span>
            </div>
          ) : systemStatus ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="text-green-600 font-medium">API サーバー</div>
                <div className="text-2xl text-green-800">
                  {systemStatus.success ? '✅ 稼働中' : '❌ エラー'}
                </div>
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-blue-600 font-medium">予測モデル</div>
                <div className="text-2xl text-blue-800">
                  {systemStatus.status?.model === 'loaded' ? '✅ 準備完了' : '⚠️ 未準備'}
                </div>
              </div>
              
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="text-purple-600 font-medium">過去データ</div>
                <div className="text-2xl text-purple-800">
                  {systemStatus.status?.historical_data === 'available' ? '✅ 利用可能' : '❌ エラー'}
                </div>
              </div>
              
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="text-orange-600 font-medium">来場者分析</div>
                <div className="text-2xl text-orange-800">
                  {systemStatus.status?.visitor_analysis === 'available' ? '✅ 利用可能' : '❌ エラー'}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <span className="text-red-600">⚠️ システム状態を取得できませんでした</span>
            </div>
          )}
        </div>

        {/* メイン機能ナビゲーション */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          
          {/* 釣果予測 */}
          <Link href="/predict">
            <div className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-8 cursor-pointer group">
              <div className="text-center">
                <div className="text-6xl mb-4">🎯</div>
                <h3 className="text-2xl font-bold text-blue-800 mb-3 group-hover:text-blue-600">
                  アジ釣果予測
                </h3>
                <p className="text-gray-600 mb-4">
                  天気・水温・来場者数から機械学習で釣果を予測
                </p>
                <div className="bg-blue-50 rounded-lg p-4 mb-4">
                  <div className="text-sm text-blue-700 font-medium mb-2">機能特徴</div>
                  <ul className="text-sm text-blue-600 space-y-1">
                    <li>✅ Random Forest モデル</li>
                    <li>✅ 25.7% 誤差精度実証済み</li>
                    <li>✅ 過去実績との比較表示</li>
                    <li>✅ 釣行アドバイス自動生成</li>
                  </ul>
                </div>
                <div className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium group-hover:bg-blue-500 transition-colors">
                  予測を開始 →
                </div>
              </div>
            </div>
          </Link>

          {/* 過去データ */}
          <Link href="/historical">
            <div className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-8 cursor-pointer group">
              <div className="text-center">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-2xl font-bold text-green-800 mb-3 group-hover:text-green-600">
                  過去データ分析
                </h3>
                <p className="text-gray-600 mb-4">
                  蓄積された釣果データの詳細分析と統計情報
                </p>
                <div className="bg-green-50 rounded-lg p-4 mb-4">
                  <div className="text-sm text-green-700 font-medium mb-2">データ概要</div>
                  <ul className="text-sm text-green-600 space-y-1">
                    <li>📈 継続的データ蓄積</li>
                    <li>🔍 条件別フィルタリング</li>
                    <li>📋 月別・魚種別集計</li>
                    <li>☀️ 天気別パフォーマンス</li>
                  </ul>
                </div>
                <div className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium group-hover:bg-green-500 transition-colors">
                  データを確認 →
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* システム情報 */}
        <div className="bg-white rounded-xl shadow-lg p-6 mt-12 max-w-4xl mx-auto">
          <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">ℹ️</span>
            システム情報
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl text-blue-500 mb-2">🤖</div>
              <div className="font-medium text-gray-800">機械学習</div>
              <div className="text-sm text-gray-600">Random Forest</div>
            </div>
            
            <div className="text-center">
              <div className="text-3xl text-green-500 mb-2">📡</div>
              <div className="font-medium text-gray-800">API</div>
              <div className="text-sm text-gray-600">FastAPI + Next.js</div>
            </div>
            
            <div className="text-center">
              <div className="text-3xl text-purple-500 mb-2">☁️</div>
              <div className="font-medium text-gray-800">データ</div>
              <div className="text-sm text-gray-600">Google Sheets</div>
            </div>
          </div>
        </div>

        {/* フッター */}
        <footer className="text-center mt-12 text-gray-500">
          <p>© 2025 本牧海釣り施設アジ釣果予測システム v1.0.0</p>
          <p className="text-sm mt-2">
            {/* 🌐 Phase 12修正: 環境対応API仕様書URL */}
            <a href={process.env.NODE_ENV === 'production' ? 'https://fishing-prediction-system.onrender.com/docs' : 'http://localhost:8000/docs'} target="_blank" className="hover:text-blue-600 transition-colors">
              API仕様書
            </a>
          </p>
        </footer>
      </div>
    </div>
  )
}