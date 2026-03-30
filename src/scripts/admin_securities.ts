import { MaintenanceActivityManager, ActivityMetadata } from './maintenance_activity.js';

class SecuritiesManager extends MaintenanceActivityManager {
    private lookupModal = document.getElementById('lookup-modal') as HTMLElement;
    private lookupResultsList = document.getElementById('lookup-results-list') as HTMLElement;
    private lookupResultsCount = document.getElementById('lookup-results-count') as HTMLElement;
    private lookupSearchInput = document.getElementById('lookup-search-input') as HTMLInputElement;
    private btnLookupSearch = document.getElementById('btn-lookup-search') as HTMLButtonElement;
    private btnCloseLookup = document.getElementById('btn-close-lookup') as HTMLButtonElement;

    constructor(metadata: ActivityMetadata) {
        super(metadata);
        this.initLookupListeners();
    }

    private initLookupListeners() {
        const lookupButtons = document.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openLookupDialog();
            });
        });

        this.btnLookupSearch?.addEventListener('click', () => this.handleLookup());
        
        this.btnCloseLookup?.addEventListener('click', () => {
            this.lookupModal.style.display = 'none';
        });

        // Allow Enter key in lookup search
        this.lookupSearchInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLookup();
            }
        });
    }

    private openLookupDialog() {
        const symbolInput = document.getElementById('field-symbol') as HTMLInputElement;
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
            this.lookupSearchInput?.focus();
        }
    }

    private async handleLookup() {
        let query = this.lookupSearchInput?.value.trim();
        if (!query) {
            alert("Please enter a symbol or name to lookup.");
            return;
        }

        try {
            this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px;">Searching...</td></tr>';
            this.lookupResultsCount.textContent = '';

            // Requirement (1): Exact match first
            let results = await this.performSearch(query);

            // Requirement (1): If no records, then starts with search
            if (results.length === 0 && !query.endsWith('*')) {
                results = await this.performSearch(query + '*');
            }

            this.showLookupResults(results);
        } catch (err: any) {
            if (err.message.includes("429") || err.message.includes("Rate limited")) {
                this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px; color: #c00;">Error: Too many requests. Yahoo Finance is rate-limiting our search. Please try again later.</td></tr>';
            } else {
                this.lookupResultsList.innerHTML = `<tr><td colspan="2" style="padding: 15px; color: #c00;">Error searching for security: ${err.message}</td></tr>`;
            }
        }
    }

    private async performSearch(q: string): Promise<any[]> {
        const resp = await fetch(`/admin/securities/search?q=${encodeURIComponent(q)}`);
        if (resp.status === 429) {
            throw new Error("Rate limited");
        }
        if (!resp.ok) {
            throw new Error(`Search failed with status ${resp.status}`);
        }
        return await resp.json();
    }

    private showLookupResults(results: any[]) {
        this.lookupResultsList.innerHTML = '';
        
        // Display count of matching records
        if (this.lookupResultsCount) {
            this.lookupResultsCount.textContent = `Found ${results.length} record(s)`;
        }

        if (results.length === 0) {
            this.lookupResultsList.innerHTML = '<tr><td colspan="2" style="padding: 15px;">No results found.</td></tr>';
        } else {
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

    private async fetchMetadata(symbol: string) {
        try {
            this.showMessage(`Fetching metadata for ${symbol}...`);
            const resp = await fetch(`/admin/securities/lookup?symbol=${encodeURIComponent(symbol)}`);
            if (!resp.ok) {
                if (resp.status === 404) {
                    throw new Error(`Security details for '${symbol}' not found on Yahoo Finance.`);
                }
                throw new Error(`Lookup failed with status ${resp.status}`);
            }
            const data = await resp.json();
            this.populateFormWithMetadata(data);
            this.showMessage(`Successfully loaded ${symbol}`);
        } catch (err: any) {
            this.showMessage(err.message || "Error fetching security metadata.", true);
        }
    }

    private populateFormWithMetadata(data: any) {
        const mapping: Record<string, any> = {
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
            const input = document.getElementById(`field-${key}`) as HTMLInputElement | HTMLSelectElement;
            if (input && mapping[key] !== undefined) {
                input.value = mapping[key] || '';
            }
        });
        
        this.checkDirty();
    }

    protected override getCreateUrl() { return "/admin/securities/create"; }
    protected override getUpdateUrl(id: string) { return `/admin/securities/update/${id}`; }
    protected override getDeleteUrl(id: string) { return `/admin/securities/delete/${id}`; }
}

document.addEventListener('DOMContentLoaded', () => {
    const metadataElement = document.getElementById('metadata-json');
    if (metadataElement) {
        const metadata = JSON.parse(metadataElement.textContent || '{}');
        new SecuritiesManager(metadata);
    }
});
