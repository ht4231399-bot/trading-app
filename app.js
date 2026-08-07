const tradingPairs = [
    // Forex
    { symbol: 'EUR/USD', bid: 1.08500, ask: 1.08520, title: 'EUR/USD', change24h: 0.25, type: 'forex', spread: 0.00020, tick: 0.00001, decimals: 5, tv_symbol: 'FX_IDC:EURUSD' },
    { symbol: 'GBP/USD', bid: 1.27500, ask: 1.27520, title: 'GBP/USD', change24h: 0.15, type: 'forex', spread: 0.00020, tick: 0.00001, decimals: 5, tv_symbol: 'FX_IDC:GBPUSD' },
    { symbol: 'USD/JPY', bid: 151.25, ask: 151.30, title: 'USD/JPY', change24h: -0.35, type: 'forex', spread: 0.05, tick: 0.01, decimals: 2, tv_symbol: 'FX_IDC:USDJPY' },
    { symbol: 'AUD/USD', bid: 0.66800, ask: 0.66820, title: 'AUD/USD', change24h: 0.50, type: 'forex', spread: 0.00020, tick: 0.00001, decimals: 5, tv_symbol: 'FX_IDC:AUDUSD' },
    { symbol: 'USD/CHF', bid: 0.89500, ask: 0.89520, title: 'USD/CHF', change24h: -0.10, type: 'forex', spread: 0.00020, tick: 0.00001, decimals: 5, tv_symbol: 'FX_IDC:USDCHF' },
    { symbol: 'NZD/USD', bid: 0.61200, ask: 0.61220, title: 'NZD/USD', change24h: 0.30, type: 'forex', spread: 0.00020, tick: 0.00001, decimals: 5, tv_symbol: 'FX_IDC:NZDUSD' },

    // Crypto (Binance symbols for TradingView mapping)
    { symbol: 'BTC/USDT', bid: 67500.00, ask: 67520.00, title: 'BTC/USDT', change24h: 2.50, type: 'crypto', spread: 20.00, tick: 0.01, decimals: 2, tv_symbol: 'BINANCE:BTCUSDT' },
    { symbol: 'ETH/USDT', bid: 3500.00, ask: 3510.00, title: 'ETH/USDT', change24h: 1.85, type: 'crypto', spread: 10.00, tick: 0.01, decimals: 2, tv_symbol: 'BINANCE:ETHUSDT' },
    { symbol: 'BNB/USDT', bid: 720.00, ask: 725.00, title: 'BNB/USDT', change24h: 0.95, type: 'crypto', spread: 5.00, tick: 0.01, decimals: 2, tv_symbol: 'BINANCE:BNBUSDT' },
    { symbol: 'ADA/USDT', bid: 1.1500, ask: 1.1600, title: 'ADA/USDT', change24h: 3.20, type: 'crypto', spread: 0.0100, tick: 0.0001, decimals: 4, tv_symbol: 'BINANCE:ADAUSDT' },
    { symbol: 'SOL/USDT', bid: 225.00, ask: 227.00, title: 'SOL/USDT', change24h: 1.45, type: 'crypto', spread: 2.00, tick: 0.01, decimals: 2, tv_symbol: 'BINANCE:SOLUSDT' },

    // Commodities (display-only mapping to TradingView symbols)
    { symbol: 'XAU/USD', market_symbol: 'XAUUSD', tv_symbol: 'OANDA:XAUUSD', title: 'Gold (XAU/USD)', type: 'commodity', bid: 1950.00, ask: 1950.10, spread: 0.10, tick: 0.01, decimals: 2 },
    { symbol: 'XAG/USD', market_symbol: 'XAGUSD', tv_symbol: 'OANDA:XAGUSD', title: 'Silver (XAG/USD)', type: 'commodity', bid: 23.50, ask: 23.52, spread: 0.02, tick: 0.01, decimals: 2 },
    { symbol: 'CL=F', market_symbol: 'CL1!', tv_symbol: 'NYMEX:CL1!', title: 'Crude Oil (WTI)', type: 'commodity', bid: 80.25, ask: 80.30, spread: 0.05, tick: 0.01, decimals: 2 },
    { symbol: 'NG=F', market_symbol: 'NG1!', tv_symbol: 'NYMEX:NG1!', title: 'Natural Gas (NG)', type: 'commodity', bid: 2.30, ask: 2.31, spread: 0.01, tick: 0.001, decimals: 3 },
    { symbol: 'HG', market_symbol: 'HG1!', tv_symbol: 'COMEX:HG1!', title: 'Copper (HG)', type: 'commodity', bid: 4.10, ask: 4.12, spread: 0.02, tick: 0.01, decimals: 2 },

    // Stocks / Companies
    { symbol: 'NEM', market_symbol: 'NEM', tv_symbol: 'NYSE:NEM', title: 'Newmont (NEM)', type: 'stock', bid: 40.50, ask: 40.52, spread: 0.02, tick: 0.01, decimals: 2 },
    { symbol: 'GOLD', market_symbol: 'GOLD', tv_symbol: 'NYSE:GOLD', title: 'Barrick (GOLD)', type: 'stock', bid: 18.20, ask: 18.22, spread: 0.02, tick: 0.01, decimals: 2 },
    { symbol: 'XOM', market_symbol: 'XOM', tv_symbol: 'NYSE:XOM', title: 'Exxon Mobil (XOM)', type: 'stock', bid: 112.50, ask: 112.55, spread: 0.05, tick: 0.01, decimals: 2 },
    { symbol: 'CVX', market_symbol: 'CVX', tv_symbol: 'NYSE:CVX', title: 'Chevron (CVX)', type: 'stock', bid: 170.00, ask: 170.05, spread: 0.05, tick: 0.01, decimals: 2 },
    { symbol: 'BHP', market_symbol: 'BHP', tv_symbol: 'LON:BHP', title: 'BHP Group (BHP)', type: 'stock', bid: 40.00, ask: 40.05, spread: 0.05, tick: 0.01, decimals: 2 },
    { symbol: 'RIO', market_symbol: 'RIO', tv_symbol: 'LON:RIO', title: 'Rio Tinto (RIO)', type: 'stock', bid: 85.00, ask: 85.10, spread: 0.10, tick: 0.01, decimals: 2 }
];

