export interface ActivityMetadata {
    browse_panel: {
        search_fields?: Array<{ name: string; label_key: string }>;
        columns: Array<{ name: string; label_key: string }>;
    };
    maintenance_panel: {
        buttons: string[];
        fields: Array<{
            name: string;
            label_key: string;
            read_only: boolean;
            required?: boolean;
            type?: string;
            options_source?: string;
            has_lookup?: boolean;
        }>;
    };
}

export class MaintenanceActivityManager {
    protected selectedRow: HTMLElement | null = null;
    protected isEditing = false;
    protected isNew = false;
    protected originalData: Record<string, string> = {};

    protected btnNew = document.getElementById('btn-new') as HTMLButtonElement;
    protected btnEdit = document.getElementById('btn-edit') as HTMLButtonElement;
    protected btnDelete = document.getElementById('btn-delete') as HTMLButtonElement;
    protected btnSave = document.getElementById('btn-save') as HTMLButtonElement;
    protected btnCancel = document.getElementById('btn-cancel') as HTMLButtonElement;
    protected btnSearch = document.getElementById('btn-search') as HTMLButtonElement;
    protected searchInput = document.getElementById('search-input') as HTMLInputElement;
    protected searchField = document.getElementById('search-field') as HTMLSelectElement;
    
    protected maintenanceForm = document.getElementById('maintenance-form') as HTMLElement;
    protected actionForm = document.getElementById('action-form') as HTMLFormElement;
    protected sep = document.getElementById('status-error-panel') as HTMLElement;
    protected sepContent = document.getElementById('sep-content') as HTMLElement;

    constructor(protected metadata: ActivityMetadata) {
        this.initEventListeners();
        this.disableForm();
        this.updateButtonStates();
    }

    private initEventListeners() {
        // BT Selection
        const tableBody = document.querySelector('#browse-table tbody');
        tableBody?.addEventListener('click', (e) => {
            const tr = (e.target as HTMLElement).closest('tr');
            if (tr && tableBody.contains(tr)) {
                this.selectRow(tr as HTMLElement);
            }
        });

        // AP Buttons
        this.btnNew?.addEventListener('click', () => this.handleNew());
        this.btnEdit?.addEventListener('click', () => this.handleEdit());
        this.btnDelete?.addEventListener('click', () => this.handleDelete());

        // SP Buttons
        this.btnSave?.addEventListener('click', () => this.handleSave());
        this.btnCancel?.addEventListener('click', () => this.handleCancel());

        // Search Button
        this.btnSearch?.addEventListener('click', () => {
            this.filterTable(this.searchField.value, this.searchInput.value);
        });

        // Form Dirty Checking
        this.maintenanceForm?.addEventListener('input', () => this.checkDirty());
        this.maintenanceForm?.addEventListener('change', () => this.checkDirty());
    }

    protected showMessage(msg: string, isError: boolean = false) {
        if (this.sepContent && this.sep) {
            this.sepContent.textContent = msg;
            this.sepContent.style.color = isError ? '#c00' : '#28a745';
            this.sep.style.display = 'block';
        }
    }

    protected clearMessage() {
        if (this.sepContent && this.sep) {
            this.sepContent.textContent = '';
            this.sep.style.display = 'none';
        }
    }

    protected selectRow(row: HTMLElement) {
        if (this.selectedRow === row) return;
        
        if (this.isDirty()) {
            if (!confirm("Discard unsaved changes?")) return;
        }

        if (this.selectedRow) this.selectedRow.classList.remove('selected');
        this.selectedRow = row;
        this.selectedRow.classList.add('selected');

        this.isEditing = false;
        this.isNew = false;
        
        this.populateFormFromRow(row);
        this.disableForm();
        this.updateButtonStates();
        this.clearMessage();
    }

    protected populateFormFromRow(row: HTMLElement) {
        this.originalData = {};
        this.metadata.maintenance_panel.fields.forEach(f => {
            const val = row.getAttribute(`data-${f.name.replace(/_/g, '-')}`) || '';
            const input = document.getElementById(`field-${f.name}`) as HTMLInputElement | HTMLSelectElement;
            if (input) {
                input.value = val;
                this.originalData[f.name] = val;
            }
        });
    }

