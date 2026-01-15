// static/notifications.js
function showNotification(message, type = 'success') {
    const notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        console.error('Elemento #notification-container não encontrado.');
        return;
    }

    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    notificationContainer.appendChild(notification);

    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, 5000); // 5 segundos
}
