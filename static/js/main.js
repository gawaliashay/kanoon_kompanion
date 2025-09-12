// ----------------------------
// Service Switching
// ----------------------------
function showService(serviceId) {
    const sections = document.querySelectorAll('.service-section');
    sections.forEach(sec => sec.classList.remove('active'));
    const target = document.getElementById(serviceId);
    if (target) target.classList.add('active');
    window.scrollTo({ top: target.offsetTop - 80, behavior: 'smooth' });
}

function goToHome() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showServicesSection() {
    showService('services-section');
}

// ----------------------------
// File Previews
// ----------------------------
function previewFiles(type) {
    let input, preview, list;
    if (type === 'analysis') {
        input = document.getElementById('analysis-files');
        preview = document.getElementById('analysis-file-preview');
        list = document.getElementById('analysis-file-list');
    } else if (type === 'comparison-a') {
        input = document.getElementById('comparison-files-a');
        preview = document.getElementById('comparison-a-file-preview');
        list = document.getElementById('comparison-a-file-list');
    } else if (type === 'comparison-b') {
        input = document.getElementById('comparison-files-b');
        preview = document.getElementById('comparison-b-file-preview');
        list = document.getElementById('comparison-b-file-list');
    }
    if (!input || !preview || !list) return;

    list.innerHTML = '';
    const files = Array.from(input.files);
    if (files.length > 0) {
        preview.style.display = 'block';
        files.forEach(file => {
            const li = document.createElement('li');
            li.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
            list.appendChild(li);
        });
    } else {
        preview.style.display = 'none';
    }
}

function previewChatFiles() {
    const input = document.getElementById('chat-files');
    const preview = document.getElementById('chat-file-preview');
    preview.innerHTML = '';
    const files = Array.from(input.files);
    if (files.length > 0) {
        files.forEach(file => {
            const div = document.createElement('div');
            div.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
            preview.appendChild(div);
        });
    }
    const fileNameSpan = document.getElementById('chat-file-name');
    fileNameSpan.textContent = files.length > 0 ? files.map(f => f.name).join(', ') : 'No file chosen';
}

// ----------------------------
// Copy to Clipboard
// ----------------------------
function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    });
}

// ----------------------------
// Toast Notification
// ----------------------------
function showToast(message) {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-message');
    msg.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ----------------------------
// Document Analysis Submission
// ----------------------------
document.getElementById('analysis-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const files = document.getElementById('analysis-files').files;
    if (!files.length) return showToast('Please select files to analyze.');

    const formData = new FormData();
    for (let file of files) formData.append('files', file);

    const loader = document.getElementById('analysis-loader');
    loader.style.display = 'block';

    try {
        const res = await fetch('/document_analysis', { method: 'POST', body: formData });
        const data = await res.json();
        loader.style.display = 'none';
        if (data.success) {
            document.getElementById('analysis-result').style.display = 'block';
            document.getElementById('analysis-result-content').innerText = JSON.stringify(data.result.analysis, null, 2);
        } else {
            showToast(data.error || 'Analysis failed.');
        }
    } catch (err) {
        loader.style.display = 'none';
        showToast('Server error. Try again.');
    }
});

// ----------------------------
// Document Comparison Submission
// ----------------------------
document.getElementById('comparison-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const filesA = document.getElementById('comparison-files-a').files;
    const filesB = document.getElementById('comparison-files-b').files;
    if (!filesA.length || !filesB.length) return showToast('Please select both sets of files.');

    const formData = new FormData();
    for (let file of filesA) formData.append('files_a', file);
    for (let file of filesB) formData.append('files_b', file);

    const loader = document.getElementById('comparison-loader');
    loader.style.display = 'block';

    try {
        const res = await fetch('/document_comparison', { method: 'POST', body: formData });
        const data = await res.json();
        loader.style.display = 'none';
        if (data.success) {
            document.getElementById('comparison-result').style.display = 'block';
            document.getElementById('comparison-result-content').innerText = JSON.stringify(data.result.comparison, null, 2);
        } else {
            showToast(data.error || 'Comparison failed.');
        }
    } catch (err) {
        loader.style.display = 'none';
        showToast('Server error. Try again.');
    }
});

// ----------------------------
// Chatbot
// ----------------------------
function handleChatKeypress(e) {
    if (e.key === 'Enter') sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const filesInput = document.getElementById('chat-files');
    const question = input.value.trim();
    if (!question) return;

    appendChatMessage('user', question);
    input.value = '';

    const formData = new FormData();
    formData.append('question', question);
    if (filesInput.files.length > 0) {
        for (let file of filesInput.files) formData.append('files', file);
    }

    const status = document.getElementById('chat-upload-status');
    status.style.display = 'block';
    status.innerText = 'Processing...';

    try {
        const res = await fetch('/document_qa_chat', { method: 'POST', body: formData });
        const data = await res.json();
        status.style.display = 'none';
        if (data.success) {
            appendChatMessage('bot', data.result.latest_answer);
        } else {
            showToast(data.error || 'Failed to get answer.');
        }
    } catch (err) {
        status.style.display = 'none';
        showToast('Server error. Try again.');
    }
}

function appendChatMessage(sender, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
    div.innerHTML = `<div>${text}</div><div class="message-time">${new Date().toLocaleTimeString()}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
