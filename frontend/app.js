const { createApp } = Vue;

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
            pollInterval: null
        }
    },
    methods: {
        async processUrl() {
            if (!this.url) return;

            this.loading = true;
            this.fileReady = false;
            this.statusMessage = '';

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ url: this.url })
                });

                const data = await response.json();

                if (data.status === 'completed' && data.result) {
                    // Файл уже готов
                    this.showCompletedStatus(data.result);
                } else if (data.task_id) {
                    // Задача поставлена в очередь
                    this.taskId = data.task_id;
                    this.showPendingStatus();
                    this.startPolling();
                }

            } catch (error) {
                console.error('Error:', error);
                this.statusMessage = 'Ошибка при обработке запроса';
                this.statusClass = 'error';
            } finally {
                this.loading = false;
            }
        },

        startPolling() {
            this.pollInterval = setInterval(async () => {
                await this.checkTaskStatus();
            }, 2000);
        },

        async checkTaskStatus() {
            if (!this.taskId) return;

            try {
                const response = await fetch(`/api/task/${this.taskId}`);
                const data = await response.json();

                if (data.status === 'completed' && data.result) {
                    this.stopPolling();
                    this.showCompletedStatus(data.result);
                } else if (data.status === 'failed') {
                    this.stopPolling();
                    this.statusMessage = 'Ошибка при обработке файла';
                    this.statusClass = 'error';
                }
            } catch (error) {
                console.error('Error checking status:', error);
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

            // Скрыть плашку через 1 секунду
            setTimeout(() => {
                this.statusMessage = '';
            }, 1000);
        },

        downloadFile() {
            if (this.currentFileId) {
                window.location.href = `/api/download/${this.currentFileId}`;
                setTimeout(() => {
                    this.fileReady = false;
                    this.url = "";
                    this.currentFileId = null;
                    this.taskId = null;
                    this.statusMessage = "Файл скачан!";
                    this.statusClass = "completed";
                    setTimeout(() => {
                        this.statusMessage = "";
                    }, 1500);
                }, 500);
            }
        }
    },

    beforeUnmount() {
        this.stopPolling();
    }
}).mount('#app');
