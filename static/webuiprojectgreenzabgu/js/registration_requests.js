// 1. Генерация инициалов из ФИО
document.querySelectorAll('.initials').forEach(el => {
    const parts = el.dataset.name.split(' ');
    if (parts.length >= 2) {
        el.textContent = parts[0][0] + parts[1][0];
    } else {
        el.textContent = parts[0].substring(0, 2);
    }
});

let currentRequestId = null;

// 2. Логика модального окна
function openModal(id, fio, group, email) {
    currentRequestId = id;
    document.getElementById('modal-fio').textContent = fio;
    document.getElementById('modal-group').textContent = group;
    document.getElementById('modal-email').textContent = email;
    document.getElementById('approveModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('approveModal').style.display = 'none';
    currentRequestId = null;
}

// Функция для получения CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.substring(0, name.length + 1) === (name + '=')) cookieValue = decodeURIComponent(c.substring(name.length + 1));
        });
    }
    return cookieValue;
}

// 3. Отклонить (Быстро, без модалки)
function rejectRequest(id) {
    if (!confirm('Вы уверены, что хотите отклонить эту заявку?')) return;

    fetch(`/api/moderate-request/${id}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'action=reject'
    }).then(res => res.json()).then(data => {
        if (data.status === 'success') location.reload();
        else alert(data.message || 'Ошибка');
    });
}

// 4. Подтвердить (Из модалки)
document.getElementById('btn-final-approve').addEventListener('click', function () {
    if (!currentRequestId) return;
    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Создание...';

    fetch(`/api/moderate-request/${currentRequestId}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'action=approve'
    }).then(res => res.json()).then(data => {
        if (data.status === 'success') {
            closeModal();
            location.reload(); // Перезагружаем чтобы обновить статистику и убрать карточку
        } else {
            alert(data.message || 'Ошибка');
            btn.disabled = false;
            btn.innerHTML = '<i class="material-icons text-sm align-middle mr-1">send</i>Создать и отправить';
        }
    });
});