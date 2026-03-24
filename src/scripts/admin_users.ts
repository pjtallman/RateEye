interface UserRow extends HTMLTableRowElement {
    dataset: DOMStringMap & {
        userId: string;
        isSelf: string;
    };
}

interface CellWithOriginal extends HTMLTableCellElement {
    dataset: DOMStringMap & {
        original: string;
    };
}

document.addEventListener('DOMContentLoaded', () => {
    let selectedRow: UserRow | null = null;
    let isEditing = false;

    const userTableBody = document.querySelector('#user-table tbody');
    const btnEdit = document.getElementById('btn-edit') as HTMLButtonElement;
    const btnSave = document.getElementById('btn-save') as HTMLButtonElement;
    const btnCancel = document.getElementById('btn-cancel') as HTMLButtonElement;
    const btnDelete = document.getElementById('btn-delete') as HTMLButtonElement;
    const actionForm = document.getElementById('action-form') as HTMLFormElement;
    const formEmail = document.getElementById('form-email') as HTMLInputElement;
    const formForcePw = document.getElementById('form-force-pw') as HTMLInputElement;

    function selectRow(row: UserRow) {
        if (selectedRow === row) return;

        if (isEditing) {
            cancelEdit(selectedRow!);
            isEditing = false;
        }

        if (selectedRow) selectedRow.classList.remove('selected-row');
        
        selectedRow = row;
        selectedRow.classList.add('selected-row');
        
        updateButtonStates();
    }

    function updateButtonStates() {
        if (!selectedRow) return;
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

        const emailInput = selectedRow.querySelector('.col-email input') as HTMLInputElement;
        const forcePwInput = selectedRow.querySelector('.col-force-pw input') as HTMLInputElement;
        
        const currentEmail = emailInput.value;
        const currentForcePw = forcePwInput.checked;
        
        const emailCell = selectedRow.querySelector('.col-email') as CellWithOriginal;
        const forcePwCell = selectedRow.querySelector('.col-force-pw') as CellWithOriginal;
        
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        
        const changed = (currentEmail !== originalEmail) || (currentForcePw !== originalForcePw);
        
        btnSave.disabled = !changed;
        btnCancel.disabled = false;
    }

    function handleEdit() {
        if (!selectedRow) return;
        isEditing = true;
        
        const emailCell = selectedRow.querySelector('.col-email') as CellWithOriginal;
        const forcePwCell = selectedRow.querySelector('.col-force-pw') as CellWithOriginal;
        
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        
        emailCell.innerHTML = `<input type="text" class="edit-input" value="${originalEmail}">`;
        forcePwCell.innerHTML = `<input type="checkbox" ${originalForcePw ? 'checked' : ''}>`;
        
        emailCell.querySelector('input')!.addEventListener('input', checkChanges);
        forcePwCell.querySelector('input')!.addEventListener('change', checkChanges);

        updateButtonStates();
    }

    function cancelEdit(row: UserRow) {
        const emailCell = row.querySelector('.col-email') as CellWithOriginal;
        const forcePwCell = row.querySelector('.col-force-pw') as CellWithOriginal;
        
        const originalEmail = emailCell.dataset.original;
        const originalForcePw = forcePwCell.dataset.original === 'true';
        
        emailCell.textContent = originalEmail;
        forcePwCell.textContent = originalForcePw ? 'Yes' : 'No';
    }

    function handleCancel() {
        if (!selectedRow || !isEditing) return;
        cancelEdit(selectedRow);
        isEditing = false;
        updateButtonStates();
    }

    function handleSave() {
        if (!selectedRow || !isEditing) return;
        
        const userId = selectedRow.dataset.userId;
        const emailInput = selectedRow.querySelector('.col-email input') as HTMLInputElement;
        const forcePwInput = selectedRow.querySelector('.col-force-pw input') as HTMLInputElement;
        
        const email = emailInput.value;
        const forcePw = forcePwInput.checked;
        
        actionForm.action = `/admin/users/update/${userId}`;
        formEmail.value = email;
        
        if (!forcePw) {
            formForcePw.name = ""; 
        } else {
            formForcePw.name = "force_password_change";
            formForcePw.value = "true";
        }

        actionForm.submit();
    }

    function handleDeleteUser() {
        if (!selectedRow || isEditing) return;
        const userId = selectedRow.dataset.userId;
        const isSelf = selectedRow.dataset.isSelf === 'true';
        
        if (isSelf) return;
        
        if (confirm('Are you sure you want to delete this user?')) {
            actionForm.action = `/admin/users/delete/${userId}`;
            actionForm.submit();
        }
    }

    // Attach Event Listeners
    if (userTableBody) {
        userTableBody.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            const row = target.closest('tr') as UserRow;
            if (row && userTableBody.contains(row)) {
                selectRow(row);
            }
        });
    }

    btnEdit?.addEventListener('click', handleEdit);
    btnSave?.addEventListener('click', handleSave);
    btnCancel?.addEventListener('click', handleCancel);
    btnDelete?.addEventListener('click', handleDeleteUser);

    // Initial Selection
    const firstRow = document.querySelector('#user-table tbody tr') as UserRow;
    if (firstRow) selectRow(firstRow);
});
