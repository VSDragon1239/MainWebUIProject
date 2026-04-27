(function () {
    const logoutBtn = document.getElementById('logoutBtn');
    const modal = document.getElementById('logoutModal');
    const form = document.getElementById('logoutForm');
    const confirmBtn = document.getElementById('confirmLogout');
    const cancelBtn = document.getElementById('cancelLogout');
    const modalContent = modal.querySelector('.modal-content');

    // Открыть модалку
    logoutBtn.addEventListener('click', () => {
        modal.style.display = 'block';
        // Зафиксировать фокус внутри
        modalContent.focus();
    });

    // Подтверждение — отправляем форму POST
    confirmBtn.addEventListener('click', () => {
        form.submit();
    });

    // Отмена — закрываем модалку
    function closeModal() {
        modal.style.display = 'none';
        logoutBtn.focus();
    }

    cancelBtn.addEventListener('click', closeModal);

    // Закрытие по Esc и клику по фону
    modal.addEventListener('click', (e) => {
        if (e.target === modal || e.target.classList.contains('modal-backdrop')) {
            closeModal();
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            closeModal();
        }
    });
})();