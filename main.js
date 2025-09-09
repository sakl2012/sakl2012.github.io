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

    // --- NEW: 更新導覽列 Active 狀態的函式 ---
    function updateActiveNavLink() {
        // 延遲一小段時間執行，確保所有元素都已渲染完畢
        setTimeout(() => {
            const currentPagePath = window.location.pathname.split('/').pop();
            const navLinks = document.querySelectorAll('#navbarCollapse .nav-link');

            navLinks.forEach(link => {
                const linkPath = link.getAttribute('href');
                if (linkPath === currentPagePath || (currentPagePath === '' && linkPath === 'index.html')) {
                    link.classList.add('active');
                    link.setAttribute('aria-current', 'page'); 
                }
            });
        }, 100); // 延遲 100 毫秒
    }


    // --- Page Functionality (保持不變) ---
    document.querySelectorAll('.back-to-top, .lnk').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            let targetY = 0;
            if (targetId) {
                const navbarHeight = document.getElementById('includeNavbar') ? document.getElementById('includeNavbar').offsetHeight : 0;
                targetY = window.scrollY + document.getElementById(targetId).getBoundingClientRect().top - navbarHeight - 10;
            }
            smoothScroll(targetY, 400);
        });
    });

    window.addEventListener('scroll', () => {
    const isScrolled = window.scrollY > 10;

    document.querySelectorAll('.back-to-top, .lnk').forEach(btn => {
        if (isScrolled) {
            btn.classList.add('show');
        } else {
            btn.classList.remove('show');
        }
    });
});

    // --- Dynamic Content Loader (保持不變) ---
    const CACHE_KEY = 'googleSheetsData';
    const CACHE_EXPIRY_MS = 60 * 60 * 1000;

    const pageLoaders = {
        'includeSidebar': 'HTML!A2',
        'includeNavbar': 'HTML!B2',
        'info': 'HTML!E2',
        'about': 'HTML!D2',
        'publications': 'HTML!C2',
    };

    const renderContent = (data) => {
        Object.keys(pageLoaders).forEach((id, index) => {
            const container = document.getElementById(id);
            if (container) {
                const content = data.valueRanges[index]?.values?.[0]?.[0] || 'Content not found.';
                container.innerHTML = content;
            }
        });
        // --- KEY CHANGE: 在這裡呼叫更新函式 ---
        // 確保內容 (包含導覽列) 都被渲染到頁面後，才執行 active 狀態的更新
        updateActiveNavLink();
    };

    const loadSpreadsheetsWithCache = () => {
        const cachedData = localStorage.getItem(CACHE_KEY);
        const cachedTimestamp = localStorage.getItem(`${CACHE_KEY}_timestamp`);

        if (cachedData && cachedTimestamp && (Date.now() - parseInt(cachedTimestamp, 10)) < CACHE_EXPIRY_MS) {
            console.log('載入自快取...');
            renderContent(JSON.parse(cachedData));
            return;
        }

        console.log('從網路獲取新資料...');
        
        fetch(`https://sheets.googleapis.com/v4/spreadsheets/1EsbqSfOS97txN7_nwxpujdkV3g6scHB24TSAaJ25AMo/values:batchGet?ranges=${Object.values(pageLoaders).join('&ranges=')}&key=AIzaSyD8sJOgRFmGvQ6T5X-PjwVfpEsb8pG2y2o`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('網路響應不佳或 API 金鑰無效');
                }
                return response.json();
            })
            .then(data => {
                localStorage.setItem(CACHE_KEY, JSON.stringify(data));
                localStorage.setItem(`${CACHE_KEY}_timestamp`, Date.now().toString());
                renderContent(data);
            })
            .catch(error => {
                console.error('從 Google Sheets 獲取資料時發生錯誤：', error);
                Object.keys(pageLoaders).forEach(id => {
                    const container = document.getElementById(id);
                    if (container) {
                        container.innerHTML = '無法載入內容。請稍後再試。';
                    }
                });
            });
    };

    document.addEventListener('DOMContentLoaded', loadSpreadsheetsWithCache);

})();