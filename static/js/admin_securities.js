var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { MaintenanceActivityManager } from './maintenance_activity.js';
class SecuritiesManager extends MaintenanceActivityManager {
    constructor(metadata) {
        super(metadata);
        this.lookupModal = document.getElementById('lookup-modal');
        this.lookupResultsList = document.getElementById('lookup-results-list');
        this.lookupResultsCount = document.getElementById('lookup-results-count');
        this.lookupSearchInput = document.getElementById('lookup-search-input');
        this.btnLookupSearch = document.getElementById('btn-lookup-search');
        this.btnCloseLookup = document.getElementById('btn-close-lookup');
        this.btnOkLookup = document.getElementById('btn-ok-lookup');
        this.selectedLookupSymbol = null;
        this.initSecuritiesListeners();
    }
    initSecuritiesListeners() {
        var _a, _b, _c, _d;
        const lookupButtons = document.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openLookupDialog();
            });
        });
        (_a = this.btnLookupSearch) === null || _a === void 0 ? void 0 : _a.addEventListener('click', () => this.handleLookup());
        (_b = this.btnCloseLookup) === null || _b === void 0 ? void 0 : _b.addEventListener('click', () => {
            this.lookupModal.style.display = 'none';
        });
        (_c = this.btnOkLookup) === null || _c === void 0 ? void 0 : _c.addEventListener('click', () => {
            if (this.selectedLookupSymbol) {
                this.fetchMetadata(this.selectedLookupSymbol);
                this.lookupModal.style.display = 'none';
            }
        });
        // Refresh button listener
        const refreshButtons = document.querySelectorAll('.btn-refresh-field');
        refreshButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.refreshPrice();
            });
        });
        // Allow Enter key in lookup search
        (_d = this.lookupSearchInput) === null || _d === void 0 ? void 0 : _d.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLookup();
            }
        });
    }
    // Auto-fetch price when row selected
    selectRow(row) {
        super.selectRow(row);
        if (this.selectedRow) {
            this.refreshPrice(true); // silent=true for auto-fetch
        }
    }
    refreshPrice() {
        return __awaiter(this, arguments, void 0, function* (silent = false) {
            const symbolInput = document.getElementById('field-symbol');
            const symbol = symbolInput === null || symbolInput === void 0 ? void 0 : symbolInput.value;
            if (!symbol)
                return;
            try {
                if (!silent)
                    this.showMessage(`Refreshing price for ${symbol}...`);
                const resp = yield fetch(`/admin/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
                if (resp.ok) {
                    const data = yield resp.json();
                    const priceInput = document.getElementById('field-current_price');
                    if (priceInput && data.current_price) {
                        priceInput.value = data.current_price;
                        if (!silent)
                            this.showMessage(`Updated price for ${symbol}: ${data.current_price}`);
                        this.checkDirty();
                    }
                }
            }
            catch (err) {
                if (!silent)
                    this.showMessage(`Failed to refresh price for ${symbol}`, true);
            }
        });
    }
    openLookupDialog() {
        var _a;
        const symbolInput = document.getElementById('field-symbol');
        if (this.lookupSearchInput && symbolInput) {
            this.lookupSearchInput.value = symbolInput.value;
        }
        if (this.lookupResultsList) {
            this.lookupResultsList.innerHTML = '';
        }
        if (this.lookupResultsCount) {
            this.lookupResultsCount.textContent = '';
        }
        this.selectedLookupSymbol = null;
        if (this.btnOkLookup)
            this.btnOkLookup.disabled = true;
        if (this.lookupModal) {
            this.lookupModal.style.display = 'flex';
            (_a = this.lookupSearchInput) === null || _a === void 0 ? void 0 : _a.focus();
        }
    }
    handleLookup() {
        return __awaiter(this, void 0, void 0, function* () {
            var _a;
            let query = (_a = this.lookupSearchInput) === null || _a === void 0 ? void 0 : _a.value.trim();
            if (!query) {
                alert("Please enter a symbol or name to lookup.");
                return;
            }
            try {
                this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px;">Searching...</td></tr>';
                this.lookupResultsCount.textContent = '';
                this.selectedLookupSymbol = null;
                if (this.btnOkLookup)
                    this.btnOkLookup.disabled = true;
                // Exact match first
                let results = yield this.performSearch(query);
                // If no records, then starts with search
                if (results.length === 0 && !query.endsWith('*')) {
                    results = yield this.performSearch(query + '*');
                }
                this.showLookupResults(results);
            }
            catch (err) {
                if (err.message.includes("429") || err.message.includes("Rate limited")) {
                    this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px; color: #c00;">Error: Too many requests. Yahoo Finance is rate-limiting our search. Please try again later.</td></tr>';
                }
                else {
                    this.lookupResultsList.innerHTML = `<tr><td colspan="2" style="padding: 15px; color: #c00;">Error searching for security: ${err.message}</td></tr>`;
                }
            }
        });
    }
    performSearch(q) {
        return __awaiter(this, void 0, void 0, function* () {
            const resp = yield fetch(`/admin/securities/search?q=${encodeURIComponent(q)}`);
            if (resp.status === 429) {
                throw new Error("Rate limited");
            }
            if (!resp.ok) {
                throw new Error(`Search failed with status ${resp.status}`);
            }
            return yield resp.json();
        });
    }
    showLookupResults(results) {
        this.lookupResultsList.innerHTML = '';
        if (this.lookupResultsCount) {
            this.lookupResultsCount.textContent = `Found ${results.length} record(s)`;
        }
        if (results.length === 0) {
            this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px;">No results found.</td></tr>';
        }
        else {
            results.forEach(res => {
                const tr = document.createElement('tr');
                tr.className = 'lookup-result-row';
                tr.innerHTML = `
                    <td><strong>${res.symbol}</strong></td>
                    <td>${res.name || ''}</td>
                `;
                // Single click to select
                tr.addEventListener('click', () => {
                    document.querySelectorAll('.lookup-result-row').forEach(r => r.classList.remove('selected'));
                    tr.classList.add('selected');
                    this.selectedLookupSymbol = res.symbol;
                    if (this.btnOkLookup)
                        this.btnOkLookup.disabled = false;
                });
                // Double click to apply
                tr.addEventListener('dblclick', () => {
                    this.fetchMetadata(res.symbol);
                    this.lookupModal.style.display = 'none';
                });
                this.lookupResultsList.appendChild(tr);
            });
        }
    }
    fetchMetadata(symbol) {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                this.showMessage(`Fetching metadata for ${symbol}...`);
                const resp = yield fetch(`/admin/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
                if (!resp.ok) {
                    if (resp.status === 404) {
                        throw new Error(`Security details for '${symbol}' not found on Yahoo Finance.`);
                    }
                    throw new Error(`Lookup failed with status ${resp.status}`);
                }
                const data = yield resp.json();
                this.populateFormWithMetadata(data);
                this.showMessage(`Successfully loaded ${symbol}`);
            }
            catch (err) {
                this.showMessage(err.message || "Error fetching security metadata.", true);
            }
        });
    }
    populateFormWithMetadata(data) {
        const mapping = {
            'symbol': data.symbol,
            'name': data.name,
            'security_type': data.security_type,
            'asset_class': data.asset_class,
            'previous_close': data.previous_close,
            'open_price': data.open_price,
            'current_price': data.current_price,
            'nav': data.nav,
            'range_52_week': data.range_52_week,
            'avg_volume': data.avg_volume,
            'yield_30_day': data.yield_30_day,
            'yield_7_day': data.yield_7_day
        };
        Object.keys(mapping).forEach(key => {
            const input = document.getElementById(`field-${key}`);
            if (input && mapping[key] !== undefined) {
                // Special handling for yields to format as percentages
                if (key.startsWith('yield_') && mapping[key]) {
                    const num = parseFloat(mapping[key]);
                    if (!isNaN(num)) {
                        input.value = (num * 100).toFixed(2) + '%';
                    }
                    else {
                        input.value = mapping[key];
                    }
                }
                else {
                    input.value = mapping[key] || '';
                }
            }
        });
        this.checkDirty();
    }
    getCreateUrl() { return "/admin/securities/create"; }
    getUpdateUrl(id) { return `/admin/securities/update/${id}`; }
    getDeleteUrl(id) { return `/admin/securities/delete/${id}`; }
}
document.addEventListener('DOMContentLoaded', () => {
    const metadataElement = document.getElementById('metadata-json');
    if (metadataElement) {
        const metadata = JSON.parse(metadataElement.textContent || '{}');
        new SecuritiesManager(metadata);
    }
});
