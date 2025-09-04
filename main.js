(function () {
    "use strict";

    // --- Core Functions (保持不變) ---
    function easeInOutQuad(t) {
        return t * (2 - t);
    }

    function smoothScroll(targetY, duration) {
        const startY = window.scrollY || document.documentElement.scrollTop;
        let start;
        window.requestAnimationFrame(function step(timestamp) {
            if (!start) start = timestamp;
            const progress = Math.min((timestamp - start) / duration, 1);
            window.scrollTo(0, startY + (targetY - startY) * easeInOutQuad(progress));
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        });
    }

    // --- Page Functionality (保持不變) ---
    document.querySelectorAll('.back-to-top, .lnk').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            let targetY = 0;
            if (targetId) {
                targetY = window.scrollY + document.getElementById(targetId).getBoundingClientRect().top - document.getElementById('includeNavbar').offsetHeight + 20;
            }
            smoothScroll(targetY, 400);
        });
    });

    window.addEventListener('scroll', () => {
        document.querySelectorAll('.back-to-top, .lnk').forEach(btn => {
            btn.style.display = (window.scrollY > 50 ? 'block' : 'none');
        });
    });

    // --- Dynamic Content Loader (優化後的新版本) ---

    // 設定快取相關的參數
    const CACHE_KEY = 'googleSheetsData';
    const CACHE_EXPIRY_MS = 60 * 60 * 1000; // 快取 1 小時

    // 定義所有需要載入的 HTML 區塊及其對應的試算表範圍
    const pageLoaders = {
        'includeSidebar': 'HTML!A2',
        'includeNavbar': 'HTML!B2',
        'info': 'HTML!E2',
        'about': 'HTML!D2',
        'publications': 'HTML!C2',
    };

    /**
     * 將取得的資料渲染到對應的 HTML 容器中
     * @param {object} data - 從 API 獲取的資料
     */
    const renderContent = (data) => {
        // 遍歷 pageLoaders 字典，將內容渲染到對應的 ID
        Object.keys(pageLoaders).forEach((id, index) => {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = data.valueRanges[index] && data.valueRanges[index].values && data.valueRanges[index].values.length > 0 ? data.valueRanges[index].values[0][0] : 'Content not found.';
            }
        });
    };

    /**
     * 檢查快取，如果無效則發出新的 API 請求
     */
    const loadSpreadsheetsWithCache = () => {
        const cachedData = localStorage.getItem(CACHE_KEY);
        const cachedTimestamp = localStorage.getItem(`${CACHE_KEY}_timestamp`);

        // 檢查快取是否存在且未過期
        if (cachedData && cachedTimestamp && (Date.now() - parseInt(cachedTimestamp, 10)) < CACHE_EXPIRY_MS) {
            console.log('載入自快取...');
            renderContent(JSON.parse(cachedData));
            return;
        }

        // 快取無效或不存在，從網路獲取資料
        console.log('從網路獲取新資料...');
        
        fetch(`https://sheets.googleapis.com/v4/spreadsheets/1EsbqSfOS97txN7_nwxpujdkV3g6scHB24TSAaJ25AMo/values:batchGet?ranges=${Object.values(pageLoaders).join('&ranges=')}&key=AIzaSyD8sJOgRFmGvQ6T5X-PjwVfpEsb8pG2y2o`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('網路響應不佳或 API 金鑰無效');
                }
                return response.json();
            })
            .then(data => {
                // 將資料存入快取並記錄時間戳
                localStorage.setItem(CACHE_KEY, JSON.stringify(data));
                localStorage.setItem(`${CACHE_KEY}_timestamp`, Date.now().toString());
                renderContent(data);
            })
            .catch(error => {
                console.error('從 Google Sheets 獲取資料時發生錯誤：', error);
                // 顯示錯誤訊息
                Object.keys(pageLoaders).forEach(id => {
                    const container = document.getElementById(id);
                    if (container) {
                        container.innerHTML = '無法載入內容。請稍後再試。';
                    }
                });
            });
    };

    // 在 DOMContentLoaded 事件中調用主載入函數
    document.addEventListener('DOMContentLoaded', loadSpreadsheetsWithCache);

})();