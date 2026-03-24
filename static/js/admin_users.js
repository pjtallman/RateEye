"use strict";
document.addEventListener('DOMContentLoaded', () => {
    let selectedRow = null;
    let isEditing = false;
    const userTableBody = document.querySelector('#user-table tbody');
    const btnEdit = document.getElementById('btn-edit');
    const btnSave = document.getElementById('btn-save');
    const btnCancel = document.getElementById('btn-cancel');
    const btnDelete = document.getElementById('btn-delete');
    const actionForm = document.getElementById('action-form');
    const formEmail = document.getElementById('form-email');
    const formForcePw = document.getElementById('form-force-pw');
    function selectRow(row) {
        if (selectedRow === row)
            return;
        if (isEditing) {
            cancelEdit(selectedRow);
            isEditing = false;
        }
        if (selectedRow)
            selectedRow.classList.remove('selected-row');
        selectedRow = row;
        selectedRow.classList.add('selected-row');
        updateButtonStates();
    }
    function updateButtonStates() {
        if (!selectedRow)
            return;
        const isSelf = selectedRow.dataset.isSelf === 'true';
        btnDelete.disabled = isEditing || isSelf;
        btnEdit.disabled = isEditing;
        checkChanges();
    }
    function checkChanges() {
        if (!isEditing || !selectedRow) {
            btnSave.disabled = true;
            btnCancel.disabled = !isEditing;
            return;
        }
        const emailInput = selectedRow.querySelector('.col-email input');
        const forcePwInput = selectedRow.querySelector('.col-force-pw input');
        const currentEmail = emailInput.value;
        const currentForcePw = forcePwInput.checked;
        const emailCell = selectedRow.querySelector('.col-email');
        const forcePwCell = selectedRow.querySelector('.col-force-pw');
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        const changed = (currentEmail !== originalEmail) || (currentForcePw !== originalForcePw);
        btnSave.disabled = !changed;
        btnCancel.disabled = false;
    }
    function handleEdit() {
        if (!selectedRow)
            return;
        isEditing = true;
        const emailCell = selectedRow.querySelector('.col-email');
        const forcePwCell = selectedRow.querySelector('.col-force-pw');
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        emailCell.innerHTML = `<input type="text" class="edit-input" value="${originalEmail}">`;
        forcePwCell.innerHTML = `<input type="checkbox" ${originalForcePw ? 'checked' : ''}>`;
        emailCell.querySelector('input').addEventListener('input', checkChanges);
        forcePwCell.querySelector('input').addEventListener('change', checkChanges);
        updateButtonStates();
    }
    function cancelEdit(row) {
        const emailCell = row.querySelector('.col-email');
        const forcePwCell = row.querySelector('.col-force-pw');
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        emailCell.textContent = originalEmail;
        forcePwCell.textContent = originalForcePw ? 'Yes' : 'No';
    }
    function handleCancel() {
        if (!selectedRow || !isEditing)
            return;
        cancelEdit(selectedRow);
        isEditing = false;
        updateButtonStates();
    }
    function handleSave() {
        if (!selectedRow || !isEditing)
            return;
        const userId = selectedRow.dataset.userId;
        const emailInput = selectedRow.querySelector('.col-email input');
        const forcePwInput = selectedRow.querySelector('.col-force-pw input');
        const email = emailInput.value;
        const forcePw = forcePwInput.checked;
        actionForm.action = `/admin/users/update/${userId}`;
        formEmail.value = email;
        if (!forcePw) {
            formForcePw.name = "";
        }
        else {
            formForcePw.name = "force_password_change";
            formForcePw.value = "true";
        }
        actionForm.submit();
    }
    function handleDeleteUser() {
        if (!selectedRow || isEditing)
            return;
        const userId = selectedRow.dataset.userId;
        const isSelf = selectedRow.dataset.isSelf === 'true';
        if (isSelf)
            return;
        if (confirm('Are you sure you want to delete this user?')) {
            actionForm.action = `/admin/users/delete/${userId}`;
            actionForm.submit();
        }
    }
    // Attach Event Listeners
    if (userTableBody) {
        userTableBody.addEventListener('click', (e) => {
            const target = e.target;
            const row = target.closest('tr');
            if (row && userTableBody.contains(row)) {
                selectRow(row);
            }
        });
    }
    btnEdit === null || btnEdit === void 0 ? void 0 : btnEdit.addEventListener('click', handleEdit);
    btnSave === null || btnSave === void 0 ? void 0 : btnSave.addEventListener('click', handleSave);
    btnCancel === null || btnCancel === void 0 ? void 0 : btnCancel.addEventListener('click', handleCancel);
    btnDelete === null || btnDelete === void 0 ? void 0 : btnDelete.addEventListener('click', handleDeleteUser);
    // Initial Selection
    const firstRow = document.querySelector('#user-table tbody tr');
    if (firstRow)
        selectRow(firstRow);
});