let watchlist = JSON.parse(localStorage.getItem('watchlist')) || [];
let currentFilter = 'all';
let lastUpdateTime = new Date();

// Quantize helper: snap value down to nearest multiple of tick
function quantize(value, tick) {
    if (!isFinite(value) || !isFinite(tick) || tick === 0) return value;
    // Use integer math where possible to avoid tiny floating errors
    const units = Math.floor(value / tick + 1e-12); // small epsilon to handle floating edge cases
    return units * tick;
}

// Format number safely using specified decimals
function fmt(value, decimals) {
    return Number(value).toFixed(decimals);
}

function initPair(pair) {
    // Ensure bid/ask align with ticks and spread
    pair.bid = quantize(pair.bid, pair.tick);
    pair.ask = quantize(pair.bid + pair.spread, pair.tick);
}

tradingPairs.forEach(initPair);

document.addEventListener('DOMContentLoaded', () => {
    renderRates();
    updateStats();
    setupEventListeners();
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
    setInterval(() => {
        updateRates();
        lastUpdateTime = new Date();
        document.getElementById('lastUpdate').textContent = lastUpdateTime.toLocaleTimeString();
    }, 2000);
});

function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', (e) => {
        filterRates(e.target.value);
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderRates();
        });
    });

    document.getElementById('watchlistBtn').addEventListener('click', showWatchlist);
    document.getElementById('closeWatchlist').addEventListener('click', closeWatchlist);
    document.getElementById('modalOverlay').addEventListener('click', closeWatchlist);
}