    protected disableForm() {
        const inputs = this.maintenanceForm.querySelectorAll('input, select');
        inputs.forEach(i => (i as HTMLInputElement).disabled = true);
        const lookupButtons = this.maintenanceForm.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => (btn as HTMLElement).style.display = 'none');
    }

    protected enableForm() {
        this.metadata.maintenance_panel.fields.forEach(f => {
            const input = document.getElementById(`field-${f.name}`) as HTMLInputElement | HTMLSelectElement;
            if (input) {
                input.disabled = f.read_only;
            }
        });
        const lookupButtons = this.maintenanceForm.querySelectorAll('.btn-lookup');
        lookupButtons.forEach(btn => (btn as HTMLElement).style.display = 'inline-block');
    }

    protected updateButtonStates() {
        if (this.btnNew) this.btnNew.disabled = false;

        const canEdit = this.selectedRow && !this.isNew && !this.isEditing;
        const canDelete = this.selectedRow && !this.isNew; 
        
        if (this.btnEdit) this.btnEdit.disabled = !canEdit;
        if (this.btnDelete) this.btnDelete.disabled = !canDelete;
        
        this.checkDirty();
    }

    protected isDirty(): boolean {
        if (this.isNew) return true;
        if (!this.isEditing) return false;

        return this.metadata.maintenance_panel.fields.some(f => {
            const input = document.getElementById(`field-${f.name}`) as HTMLInputElement | HTMLSelectElement;
            return input && input.value !== (this.originalData[f.name] || '');
        });
    }

    protected checkDirty() {
        const dirty = this.isDirty();
        if (this.btnSave) this.btnSave.disabled = !dirty;
        if (this.btnCancel) this.btnCancel.disabled = !dirty;
    }

    protected handleNew() {
        if (this.isDirty() && !confirm("Discard unsaved changes?")) return;

        this.isNew = true;
        this.isEditing = false;
        if (this.selectedRow) this.selectedRow.classList.remove('selected');
        this.selectedRow = null;

        this.metadata.maintenance_panel.fields.forEach(f => {
            const input = document.getElementById(`field-${f.name}`) as HTMLInputElement | HTMLSelectElement;
            if (input) input.value = '';
        });

        this.enableForm();
        this.updateButtonStates();
        this.clearMessage();
    }

    protected handleEdit() {
        if (!this.selectedRow) return;
        this.isEditing = true;
        this.enableForm();
        this.updateButtonStates();
    }

    protected handleCancel() {
        this.isNew = false;
        this.isEditing = false;
        if (this.selectedRow) {
            this.populateFormFromRow(this.selectedRow);
        } else {
            this.maintenanceForm.querySelectorAll('input, select').forEach(i => (i as HTMLInputElement).value = '');
        }
        this.disableForm();
        this.updateButtonStates();
        this.clearMessage();
    }

    protected handleSave() {
        if (!this.isNew && !this.selectedRow) return;

        if (this.isNew) {
            this.actionForm.action = this.getCreateUrl();
        } else {
            this.actionForm.action = this.getUpdateUrl(this.selectedRow!.getAttribute('data-id')!);
        }

        this.metadata.maintenance_panel.fields.forEach(f => {
            const input = document.getElementById(`field-${f.name}`) as HTMLInputElement | HTMLSelectElement;
            const hidden = document.getElementById(`form-${f.name.replace(/_/g, '-')}`) as HTMLInputElement;
            if (input && hidden) hidden.value = input.value;
        });

        this.actionForm.submit();
    }

    protected handleDelete() {
        if (this.isDirty() && !confirm("Discard unsaved changes?")) return;
        
        if (!this.selectedRow || !confirm("Are you sure you want to delete this record?")) return;
        this.actionForm.action = this.getDeleteUrl(this.selectedRow.getAttribute('data-id')!);
        this.actionForm.submit();
    }

    protected filterTable(field: string, query: string) {
        const rows = document.querySelectorAll('#browse-table tbody tr');
        const q = query.toLowerCase();
        
        // Find which column index matches 'field'
        const columns = this.metadata.browse_panel.columns;
        const colIndex = columns.findIndex(c => c.name === field);

        rows.forEach(row => {
            if (!q) {
                (row as HTMLElement).style.display = '';
                return;
            }
            if (colIndex === -1) return;

            const cell = (row as HTMLTableRowElement).cells[colIndex];
            if (cell) {
                const text = cell.textContent?.toLowerCase() || '';
                (row as HTMLElement).style.display = text.includes(q) ? '' : 'none';
            }
        });
    }

    protected getCreateUrl() { return ""; }
    protected getUpdateUrl(id: string) { return ""; }
    protected getDeleteUrl(id: string) { return ""; }
}
