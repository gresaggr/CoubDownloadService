const {createApp} = Vue;

createApp({
    data() {
        return {
            url: '',
            loading: false,
            statusMessage: '',
            statusClass: '',
            fileReady: false,
            currentFileId: null,
            taskId: null,
            pollInterval: null,
            progress: null,
            errorDetails: null,
            lastError: null
        }
    },
    methods: {
        async processUrl() {
            if (!this.url) return;

            this.loading = true;
            this.fileReady = false;
            this.statusMessage = '';
            this.errorDetails = null;
            this.progress = null;

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({url: this.url})
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Ошибка при обработке запроса');
                }

                const data = await response.json();

                if (data.status === 'completed' && data.result) {
                    // Файл уже готов
                    this.showCompletedStatus(data.result);
                } else if (data.task_id) {
                    // Задача поставлена в очередь
                    this.taskId = data.task_id;
                    this.showPendingStatus();
                    this.startPolling();
                } else if (data.status === 'pending' || data.status === 'processing') {
                    // Файл уже в обработке
                    this.statusMessage = 'Статус: Уже обрабатывается';
                    this.statusClass = 'pending';
                }

            } catch (error) {
                console.error('Error:', error);
                this.handleError(error);
            } finally {
                this.loading = false;
            }
        },

        startPolling() {
            // Очищаем предыдущий интервал если есть
            this.stopPolling();

            this.pollInterval = setInterval(async () => {
                await this.checkTaskStatus();
            }, 2000);
        },

        async checkTaskStatus() {
            if (!this.taskId) return;

            try {
                const response = await fetch(`/api/task/${this.taskId}`);

                if (!response.ok) {
                    throw new Error('Ошибка при проверке статуса');
                }

                const data = await response.json();

                // Обработка прогресса
                if (data.progress) {
                    this.progress = data.progress;
                    this.statusMessage = `${data.progress.status || 'Обработка'} (${data.progress.current}%)`;
                    this.statusClass = 'pending';
                }

                // Файл готов
                if (data.status === 'completed' && data.result) {
                    this.stopPolling();
                    this.showCompletedStatus(data.result);
                }
                // Ошибка
                else if (data.status === 'failed' || data.error) {
                    this.stopPolling();
                    this.statusMessage = 'Ошибка при обработке файла';
                    this.statusClass = 'error';
                    this.errorDetails = data.error || 'Неизвестная ошибка';
                }
                // Всё ещё обрабатывается
                else if (data.status === 'processing' || data.status === 'pending') {
                    if (!this.progress) {
                        this.statusMessage = 'Статус: ' + (data.status === 'pending' ? 'Ожидание' : 'Обработка');
                    }
                }

            } catch (error) {
                console.error('Error checking status:', error);
                // Не останавливаем polling при ошибке сети, пробуем ещё
                this.lastError = error.message;
            }
        },

        stopPolling() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        },

        showPendingStatus() {
            this.statusMessage = 'Статус: Обработка';
            this.statusClass = 'pending';
        },

        showCompletedStatus(result) {
            this.currentFileId = result.id;
            this.statusMessage = 'Статус: Готов';
            this.statusClass = 'completed';
            this.fileReady = true;
            this.progress = null;

            // Скрыть плашку через 2 секунды
            setTimeout(() => {
                this.statusMessage = '';
            }, 2000);
        },

        downloadFile() {
            if (this.currentFileId) {
                // Скачиваем файл
                window.location.href = `/api/download/${this.currentFileId}`;

                // Сбрасываем состояние через небольшую задержку
                setTimeout(() => {
                    this.fileReady = false;
                    this.url = "";
                    this.currentFileId = null;
                    this.taskId = null;
                    this.progress = null;
                    this.statusMessage = "Файл скачан!";
                    this.statusClass = "completed";

                    setTimeout(() => {
                        this.statusMessage = "";
                    }, 2000);
                }, 500);
            }
        },

        handleError(error) {
            if (error instanceof TypeError && error.message.includes('fetch')) {
                this.statusMessage = 'Нет соединения с сервером';
            } else if (error.message.includes('422')) {
                this.statusMessage = 'Некорректный URL. Используйте формат: https://coub.com/view/VIDEO_ID';
            } else if (error.message.includes('429')) {
                this.statusMessage = 'Слишком много запросов. Подождите немного.';
            } else {
                this.statusMessage = error.message || 'Произошла ошибка';
            }
            this.statusClass = 'error';
        },

        clearError() {
            this.statusMessage = '';
            this.statusClass = '';
            this.errorDetails = null;
            this.lastError = null;
        }
    },

    beforeUnmount() {
        this.stopPolling();
    }
}).mount('#app');