function renderRates() {
    const grid = document.getElementById('ratesGrid');
    const search = document.getElementById('searchInput').value.toLowerCase();
    
    const filtered = tradingPairs.filter(pair => {
        const matchesFilter = currentFilter === 'all' || pair.type === currentFilter;
        const matchesSearch = pair.symbol.toLowerCase().includes(search) || (pair.title && pair.title.toLowerCase().includes(search));
        return matchesFilter && matchesSearch;
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-message">No trading pairs found</div>';
        return;
    }

    grid.innerHTML = filtered.map(pair => {
        const isInWatchlist = watchlist.includes(pair.symbol);
        const changeClass = pair.change24h >= 0 ? 'positive' : 'negative';
        const changeSymbol = pair.change24h >= 0 ? '▲' : '▼';
        const mid = quantize((pair.bid + pair.ask) / 2, pair.tick);

        return `
            <div class="rate-card">
                <div class="rate-header">
                    <div>
                        <div class="pair-name">${pair.title || pair.symbol}</div>
                        <span class="pair-type">${pair.type.toUpperCase()}</span>
                    </div>
                    <button class="watchlist-star ${isInWatchlist ? 'active' : ''}" 
                            onclick="toggleWatchlist('${pair.symbol}')">★</button>
                </div>
                <div class="rate-value">${fmt(mid, pair.decimals)}</div>
                <div class="rate-change">
                    <div class="change-item">
                        <div class="change-label">Bid</div>
                        <div class="change-value">${fmt(pair.bid, pair.decimals)}</div>
                    </div>
                    <div class="change-item">
                        <div class="change-label">Ask</div>
                        <div class="change-value">${fmt(pair.ask, pair.decimals)}</div>
                    </div>
                    <div class="change-item">
                        <div class="change-label">24h Change</div>
                        <div class="change-value ${changeClass}">${changeSymbol} ${Math.abs(pair.change24h).toFixed(2)}%</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function filterRates(search) {
    renderRates();
}

function toggleWatchlist(symbol) {
    const index = watchlist.indexOf(symbol);
    if (index > -1) {
        watchlist.splice(index, 1);
    } else {
        watchlist.push(symbol);
    }
    localStorage.setItem('watchlist', JSON.stringify(watchlist));
    updateStats();
    renderRates();
}

function showWatchlist() {
    const modal = document.getElementById('watchlistModal');
    const content = document.getElementById('watchlistContent');

    if (watchlist.length === 0) {
        content.innerHTML = '<div class="empty-message">Your watchlist is empty. Add some trading pairs!</div>';
    } else {
        const watchlistItems = tradingPairs.filter(p => watchlist.includes(p.symbol));
        content.innerHTML = watchlistItems.map(pair => {
            const changeClass = pair.change24h >= 0 ? 'positive' : 'negative';
            const changeSymbol = pair.change24h >= 0 ? '▲' : '▼';
            const mid = quantize((pair.bid + pair.ask) / 2, pair.tick);
            return `
                <div class="watchlist-item">
                    <div class="watchlist-item-info">
                        <div class="watchlist-item-name">${pair.title || pair.symbol}</div>
                        <div class="watchlist-item-rate">${fmt(mid, pair.decimals)}</div>
                    </div>
                    <div class="${changeClass}">${changeSymbol} ${Math.abs(pair.change24h).toFixed(2)}%</div>
                    <button class="remove-btn" onclick="toggleWatchlist('${pair.symbol}')">Remove</button>
                </div>
            `;
        }).join('');
    }

    modal.classList.add('show');
    document.getElementById('modalOverlay').classList.add('show');
}

function closeWatchlist() {
    document.getElementById('watchlistModal').classList.remove('show');
    document.getElementById('modalOverlay').classList.remove('show');
}

function updateRates() {
    tradingPairs.forEach(pair => {
        // Volatility expressed in "ticks" to ensure discrete, quantized updates
        const maxTicks = pair.volatilityTicks || (pair.type === 'crypto' ? 50 : 6);
        // Choose a random integer number of ticks to move (can be negative)
        const ticks = Math.floor((Math.random() - 0.5) * 2 * maxTicks);
        const movement = ticks * pair.tick;

        let newBid = quantize(pair.bid + movement, pair.tick);
        // Prevent negative or zero prices
        if (newBid <= 0) newBid = quantize(Math.abs(pair.bid) + pair.tick, pair.tick);

        pair.bid = newBid;
        // Maintain spread but quantize ask as well
        pair.ask = quantize(pair.bid + pair.spread, pair.tick);

        // Small random change in 24h percentage (keep it smooth)
        pair.change24h += (Math.random() - 0.5) * 0.05;
    });
    renderRates();
}

function updateStats() {
    document.getElementById('totalPairs').textContent = tradingPairs.length;
    document.getElementById('watchlistCount').textContent = watchlist.length;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}
