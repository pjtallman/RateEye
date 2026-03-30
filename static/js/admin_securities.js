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
        this.initLookupListeners();
    }
    initLookupListeners() {
        var _a, _b, _c;
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
        // Allow Enter key in lookup search
        (_c = this.lookupSearchInput) === null || _c === void 0 ? void 0 : _c.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLookup();
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
                // Requirement (1): Exact match first
                let results = yield this.performSearch(query);
                // Requirement (1): If no records, then starts with search
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
        // Display count of matching records
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
                tr.addEventListener('click', () => {
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
                input.value = mapping[key] || '';
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
