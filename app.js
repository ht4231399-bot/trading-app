const tradingPairs = [
    { symbol: 'EUR/USD', bid: 1.0850, ask: 1.0851, change24h: 0.25, type: 'forex' },
    { symbol: 'GBP/USD', bid: 1.2650, ask: 1.2651, change24h: 0.15, type: 'forex' },
    { symbol: 'USD/JPY', bid: 149.50, ask: 149.52, change24h: -0.35, type: 'forex' },
    { symbol: 'AUD/USD', bid: 0.6580, ask: 0.6581, change24h: 0.50, type: 'forex' },
    { symbol: 'USD/CHF', bid: 0.8910, ask: 0.8911, change24h: -0.10, type: 'forex' },
    { symbol: 'NZD/USD', bid: 0.6020, ask: 0.6021, change24h: 0.30, type: 'forex' },
    { symbol: 'BTC/USD', bid: 62500, ask: 62505, change24h: 2.50, type: 'crypto' },
    { symbol: 'ETH/USD', bid: 2450, ask: 2451, change24h: 1.85, type: 'crypto' },
    { symbol: 'BNB/USD', bid: 620, ask: 621, change24h: 0.95, type: 'crypto' },
    { symbol: 'ADA/USD', bid: 0.98, ask: 0.99, change24h: 3.20, type: 'crypto' },
    { symbol: 'SOL/USD', bid: 195.50, ask: 195.80, change24h: 1.45, type: 'crypto' }
];

let watchlist = JSON.parse(localStorage.getItem('watchlist')) || [];
let currentFilter = 'all';
let lastUpdateTime = new Date();

document.addEventListener('DOMContentLoaded', () => {
    renderRates();
    updateStats();
    setupEventListeners();
    setInterval(() => {
        updateRates();
        lastUpdateTime = new Date();
        document.getElementById('lastUpdate').textContent = lastUpdateTime.toLocaleTimeString();
    }, 30000);
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
        const matchesSearch = pair.symbol.toLowerCase().includes(search);
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

        return `
            <div class="rate-card">
                <div class="rate-header">
                    <div>
                        <div class="pair-name">${pair.symbol}</div>
                        <span class="pair-type">${pair.type.toUpperCase()}</span>
                    </div>
                    <button class="watchlist-star ${isInWatchlist ? 'active' : ''}" 
                            onclick="toggleWatchlist('${pair.symbol}')">★</button>
                </div>
                <div class="rate-value">${pair.ask.toFixed(2)}</div>
                <div class="rate-change">
                    <div class="change-item">
                        <div class="change-label">Bid</div>
                        <div class="change-value">${pair.bid.toFixed(2)}</div>
                    </div>
                    <div class="change-item">
                        <div class="change-label">Ask</div>
                        <div class="change-value">${pair.ask.toFixed(2)}</div>
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
            return `
                <div class="watchlist-item">
                    <div class="watchlist-item-info">
                        <div class="watchlist-item-name">${pair.symbol}</div>
                        <div class="watchlist-item-rate">${pair.ask.toFixed(2)}</div>
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
        pair.bid += (Math.random() - 0.5) * pair.bid * 0.001;
        pair.ask = pair.bid + (Math.random() * 0.0001);
        pair.change24h += (Math.random() - 0.5) * 0.1;
    });
    renderRates();
}

function updateStats() {
    document.getElementById('totalPairs').textContent = tradingPairs.length;
    document.getElementById('watchlistCount').textContent = watchlist.length;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}