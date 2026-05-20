document.addEventListener('DOMContentLoaded', function () {

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');
    const btn = document.getElementById('complete-task-btn');

    btn.addEventListener('click', function () {
        const taskId = btn.getAttribute('data-task-id');

        // 1. Блокируем кнопку и меняем текст
        btn.disabled = true;
        // Используем Tailwind-спиннер вместо Bootstrap
        btn.innerHTML = `
                        <svg class="animate-spin h-5 w-5 mr-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Проверка на сервере...
                    `;

        fetch(`/main/green-zabgu/eco-tasks/complete/${taskId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 2. Меняем кнопку на зеленый алерт об успехе (в стиле Tailwind)
                    document.getElementById('action-area').innerHTML = `
                                <div class="flex items-center bg-green-50 p-4 rounded-xl border border-green-200">
                                    <i class="material-icons text-3xl eco-green mr-4">check_circle</i>
                                    <div>
                                        <h4 class="font-bold text-gray-800">${data.message}</h4>
                                        <p class="text-gray-600 text-sm mt-1">Баланс обновлен!</p>
                                    </div>
                                </div>
                            `;

                    // 3. Обновляем баланс в шапке сайта
                    const balanceEl = document.getElementById('eco-balance-display');
                    if (balanceEl) {
                        balanceEl.innerText = data.new_balance;
                    }
                } else {
                    alert(data.error || 'Произошла ошибка');
                    btn.disabled = false;
                    // Возвращаем исходный вид кнопки
                    btn.innerHTML = '<i class="material-icons mr-2">bolt</i> Выполнить и получить награду';
                }
            })
            .catch(() => {
                alert('Сетевая ошибка, проверьте подключение');
                btn.disabled = false;
                btn.innerHTML = '<i class="material-icons mr-2">bolt</i> Выполнить и получить награду';
            });
    });
});