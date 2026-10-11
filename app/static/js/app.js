document.addEventListener('DOMContentLoaded', () => {
    const setupView = document.getElementById('setupView');
    const questView = document.getElementById('questView');
    const uploadView = document.getElementById('uploadView');
    const resultView = document.getElementById('resultView');
    const taskList = document.getElementById('taskList');
    const uploadStatus = document.getElementById('uploadStatus');
    const journalText = document.getElementById('journalText');
    const streakText = document.getElementById('streakText');

    let currentQuestId = null;

    // Toggle Outdoor Mode
    document.getElementById('toggleOutdoor').addEventListener('click', () => {
        document.body.classList.toggle('outdoor-mode');
    });

    // Start Quest
    document.getElementById('startQuest').addEventListener('click', async () => {
        const env = document.getElementById('environment').value;
        const diff = document.getElementById('difficulty').value;
        const dur = document.getElementById('duration').value;

        try {
            document.getElementById('startQuest').innerText = 'Generating...';
            const response = await fetch('/api/quests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ environment: env, difficulty: diff, duration: parseInt(dur) })
            });

            if (!response.ok) throw new Error('Ollama error. Is it running?');

            const quest = await response.json();
            renderQuest(quest.tasks);
            
            // Get latest quest ID from DB
            const latest = await fetch('/api/quests/latest').then(r => r.json());
            currentQuestId = latest.id;

            showView(questView);
        } catch (err) {
            alert(err.message);
        } finally {
            document.getElementById('startQuest').innerText = 'Generate Quest';
        }
    });

    function renderQuest(tasks) {
        taskList.innerHTML = '';
        tasks.forEach(task => {
            const div = document.createElement('div');
            div.className = 'quest-task';
            div.innerHTML = `
                <div class="task-id">${task.id}</div>
                <div class="task-text">${task.text}</div>
            `;
            taskList.appendChild(div);
        });
    }

    document.getElementById('finishWalk').addEventListener('click', () => {
        showView(uploadView);
    });

    // Process Photos
    document.getElementById('processPhotos').addEventListener('click', async () => {
        const files = document.getElementById('photoUpload').files;
        if (files.length === 0) {
            await finalizeJournal();
            return;
        }

        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }

        try {
            uploadStatus.innerText = 'Processing photos with vision model...';
            await fetch(`/api/quests/${currentQuestId}/match-photos`, {
                method: 'POST',
                body: formData
            });
            await finalizeJournal();
        } catch (err) {
            alert('Error processing photos: ' + err.message);
        }
    });

    async function finalizeJournal() {
        uploadStatus.innerText = 'Writing journal...';
        const response = await fetch(`/api/quests/${currentQuestId}/journal`, { method: 'POST' });
        const data = await response.json();
        journalText.innerText = data.journal;

        const history = await fetch('/api/history').then(r => r.json());
        streakText.innerText = `Streak: ${history.streak} days outside this week!`;
        
        showView(resultView);
        loadHistory();
    }

    async function loadHistory() {
        const historyList = document.getElementById('historyList');
        const data = await fetch('/api/history').then(r => r.json());
        historyList.innerHTML = '';
        data.history.forEach(q => {
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `
                <small>${new Date(q.created_at).toLocaleDateString()}</small>
                <p><strong>${q.environment} walk</strong></p>
                <p>${q.journal_entry || 'No journal yet.'}</p>
            `;
            historyList.appendChild(div);
        });
    }

    function showView(view) {
        document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
        view.classList.remove('hidden');
    }

    document.getElementById('newQuest').addEventListener('click', () => {
        showView(setupView);
    });

    loadHistory();
});
