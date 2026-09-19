import os

html_content = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>幣安廣場「K線人生飞哥」2年全量研報智庫 (2024-2026 官方動態完整收錄)</title>
    <style>
        :root {
            --primary: #181a20;
            --secondary: #0b0e11;
            --card-bg: #202630;
            --card-hover: #262e3b;
            --border: #333b47;
            --border-light: #474d57;
            --text-primary: #eaecef;
            --text-secondary: #929aa5;
            --text-muted: #707a8a;
            --accent-yellow: #fcd535;
            --accent-gold: #f0b90b;
            --accent-blue: #38bdf8;
            --accent-purple: #c084fc;
            --success: #2ebd85;
            --danger: #f6465d;
            --tag-bg: #2b3139;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "BinanceNova", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px 16px 80px 16px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* 頂部導航 */
        .top-navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 16px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 20px;
            font-weight: 700;
            color: var(--accent-yellow);
        }

        .nav-link-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--tag-bg);
            border: 1px solid var(--border);
            color: var(--accent-yellow);
            padding: 6px 14px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .nav-link-btn:hover {
            background: rgba(252, 213, 53, 0.15);
            border-color: var(--accent-yellow);
        }

        /* 創作者個人主頁橫幅卡片 */
        .kol-banner-card {
            background: linear-gradient(135deg, #202630 0%, #181a20 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }

        .kol-profile {
            display: flex;
            align-items: center;
            gap: 18px;
        }

        .kol-avatar {
            width: 76px;
            height: 76px;
            border-radius: 50%;
            border: 3px solid var(--accent-yellow);
            background-image: url('https://public.bnbstatic.com/image/pgc/202512/b736e2f07305a1fea15b9f7319d016c8.png');
            background-size: cover;
            background-position: center;
            box-shadow: 0 4px 14px rgba(240, 185, 11, 0.3);
            flex-shrink: 0;
        }

        .kol-title-row {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .kol-name {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }

        .badge-verified {
            background: rgba(240, 185, 11, 0.15);
            color: var(--accent-yellow);
            border: 1px solid rgba(240, 185, 11, 0.4);
            font-size: 11.5px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .badge-rank {
            background: rgba(46, 189, 133, 0.15);
            color: var(--success);
            border: 1px solid rgba(46, 189, 133, 0.3);
            font-size: 11.5px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .badge-category {
            background: var(--tag-bg);
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .kol-bio {
            font-size: 13.5px;
            color: var(--text-secondary);
            margin-top: 6px;
            line-height: 1.5;
        }

        .kol-stats {
            display: flex;
            gap: 16px;
            background: rgba(11, 14, 17, 0.6);
            border: 1px solid var(--border);
            padding: 12px 20px;
            border-radius: 12px;
            flex-wrap: wrap;
        }

        .stat-box {
            text-align: center;
            min-width: 75px;
        }

        .stat-val {
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
        }

        .stat-lbl {
            font-size: 11.5px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* 控制器卡片 */
        .controls-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        /* 時光機導航列 */
        .timeline-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .timeline-label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            font-weight: 700;
            color: var(--accent-yellow);
        }

        .year-btn-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .year-btn {
            background: #181a20;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 5px 14px;
            border-radius: 6px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .year-btn:hover {
            background: #2b3139;
            color: #ffffff;
        }
        .year-btn.active {
            background: var(--accent-yellow);
            border-color: var(--accent-yellow);
            color: #181a20;
            font-weight: 700;
        }

        .month-select {
            background: #181a20;
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12.5px;
            outline: none;
            cursor: pointer;
        }
        .month-select:focus {
            border-color: var(--accent-yellow);
        }

        /* 專題標籤篩選列 */
        .topics-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }

        .topic-btn {
            background: var(--tag-bg);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 5px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .topic-btn:hover {
            background: #333b47;
            color: #ffffff;
        }
        .topic-btn.active {
            background: rgba(240, 185, 11, 0.15);
            border-color: var(--accent-yellow);
            color: var(--accent-yellow);
            font-weight: 700;
        }

        /* 搜尋列 */
        .search-wrap {
            position: relative;
            width: 100%;
        }

        .search-input {
            width: 100%;
            background: #181a20;
            border: 1px solid var(--border);
            color: #ffffff;
            padding: 12px 42px 12px 42px;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent-yellow);
            box-shadow: 0 0 0 2px rgba(240, 185, 11, 0.2);
        }

        .search-icon {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            pointer-events: none;
        }

        .clear-btn {
            position: absolute;
            right: 14px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 16px;
            cursor: pointer;
            display: none;
        }
        .clear-btn:hover {
            color: #ffffff;
        }

        /* 資訊與分頁工具列 */
        .results-meta-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
            padding: 0 4px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .results-highlight {
            color: var(--accent-yellow);
            font-weight: 700;
        }

        .page-size-selector {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .page-size-selector select {
            background: #202630;
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            outline: none;
        }

        /* 貼文流佈局 */
        .posts-stream {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        /* 貼文單卡 */
        .post-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s ease;
        }
        .post-card:hover {
            border-color: #474d57;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .post-top-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .meta-badges {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .badge-source {
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 7px;
            border-radius: 4px;
        }

        .post-date-tag {
            font-size: 12px;
            color: var(--text-muted);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .post-id-tag {
            font-family: monospace;
            font-size: 11.5px;
            color: var(--text-muted);
        }

        .post-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 10px;
            line-height: 1.4;
        }

        .content-box {
            background: #181a20;
            border: 1px solid var(--border);
            border-left: 4px solid var(--accent-yellow);
            border-radius: 6px 10px 10px 6px;
            padding: 14px 16px;
            font-size: 14px;
            line-height: 1.75;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
            margin-bottom: 14px;
        }

        /* 引用歷史貼文區塊 */
        .quoted-box {
            background: rgba(11, 14, 17, 0.7);
            border: 1px dashed #474d57;
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin-bottom: 14px;
            white-space: pre-wrap;
        }
        .quoted-label {
            font-size: 11.5px;
            color: var(--accent-blue);
            font-weight: 700;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* 關聯交易對與行情標籤 */
        .pairs-bar {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 14px;
        }

        .pair-chip {
            background: #2b3139;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 3px 9px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .pair-up { color: var(--success); }
        .pair-down { color: var(--danger); }

        /* 底部數據與功能按鈕 */
        .post-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 12.5px;
            color: var(--text-muted);
        }

        .stats-group {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }

        .stat-entry {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .action-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-action {
            background: var(--tag-bg);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .btn-action:hover {
            background: #333b47;
            color: #ffffff;
        }
        .btn-action.btn-link {
            color: var(--accent-yellow);
            border-color: rgba(240, 185, 11, 0.3);
        }
        .btn-action.btn-link:hover {
            background: rgba(240, 185, 11, 0.15);
        }

        /* 分頁控制器 */
        .pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin-top: 36px;
            flex-wrap: wrap;
        }

        .page-btn {
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text-primary);
            min-width: 36px;
            height: 36px;
            padding: 0 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .page-btn:hover:not(:disabled) {
            background: #333b47;
            border-color: var(--accent-yellow);
        }
        .page-btn.active {
            background: var(--accent-yellow);
            border-color: var(--accent-yellow);
            color: #181a20;
            font-weight: 700;
        }
        .page-btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .page-ellipsis {
            color: var(--text-muted);
            padding: 0 4px;
        }

        /* 搜尋高亮 */
        mark.hl {
            background: rgba(252, 213, 53, 0.3);
            color: #ffffff;
            padding: 0 2px;
            border-radius: 2px;
        }

        .empty-indicator {
            text-align: center;
            padding: 80px 20px;
            color: var(--text-muted);
            font-size: 15px;
            background: var(--card-bg);
            border: 1px dashed var(--border);
            border-radius: 12px;
        }

        /* 回到頂部懸浮按鈕 */
        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent-yellow);
            color: #181a20;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4);
            transition: all 0.2s;
            opacity: 0;
            pointer-events: none;
            z-index: 100;
        }
        .back-to-top.show {
            opacity: 1;
            pointer-events: auto;
        }
        .back-to-top:hover {
            transform: translateY(-3px);
            background: #ffffff;
        }
    </style>
</head>
<body>

<div class="container">
    <!-- 頂部導航 -->
    <div class="top-navbar">
        <div class="brand-box">
            <span>⚡ 幣安廣場「K線人生飞哥」2年全量研報智庫 (2024-2026)</span>
        </div>
        <a href="index.html" class="nav-link-btn">
            <span>⬅ 返回 5-Zone 階梯智能持倉主系統</span>
        </a>
    </div>

    <!-- KOL 官方個人檔案卡片 -->
    <div class="kol-banner-card">
        <div class="kol-profile">
            <div class="kol-avatar"></div>
            <div>
                <div class="kol-title-row">
                    <h1 class="kol-name">K线人生飞哥</h1>
                    <span class="badge-verified">✓ 幣安廣場認證創作者</span>
                    <span class="badge-rank">30D收益榜 TOP</span>
                    <span class="badge-category">8年高頻交易者</span>
                </div>
                <div class="kol-bio">
                    公眾號：K線人生飛哥 ｜ 推特（X）：@TT520btc ｜ 幣安個人主頁：xg297174<br>
                    核心風格：注重週期研究、宏觀資金邏輯、大趨勢判斷、細分賽道龍頭選幣與低倍槓桿滾倉現貨
                </div>
            </div>
        </div>
        <div class="kol-stats">
            <div class="stat-box">
                <div class="stat-val" id="statTotalPosts">9,780</div>
                <div class="stat-lbl">收錄貼文總數</div>
            </div>
            <div class="stat-box">
                <div class="stat-val">2.5 年</div>
                <div class="stat-lbl">歷史時間跨度</div>
            </div>
            <div class="stat-box">
                <div class="stat-val" id="statTotalViews">--</div>
                <div class="stat-lbl">總累計閱讀量</div>
            </div>
            <div class="stat-box">
                <div class="stat-val" id="statTotalLikes">--</div>
                <div class="stat-lbl">總累計獲讚</div>
            </div>
        </div>
    </div>

    <!-- 搜尋與時光機控制器 -->
    <div class="controls-card">
        <!-- 時光機：年份與月份 -->
        <div class="timeline-bar">
            <div class="timeline-label">
                <span>⏳ 時光機歸檔導航：</span>
            </div>
            <div class="year-btn-group" id="yearBtnGroup">
                <button class="year-btn active" data-year="ALL" onclick="setYear('ALL')">全部年份 (9,780)</button>
                <button class="year-btn" data-year="2026" onclick="setYear('2026')">2026 年 (2,772)</button>
                <button class="year-btn" data-year="2025" onclick="setYear('2025')">2025 年 (6,767)</button>
                <button class="year-btn" data-year="2024" onclick="setYear('2024')">2024 年 (241)</button>
            </div>
            <div>
                <select id="monthSelect" class="month-select" onchange="setMonth(this.value)">
                    <option value="ALL">全部月份 (全年)</option>
                </select>
            </div>
        </div>

        <!-- 專題分類快選 -->
        <div class="topics-row" id="topicRow">
            <button class="topic-btn active" data-topic="all" onclick="setTopic('all')">🌟 全部貼文</button>
            <button class="topic-btn" data-topic="signals" onclick="setTopic('signals')">🎯 逃頂抄底點位 (76000/5.7萬/20萬/15萬)</button>
            <button class="topic-btn" data-topic="macro" onclick="setTopic('macro')">🌍 宏觀政策與週期 (加息/降息/大選/牛熊)</button>
            <button class="topic-btn" data-topic="ai" onclick="setTopic('ai')">🤖 AI 與算力 (TAO/FET/VIRTUAL/NEAR)</button>
            <button class="topic-btn" data-topic="l1" onclick="setTopic('l1')">⛓️ 主流與公鏈 (BTC/ETH/SOL/SUI/TIA)</button>
            <button class="topic-btn" data-topic="defi" onclick="setTopic('defi')">🦄 DeFi 與 DEX (UNI/ARB/HYPE/ENA/PENDLE)</button>
            <button class="topic-btn" data-topic="risk" onclick="setTopic('risk')">🛡️ 資金風控與心法 (手續費/返傭/定投/倉位)</button>
        </div>

        <!-- 搜尋列 -->
        <div class="search-wrap">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" class="search-input" placeholder="即時全文檢索（輸入幣種代碼、點位數值、或關鍵字，如：76000, 15萬, SUI, TAO, 熊市轉牛, 手續費）...">
            <button class="clear-btn" id="clearSearchBtn" onclick="clearSearch()">✕</button>
        </div>
    </div>

    <!-- 檢索結果資訊與分頁工具列 -->
    <div class="results-meta-bar">
        <div>
            <span>共檢索出 </span>
            <span class="results-highlight" id="matchedCount">0</span>
            <span> 篇符合條件貼文 ｜ 當前顯示第 </span>
            <span class="results-highlight" id="currentPageText">1</span>
            <span> / </span>
            <span id="totalPagesText">1</span>
            <span> 頁</span>
        </div>
        <div class="page-size-selector">
            <span>每頁顯示：</span>
            <select id="pageSizeSelect" onchange="setPageSize(this.value)">
                <option value="25" selected>25 篇</option>
                <option value="50">50 篇</option>
                <option value="100">100 篇</option>
            </select>
        </div>
    </div>

    <!-- 貼文卡片串流容器 -->
    <div class="posts-stream" id="postsContainer">
        <!-- 動態由 JavaScript 高效渲染 -->
    </div>

    <!-- 空數據狀態 -->
    <div class="empty-indicator" id="emptyState" style="display: none;">
        <span>🔍 沒有找到相符的貼文，請嘗試調整時光機年份、月份、專題標籤或搜尋關鍵字。</span>
    </div>

    <!-- 底部翻頁控制器 -->
    <div class="pagination-container" id="paginationBar">
        <!-- 動態生成分頁按鈕 -->
    </div>
</div>

<!-- 回到頂部按鈕 -->
<button class="back-to-top" id="backToTopBtn" onclick="scrollToTop()">↑</button>

<!-- 載入外部全量資料庫 (避免 CORS，支援本地 file:/// 直開) -->
<script src="feige_posts_data.js"></script>

<script>
    // 專題關鍵字規則庫
    const TOPIC_KEYWORDS = {
        signals: ['抄底', '逃顶', '逃頂', '跑得快', '5.7万', '5.7萬', '15万', '15萬', '20万', '20萬', '76000', '77000', '76200', '点位', '點位', '止损', '止損', '止盈', '挂单', '掛單', '买入', '買入', '出货', '出貨', '加仓', '加倉', '服不服', '最低点', '最低點'],
        macro: ['加息', '降息', '美联储', '美聯儲', '鲍威尔', '鮑威爾', '沃勒', '沃什', '通胀', '通脹', 'cpi', '非农', '非農', '大选', '大選', '牛市', '熊市', '2027', '周期', '週期', '宏观', '宏觀', '流动性', '流動性'],
        ai: ['tao', 'fet', 'virtual', 'near', 'kite', 'vvv', 'ai', 'agent', '人工智能', '算力'],
        l1: ['btc', 'eth', 'sol', 'sui', 'sei', 'tia', 'bnb', 'link', 'bera', '公链', '公鏈', '二线公链', '二線公鏈', '大饼', '大餅', '以太'],
        defi: ['uni', 'arb', 'hype', 'lit', 'aster', 'ena', 'xpl', 'crcl', 'pendle', 'defi', 'dex', 'perp', '衍生品', '协议收入', '協議收入', '分红', '分成', '回购', '回購', 'tvl', 'robinhood'],
        risk: ['手续费', '手續費', '返佣', '返傭', '磨损', '磨損', '本金', '定投', '滚仓', '滾倉', '仓位', '倉位', '风控', '風控', '爆仓', '爆倉', '杠杆', '槓桿']
    };

    let allPosts = window.FEIGE_DATABASE || [];
    let filteredPosts = [];
    let currentYear = 'ALL';
    let currentMonth = 'ALL';
    let currentTopic = 'all';
    let searchQuery = '';
    let currentPage = 1;
    let pageSize = 25;

    // 初始化
    window.addEventListener('DOMContentLoaded', () => {
        if (!allPosts || allPosts.length === 0) {
            document.getElementById('postsContainer').innerHTML = '<div class="empty-indicator">⚠️ 未檢測到 feige_posts_data.js 資料，請確認檔案路徑是否正確。</div>';
            return;
        }

        // 計算並填充頂部總數據
        calcGlobalStats();
        // 填充月份選單
        populateMonthSelect('ALL');
        // 綁定搜尋框監聽
        const searchInput = document.getElementById('searchInput');
        let searchTimer = null;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimer);
            const val = e.target.value;
            document.getElementById('clearSearchBtn').style.display = val ? 'block' : 'none';
            searchTimer = setTimeout(() => {
                searchQuery = val.toLowerCase().trim();
                currentPage = 1;
                applyFilters();
            }, 150);
        });

        // 初始套用過濾
        applyFilters();

        // 滾動回到頂部監聽
        window.addEventListener('scroll', () => {
            const btn = document.getElementById('backToTopBtn');
            if (window.scrollY > 400) {
                btn.classList.add('show');
            } else {
                btn.classList.remove('show');
            }
        });
    });

    function calcGlobalStats() {
        document.getElementById('statTotalPosts').innerText = allPosts.length.toLocaleString();
        let totalViews = 0;
        let totalLikes = 0;
        allPosts.forEach(p => {
            totalViews += (p.views || 0);
            totalLikes += (p.likes || 0);
        });
        document.getElementById('statTotalViews').innerText = (totalViews > 1000000) ? (totalViews / 1000000).toFixed(1) + 'M+' : totalViews.toLocaleString();
        document.getElementById('statTotalLikes').innerText = (totalLikes > 1000) ? (totalLikes / 1000).toFixed(1) + 'k+' : totalLikes.toLocaleString();
    }

    function setYear(year) {
        currentYear = year;
        currentMonth = 'ALL';
        currentPage = 1;

        // 更新按鈕樣式
        document.querySelectorAll('#yearBtnGroup .year-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-year') === year);
        });

        populateMonthSelect(year);
        applyFilters();
    }

    function setMonth(month) {
        currentMonth = month;
        currentPage = 1;
        applyFilters();
    }

    function populateMonthSelect(year) {
        const select = document.getElementById('monthSelect');
        select.innerHTML = '<option value="ALL">全部月份 (全年)</option>';

        const monthCounts = {};
        allPosts.forEach(p => {
            if (year === 'ALL' || p.year === year) {
                if (p.month) {
                    monthCounts[p.month] = (monthCounts[p.month] || 0) + 1;
                }
            }
        });

        const sortedMonths = Object.keys(monthCounts).sort().reverse();
        sortedMonths.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.innerText = `${m} (${monthCounts[m]}篇)`;
            select.appendChild(opt);
        });
        select.value = 'ALL';
    }

    function setTopic(topic) {
        currentTopic = topic;
        currentPage = 1;

        document.querySelectorAll('#topicRow .topic-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-topic') === topic);
        });

        applyFilters();
    }

    function clearSearch() {
        const input = document.getElementById('searchInput');
        input.value = '';
        document.getElementById('clearSearchBtn').style.display = 'none';
        searchQuery = '';
        currentPage = 1;
        applyFilters();
    }

    function setPageSize(size) {
        pageSize = parseInt(size, 10);
        currentPage = 1;
        renderPage();
    }

    function applyFilters() {
        filteredPosts = allPosts.filter(p => {
            // 年份過濾
            if (currentYear !== 'ALL' && p.year !== currentYear) return false;

            // 月份過濾
            if (currentMonth !== 'ALL' && p.month !== currentMonth) return false;

            // 專題標籤過濾
            if (currentTopic !== 'all') {
                const keywords = TOPIC_KEYWORDS[currentTopic] || [];
                const fullText = (p.body + ' ' + (p.title || '') + ' ' + (p.quote || '')).toLowerCase();
                const matched = keywords.some(k => fullText.includes(k.toLowerCase()));
                if (!matched) return false;
            }

            // 關鍵字全文字串檢索
            if (searchQuery) {
                const fullText = (p.body + ' ' + (p.title || '') + ' ' + (p.quote || '') + ' ' + (p.date || '') + ' ' + (p.id || '')).toLowerCase();
                // 交易對檢查
                const pairsText = (p.pairs || []).map(pr => (pr.name || '')).join(' ').toLowerCase();
                if (!fullText.includes(searchQuery) && !pairsText.includes(searchQuery)) {
                    return false;
                }
            }

            return true;
        });

        renderPage();
    }

    function renderPage() {
        const total = filteredPosts.length;
        const totalPages = Math.ceil(total / pageSize) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        document.getElementById('matchedCount').innerText = total.toLocaleString();
        document.getElementById('currentPageText').innerText = currentPage;
        document.getElementById('totalPagesText').innerText = totalPages;

        const container = document.getElementById('postsContainer');
        const emptyState = document.getElementById('emptyState');
        const paginationBar = document.getElementById('paginationBar');

        if (total === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            paginationBar.innerHTML = '';
            return;
        }

        emptyState.style.display = 'none';

        const startIndex = (currentPage - 1) * pageSize;
        const pageItems = filteredPosts.slice(startIndex, startIndex + pageSize);

        let html = '';
        pageItems.forEach(p => {
            html += generatePostCard(p);
        });
        container.innerHTML = html;

        renderPagination(totalPages);
    }

    function highlightText(text) {
        if (!searchQuery || !text) return escapeHtml(text);
        const escapedQuery = searchQuery.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return escapeHtml(text).replace(regex, '<mark class="hl">$1</mark>');
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function generatePostCard(p) {
        // Pairs chips
        let pairsHtml = '';
        if (p.pairs && p.pairs.length > 0) {
            pairsHtml += '<div class="pairs-bar">';
            p.pairs.forEach(pr => {
                const name = escapeHtml(pr.name);
                const rate = pr.rate || '';
                let rateClass = '';
                if (rate.startsWith('+')) rateClass = 'pair-up';
                else if (rate.startsWith('-')) rateClass = 'pair-down';
                pairsHtml += `<div class="pair-chip"><span>${name}</span> ${rate ? `<span class="${rateClass}">${rate}</span>` : ''}</div>`;
            });
            pairsHtml += '</div>';
        }

        // Quoted content
        let quoteHtml = '';
        if (p.quote) {
            quoteHtml = `
                <div class="quoted-box">
                    <div class="quoted-label">📌 引用歷史貼文或觀點：</div>
                    <div>${highlightText(p.quote)}</div>
                </div>
            `;
        }

        const titleHtml = p.title ? `<h2 class="post-title">${highlightText(p.title)}</h2>` : '';
        const bodyHtml = highlightText(p.body);

        const views = (p.views || 0).toLocaleString();
        const likes = (p.likes || 0).toLocaleString();
        const comments = (p.comments || 0).toLocaleString();

        return `
            <div class="post-card" id="card-${p.id}">
                <div class="post-top-row">
                    <div class="meta-badges">
                        <span class="badge-source">🌐 幣安官方原文</span>
                        <span class="post-date-tag">🕒 ${p.date || '未知時間'}</span>
                    </div>
                    <div class="post-id-tag">Post ID: ${p.id}</div>
                </div>
                ${titleHtml}
                <div class="content-box" id="content-${p.id}">${bodyHtml}</div>
                ${quoteHtml}
                ${pairsHtml}
                <div class="post-footer">
                    <div class="stats-group">
                        <span class="stat-entry">👁️ ${views} 次閱讀</span>
                        <span class="stat-entry">👍 ${likes} 點讚</span>
                        <span class="stat-entry">💬 ${comments} 留言</span>
                    </div>
                    <div class="action-group">
                        <button class="btn-action" onclick="copyPost('${p.id}', this)">📋 複製原文</button>
                        <a href="${p.url}" target="_blank" class="btn-action btn-link">🔗 幣安官方直達</a>
                    </div>
                </div>
            </div>
        `;
    }

    function renderPagination(totalPages) {
        const bar = document.getElementById('paginationBar');
        if (totalPages <= 1) {
            bar.innerHTML = '';
            return;
        }

        let html = '';
        // 第一頁
        html += `<button class="page-btn" onclick="goToPage(1)" ${currentPage === 1 ? 'disabled' : ''}>|&lt;</button>`;
        // 上一頁
        html += `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>&lt; 上一頁</button>`;

        // 頁碼動態區間
        const delta = 2;
        const left = Math.max(1, currentPage - delta);
        const right = Math.min(totalPages, currentPage + delta);

        if (left > 1) {
            html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
            if (left > 2) html += `<span class="page-ellipsis">...</span>`;
        }

        for (let i = left; i <= right; i++) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
        }

        if (right < totalPages) {
            if (right < totalPages - 1) html += `<span class="page-ellipsis">...</span>`;
            html += `<button class="page-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`;
        }

        // 下一頁
        html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>下一頁 &gt;</button>`;
        // 最後一頁
        html += `<button class="page-btn" onclick="goToPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>&gt;|</button>`;

        bar.innerHTML = html;
    }

    function goToPage(page) {
        currentPage = page;
        renderPage();
        scrollToTop();
    }

    function scrollToTop() {
        window.scrollTo({
            top: document.querySelector('.controls-card').offsetTop - 20,
            behavior: 'smooth'
        });
    }

    function copyPost(id, btn) {
        const p = allPosts.find(item => item.id === id);
        if (!p) return;
        const fullContent = (p.title ? p.title + '\\n\\n' : '') + p.body + (p.quote ? '\\n\\n[引用] ' + p.quote : '');
        navigator.clipboard.writeText(fullContent).then(() => {
            const orig = btn.innerText;
            btn.innerText = '✅ 已複製！';
            btn.style.borderColor = '#2ebd85';
            btn.style.color = '#2ebd85';
            setTimeout(() => {
                btn.innerText = orig;
                btn.style.borderColor = '';
                btn.style.color = '';
            }, 1800);
        }).catch(err => {
            alert('複製失敗，請手動選取文字');
        });
    }
</script>

</body>
</html>
'''

with open('feige_posts.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("feige_posts.html updated successfully!")
