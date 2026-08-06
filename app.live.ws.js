// (rest of app.js left as-is earlier) 
// Add WebSocket client to receive live tickers and update in-memory tradingPairs

(function(){
    // attempt to connect to WebSocket server serving live rates
    const WS_HOST = window.location.hostname || 'localhost';
    const WS_PORT = 8765;
    const WS_URL = `ws://${WS_HOST}:${WS_PORT}`;

    let ws = null;
    let wsReconnectDelay = 1000;

    function connectLiveRates() {
        try {
            ws = new WebSocket(WS_URL);
        } catch (e) {
            console.warn('Live rates websocket connection failed to initialize', e);
            scheduleReconnect();
            return;
        }

        ws.addEventListener('open', () => {
            console.info('Connected to live rates:', WS_URL);
            wsReconnectDelay = 1000;
        });

        ws.addEventListener('message', (ev) => {
            try {
                const msg = JSON.parse(ev.data);
                if (msg.type === 'tickers' && Array.isArray(msg.data)) {
                    msg.data.forEach(u => {
                        const idx = tradingPairs.findIndex(p => p.symbol === u.symbol || p.symbol.replace('/', '/') === u.symbol);
                        if (idx > -1) {
                            const p = tradingPairs[idx];
                            // parse and quantize to pair.tick
                            const tick = p.tick || parseFloat(u.tick) || 0.01;
                            // Use small epsilon to avoid float rounding pitfalls
                            const bid = Math.floor((parseFloat(u.bid) + 1e-12) / tick) * tick;
                            const ask = Math.floor((parseFloat(u.ask) + 1e-12) / tick) * tick + (p.spread || 0);
                            p.bid = bid;
                            p.ask = ask;
                            // update 24h change roughly if you want — keep existing change24h or compute relative to mid
                            const oldMid = (p.bid + p.ask) / 2;
                            const newMid = (bid + ask) / 2;
                            // small smoothing to avoid jarring UI
                            p.change24h = ((newMid - oldMid) / (oldMid || newMid)) * 100;
                        }
                    });
                    renderRates();
                }
            } catch (e) {
                console.warn('Failed to parse live rates message', e);
            }
        });

        ws.addEventListener('close', (ev) => {
            console.warn('Live rates websocket closed', ev);
            scheduleReconnect();
        });

        ws.addEventListener('error', (ev) => {
            console.error('Live rates websocket error', ev);
            ws.close();
        });
    }

    function scheduleReconnect() {
        setTimeout(() => {
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
            connectLiveRates();
        }, wsReconnectDelay);
    }

    // start connection after DOM loads
    document.addEventListener('DOMContentLoaded', () => {
        connectLiveRates();
    });
})();
