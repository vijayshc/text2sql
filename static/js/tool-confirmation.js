// static/js/tool-confirmation.js

// Display a confirmation dialog for sensitive tool execution
function showConfirmationDialog(toolName, args) {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.classList.add('confirmation-overlay');

        // Create dialog container
        const dialog = document.createElement('div');
        dialog.classList.add('confirmation-dialog', 'glass');

        // Title
        const title = document.createElement('h3');
        title.textContent = `Confirm execution of ${toolName}`;
        dialog.appendChild(title);

        // Arguments display
        const argPre = document.createElement('pre');
        argPre.textContent = JSON.stringify(args, null, 2);
        dialog.appendChild(argPre);

        // Buttons
        const btnContainer = document.createElement('div');
        btnContainer.classList.add('confirmation-buttons');

        const confirmBtn = document.createElement('button');
        confirmBtn.textContent = 'Confirm';
        confirmBtn.classList.add('btn', 'btn-confirm');
        confirmBtn.addEventListener('click', () => {
            document.body.removeChild(overlay);
            resolve(true);
        });

        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.classList.add('btn', 'btn-cancel');
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(overlay);
            resolve(false);
        });

        btnContainer.appendChild(confirmBtn);
        btnContainer.appendChild(cancelBtn);
        dialog.appendChild(btnContainer);

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
    });
}

// Expose function globally
window.showConfirmationDialog = showConfirmationDialog;
