"use strict";
document.addEventListener('DOMContentLoaded', () => {
    var _a, _b;
    let selectedRow = null;
    let isEditing = false;
    let isNew = false;
    const tableBody = document.querySelector('#securities-table tbody');
    const btnNew = document.getElementById('btn-new');
    const btnEdit = document.getElementById('btn-edit');
    const btnSave = document.getElementById('btn-save');
    const btnCancel = document.getElementById('btn-cancel');
    const btnDelete = document.getElementById('btn-delete');
    const actionForm = document.getElementById('action-form');
    const typeOptions = ((_a = document.getElementById('type-options')) === null || _a === void 0 ? void 0 : _a.innerHTML) || '';
    const assetClassOptions = ((_b = document.getElementById('asset-class-options')) === null || _b === void 0 ? void 0 : _b.innerHTML) || '';
    function selectRow(row) {
        if (selectedRow === row)
            return;
        if (isEditing || isNew) {
            if (!confirm("Discard unsaved changes?"))
                return;
            cancelEdit();
        }
        if (selectedRow)
            selectedRow.classList.remove('selected-row');
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
        if (selectedRow)
            selectedRow.classList.remove('selected-row');
        const tr = document.createElement('tr');
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
        tableBody === null || tableBody === void 0 ? void 0 : tableBody.prepend(tr);
        selectedRow = tr;
        selectedRow.classList.add('selected-row');
        updateButtonStates();
    }
    function handleEdit() {
        if (!selectedRow)
            return;
        isEditing = true;
        const d = selectedRow.dataset;
        const cells = selectedRow.cells;
        cells[0].innerHTML = `<input type="text" class="edit-input" value="${d.symbol}">`;
        cells[1].innerHTML = `<input type="text" class="edit-input" value="${d.name}">`;
        cells[2].innerHTML = `<select class="edit-input">${typeOptions}</select>`;
        cells[2].querySelector('select').value = d.type;
        cells[3].innerHTML = `<select class="edit-input">${assetClassOptions}</select>`;
        cells[3].querySelector('select').value = d.assetClass;
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
        var _a;
        if (isNew) {
            (_a = document.getElementById('temp-row')) === null || _a === void 0 ? void 0 : _a.remove();
            isNew = false;
        }
        else if (isEditing && selectedRow) {
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
        const firstRow = document.querySelector('#securities-table tbody tr:not(#temp-row)');
        if (firstRow) {
            selectedRow = null;
            selectRow(firstRow);
        }
        updateButtonStates();
    }
    function handleSave() {
        if (!selectedRow)
            return;
        const inputs = selectedRow.querySelectorAll('input, select');
        const data = {
            symbol: inputs[0].value,
            name: inputs[1].value,
            type: inputs[2].value,
            assetClass: inputs[3].value,
            prevClose: inputs[4].value,
            open: inputs[5].value,
            price: inputs[6].value,
            nav: inputs[7].value,
            range: inputs[8].value,
            volume: inputs[9].value,
            yield30: inputs[10].value,
            yield7: inputs[11].value,
        };
        if (isNew) {
            actionForm.action = '/admin/securities/create';
        }
        else {
            actionForm.action = `/admin/securities/update/${selectedRow.dataset.id}`;
        }
        document.getElementById('form-symbol').value = data.symbol;
        document.getElementById('form-name').value = data.name;
        document.getElementById('form-type').value = data.type;
        document.getElementById('form-asset-class').value = data.assetClass;
        document.getElementById('form-prev-close').value = data.prevClose;
        document.getElementById('form-open').value = data.open;
        document.getElementById('form-price').value = data.price;
        document.getElementById('form-nav').value = data.nav;
        document.getElementById('form-range').value = data.range;
        document.getElementById('form-volume').value = data.volume;
        document.getElementById('form-yield30').value = data.yield30;
        document.getElementById('form-yield7').value = data.yield7;
        actionForm.submit();
    }
    function handleDelete() {
        if (!selectedRow || isEditing || isNew)
            return;
        if (confirm(`Delete security ${selectedRow.dataset.symbol}?`)) {
            actionForm.action = `/admin/securities/delete/${selectedRow.dataset.id}`;
            actionForm.submit();
        }
    }
    tableBody === null || tableBody === void 0 ? void 0 : tableBody.addEventListener('click', (e) => {
        const tr = e.target.closest('tr');
        if (tr && tableBody.contains(tr) && tr.id !== 'temp-row') {
            selectRow(tr);
        }
    });
    btnNew.addEventListener('click', handleNew);
    btnEdit.addEventListener('click', handleEdit);
    btnSave.addEventListener('click', handleSave);
    btnCancel.addEventListener('click', cancelEdit);
    btnDelete.addEventListener('click', handleDelete);
    const first = document.querySelector('#securities-table tbody tr');
    if (first)
        selectRow(first);
});
