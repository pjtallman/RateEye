interface SecurityRow extends HTMLTableRowElement {
    dataset: DOMStringMap & {
        id: string;
        symbol: string;
        name: string;
        type: string;
        assetClass: string;
        prevClose: string;
        open: string;
        price: string;
        nav: string;
        range: string;
        volume: string;
        yield30: string;
        yield7: string;
    };
}

document.addEventListener('DOMContentLoaded', () => {
    let selectedRow: SecurityRow | null = null;
    let isEditing = false;
    let isNew = false;

    const tableBody = document.querySelector('#securities-table tbody');
    const btnNew = document.getElementById('btn-new') as HTMLButtonElement;
    const btnEdit = document.getElementById('btn-edit') as HTMLButtonElement;
    const btnSave = document.getElementById('btn-save') as HTMLButtonElement;
    const btnCancel = document.getElementById('btn-cancel') as HTMLButtonElement;
    const btnDelete = document.getElementById('btn-delete') as HTMLButtonElement;
    
    const actionForm = document.getElementById('action-form') as HTMLFormElement;
    const typeOptions = document.getElementById('type-options')?.innerHTML || '';
    const assetClassOptions = document.getElementById('asset-class-options')?.innerHTML || '';

    function selectRow(row: SecurityRow) {
        if (selectedRow === row) return;
        if (isEditing || isNew) {
            if (!confirm("Discard unsaved changes?")) return;
            cancelEdit();
        }

        if (selectedRow) selectedRow.classList.remove('selected-row');
        selectedRow = row;
        selectedRow.classList.add('selected-row');
        updateButtonStates();
    }

    function updateButtonStates() {
        btnEdit.disabled = !selectedRow || isEditing || isNew;
        btnDelete.disabled = !selectedRow || isEditing || isNew;
        btnNew.disabled = isEditing || isNew;
        checkChanges();
    }

    function checkChanges() {
        if (!selectedRow || (!isEditing && !isNew)) {
            btnSave.disabled = true;
            btnCancel.disabled = true;
            return;
        }
        btnSave.disabled = false;
        btnCancel.disabled = false;
    }

    function handleNew() {
        isNew = true;
        if (selectedRow) selectedRow.classList.remove('selected-row');
        
        const tr = document.createElement('tr') as SecurityRow;
        tr.id = 'temp-row';
        tr.innerHTML = `
            <td><input type="text" class="edit-input" placeholder="Symbol"></td>
            <td><input type="text" class="edit-input" placeholder="Name"></td>
            <td><select class="edit-input">${typeOptions}</select></td>
            <td><select class="edit-input">${assetClassOptions}</select></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
            <td><input type="text" class="edit-input"></td>
        `;
        tableBody?.prepend(tr);
        selectedRow = tr;
        selectedRow.classList.add('selected-row');
        updateButtonStates();
    }

    function handleEdit() {
        if (!selectedRow) return;
        isEditing = true;
        
        const d = selectedRow.dataset;
        const cells = selectedRow.cells;
        
        cells[0].innerHTML = `<input type="text" class="edit-input" value="${d.symbol}">`;
        cells[1].innerHTML = `<input type="text" class="edit-input" value="${d.name}">`;
        
        cells[2].innerHTML = `<select class="edit-input">${typeOptions}</select>`;
        (cells[2].querySelector('select') as HTMLSelectElement).value = d.type;
        
        cells[3].innerHTML = `<select class="edit-input">${assetClassOptions}</select>`;
        (cells[3].querySelector('select') as HTMLSelectElement).value = d.assetClass;
        
        cells[4].innerHTML = `<input type="text" class="edit-input" value="${d.prevClose}">`;
        cells[5].innerHTML = `<input type="text" class="edit-input" value="${d.open}">`;
        cells[6].innerHTML = `<input type="text" class="edit-input" value="${d.price}">`;
        cells[7].innerHTML = `<input type="text" class="edit-input" value="${d.nav}">`;
        cells[8].innerHTML = `<input type="text" class="edit-input" value="${d.range}">`;
        cells[9].innerHTML = `<input type="text" class="edit-input" value="${d.volume}">`;
        cells[10].innerHTML = `<input type="text" class="edit-input" value="${d.yield30}">`;
        cells[11].innerHTML = `<input type="text" class="edit-input" value="${d.yield7}">`;

        updateButtonStates();
    }

    function cancelEdit() {
        if (isNew) {
            document.getElementById('temp-row')?.remove();
            isNew = false;
        } else if (isEditing && selectedRow) {
            const d = selectedRow.dataset;
            selectedRow.cells[0].textContent = d.symbol;
            selectedRow.cells[1].textContent = d.name;
            selectedRow.cells[2].textContent = d.type;
            selectedRow.cells[3].textContent = d.assetClass;
            selectedRow.cells[4].textContent = d.prevClose;
            selectedRow.cells[5].textContent = d.open;
            selectedRow.cells[6].textContent = d.price;
            selectedRow.cells[7].textContent = d.nav;
            selectedRow.cells[8].textContent = d.range;
            selectedRow.cells[9].textContent = d.volume;
            selectedRow.cells[10].textContent = d.yield30;
            selectedRow.cells[11].textContent = d.yield7;
            isEditing = false;
        }
        
        const firstRow = document.querySelector('#securities-table tbody tr:not(#temp-row)') as SecurityRow;
        if (firstRow) {
            selectedRow = null;
            selectRow(firstRow);
        }
        updateButtonStates();
    }

    function handleSave() {
        if (!selectedRow) return;
        
        const inputs = selectedRow.querySelectorAll('input, select');
        const data = {
            symbol: (inputs[0] as HTMLInputElement).value,
            name: (inputs[1] as HTMLInputElement).value,
            type: (inputs[2] as HTMLSelectElement).value,
            assetClass: (inputs[3] as HTMLSelectElement).value,
            prevClose: (inputs[4] as HTMLInputElement).value,
            open: (inputs[5] as HTMLInputElement).value,
            price: (inputs[6] as HTMLInputElement).value,
            nav: (inputs[7] as HTMLInputElement).value,
            range: (inputs[8] as HTMLInputElement).value,
            volume: (inputs[9] as HTMLInputElement).value,
            yield30: (inputs[10] as HTMLInputElement).value,
            yield7: (inputs[11] as HTMLInputElement).value,
        };

        if (isNew) {
            actionForm.action = '/admin/securities/create';
        } else {
            actionForm.action = `/admin/securities/update/${selectedRow.dataset.id}`;
        }

        (document.getElementById('form-symbol') as HTMLInputElement).value = data.symbol;
        (document.getElementById('form-name') as HTMLInputElement).value = data.name;
        (document.getElementById('form-type') as HTMLInputElement).value = data.type;
        (document.getElementById('form-asset-class') as HTMLInputElement).value = data.assetClass;
        (document.getElementById('form-prev-close') as HTMLInputElement).value = data.prevClose;
        (document.getElementById('form-open') as HTMLInputElement).value = data.open;
        (document.getElementById('form-price') as HTMLInputElement).value = data.price;
        (document.getElementById('form-nav') as HTMLInputElement).value = data.nav;
        (document.getElementById('form-range') as HTMLInputElement).value = data.range;
        (document.getElementById('form-volume') as HTMLInputElement).value = data.volume;
        (document.getElementById('form-yield30') as HTMLInputElement).value = data.yield30;
        (document.getElementById('form-yield7') as HTMLInputElement).value = data.yield7;

        actionForm.submit();
    }

    function handleDelete() {
        if (!selectedRow || isEditing || isNew) return;
        if (confirm(`Delete security ${selectedRow.dataset.symbol}?`)) {
            actionForm.action = `/admin/securities/delete/${selectedRow.dataset.id}`;
            actionForm.submit();
        }
    }

    tableBody?.addEventListener('click', (e) => {
        const tr = (e.target as HTMLElement).closest('tr') as SecurityRow;
        if (tr && tableBody.contains(tr) && tr.id !== 'temp-row') {
            selectRow(tr);
        }
    });

    btnNew.addEventListener('click', handleNew);
    btnEdit.addEventListener('click', handleEdit);
    btnSave.addEventListener('click', handleSave);
    btnCancel.addEventListener('click', cancelEdit);
    btnDelete.addEventListener('click', handleDelete);

    const first = document.querySelector('#securities-table tbody tr') as SecurityRow;
    if (first) selectRow(first);
});
