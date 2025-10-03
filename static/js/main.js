// ===== CONFIGURATION & CONSTANTS =====
const CONFIG = {
    endpoints: {
        analysis: '/document_analysis',
        comparison: '/document_comparison',
        qaChat: '/document_qa_chat',
        qaSession: '/document_qa_chat/session',
        qaEnd: '/document_qa_chat/end',
        qaClear: '/document_qa_chat/clear'
    },
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedFileTypes: ['.pdf', '.doc', '.docx', '.txt'],
    maxFiles: 5,
    toastDuration: 4000,
    apiTimeout: 30000 // 30 seconds
};

// ===== STATE MANAGEMENT =====
const AppState = {
    currentChatSession: null,
    currentConversationHistory: [],
    activeUploads: new Map(),
    abortControllers: new Map()
};

// ===== DOM ELEMENTS CACHE =====
const Elements = {
    // Service sections
    serviceSections: null,
    
    // Analysis
    analysisForm: null,
    analysisFiles: null,
    analysisLoader: null,
    analysisSubmitBtn: null,
    analysisResult: null,
    analysisResultContent: null,
    
    // Comparison
    comparisonForm: null,
    comparisonFilesA: null,
    comparisonFilesB: null,
    comparisonLoader: null,
    comparisonSubmitBtn: null,
    comparisonResult: null,
    comparisonResultContent: null,
    
    // Chat
    chatUploadSection: null,
    chatInterface: null,
    chatUploadForm: null,
    chatFiles: null,
    chatFileNames: null,
    chatUploadLoader: null,
    chatUploadBtn: null,
    chatUploadStatus: null,
    chatMessages: null,
    chatInput: null,
    chatSendBtn: null,
    activeFilesList: null,
    currentSessionId: null
};

// ===== TOAST NOTIFICATION SYSTEM =====
class ToastManager {
    constructor() {
        this.toast = null;
        this.toastMessage = null;
        this.toastType = null;
        this.timeoutId = null;
        this.initialize();
    }

    initialize() {
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toast-message');
        this.toastType = document.getElementById('toast-type');
        
        if (!this.toast || !this.toastMessage || !this.toastType) {
            console.warn('Toast elements not found');
            return;
        }

        // Auto-hide on click
        this.toast.addEventListener('click', (e) => {
            if (!e.target.closest('.toast-close')) {
                this.hide();
            }
        });
    }

    show(message, type = 'success', duration = CONFIG.toastDuration) {
        if (!this.toast || !this.toastMessage || !this.toastType) {
            console.warn('Toast system not initialized');
            return;
        }

        // Clear any existing timeout
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        // Remove any existing classes
        this.toast.classList.remove('success', 'error', 'warning', 'info', 'show', 'hiding');

        // Set content and styling
        this.toastMessage.textContent = message;
        this.toastType.textContent = this.getTypeText(type);
        this.toast.classList.add(type);

        // Set appropriate icon
        const icon = this.toast.querySelector('.toast-icon i');
        if (icon) {
            icon.className = this.getIconClass(type);
        }

        // Show toast
        setTimeout(() => {
            this.toast.classList.add('show');
        }, 10);

        // Auto hide
        if (duration > 0) {
            this.timeoutId = setTimeout(() => {
                this.hide();
            }, duration);
        }
    }

    hide() {
        if (!this.toast) return;

        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        this.toast.classList.add('hiding');
        this.toast.classList.remove('show');

        // Remove hiding class after animation
        setTimeout(() => {
            this.toast.classList.remove('hiding');
        }, 300);
    }

    getTypeText(type) {
        const typeMap = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Information'
        };
        return typeMap[type] || 'Notification';
    }

    getIconClass(type) {
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return iconMap[type] || 'fas fa-bell';
    }
}

// Initialize toast manager
const toastManager = new ToastManager();

// Global toast functions
function showToast(message, type = 'success', duration = CONFIG.toastDuration) {
    toastManager.show(message, type, duration);
}

function hideToast() {
    toastManager.hide();
}

// Convenience methods for different toast types
const Toast = {
    success: (message, duration) => showToast(message, 'success', duration),
    error: (message, duration) => showToast(message, 'error', duration),
    warning: (message, duration) => showToast(message, 'warning', duration),
    info: (message, duration) => showToast(message, 'info', duration),
    hide: () => hideToast()
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    cacheDOMElements();
    initializeEventListeners();
    initializeChatInterface();
    loadExistingSession();
    
    console.log('कानूनKompanion initialized successfully');
}

function cacheDOMElements() {
    // Service sections
    Elements.serviceSections = document.querySelectorAll('.service-section');
    
    // Analysis elements
    Elements.analysisForm = document.getElementById('analysis-form');
    Elements.analysisFiles = document.getElementById('analysis-files');
    Elements.analysisLoader = document.getElementById('analysis-loader');
    Elements.analysisSubmitBtn = document.getElementById('analysis-submit-btn');
    Elements.analysisResult = document.getElementById('analysis-result');
    Elements.analysisResultContent = document.getElementById('analysis-result-content');
    
    // Comparison elements
    Elements.comparisonForm = document.getElementById('comparison-form');
    Elements.comparisonFilesA = document.getElementById('comparison-files-a');
    Elements.comparisonFilesB = document.getElementById('comparison-files-b');
    Elements.comparisonLoader = document.getElementById('comparison-loader');
    Elements.comparisonSubmitBtn = document.getElementById('comparison-submit-btn');
    Elements.comparisonResult = document.getElementById('comparison-result');
    Elements.comparisonResultContent = document.getElementById('comparison-result-content');
    
    // Chat elements
    Elements.chatUploadSection = document.getElementById('chat-upload-section');
    Elements.chatInterface = document.getElementById('chat-interface');
    Elements.chatUploadForm = document.getElementById('chat-upload-form');
    Elements.chatFiles = document.getElementById('chat-files');
    Elements.chatFileNames = document.getElementById('chat-file-names');
    Elements.chatUploadLoader = document.getElementById('chat-upload-loader');
    Elements.chatUploadBtn = document.getElementById('chat-upload-btn');
    Elements.chatUploadStatus = document.getElementById('chat-upload-status');
    Elements.chatMessages = document.getElementById('chat-messages');
    Elements.chatInput = document.getElementById('chat-input');
    Elements.chatSendBtn = document.getElementById('chat-send-btn');
    Elements.activeFilesList = document.getElementById('active-files-list');
    Elements.currentSessionId = document.getElementById('current-session-id');
}

function initializeEventListeners() {
    // Analysis form
    if (Elements.analysisForm) {
        Elements.analysisForm.addEventListener('submit', handleAnalysisSubmit);
    }
    
    // Comparison form
    if (Elements.comparisonForm) {
        Elements.comparisonForm.addEventListener('submit', handleComparisonSubmit);
    }
    
    // Chat input keypress
    if (Elements.chatInput) {
        Elements.chatInput.addEventListener('keypress', handleChatKeypress);
    }
    
    // Global error handler
    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handlePromiseRejection);
}

// ===== SERVICE MANAGEMENT =====
function showService(serviceId) {
    // Hide all service sections
    Elements.serviceSections.forEach(sec => {
        sec.classList.remove('active');
        sec.style.display = 'none';
    });
    
    // Show target section
    const target = document.getElementById(serviceId);
    if (target) {
        target.classList.add('active');
        target.style.display = 'block';
        window.scrollTo({ top: target.offsetTop - 80, behavior: 'smooth' });
    }
}

function goToHome() {
    Elements.serviceSections.forEach(sec => {
        sec.classList.remove('active');
        sec.style.display = 'none';
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showServicesSection() {
    const servicesSection = document.getElementById('services-section');
    if (servicesSection) {
        servicesSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// ===== FILE HANDLING =====
function validateFiles(files, maxFiles = CONFIG.maxFiles) {
    const errors = [];
    
    if (!files || files.length === 0) {
        errors.push('Please select at least one file.');
        return errors;
    }
    
    if (files.length > maxFiles) {
        errors.push(`Maximum ${maxFiles} files allowed. You selected ${files.length}.`);
    }
    
    for (let file of files) {
        // Check file size
        if (file.size > CONFIG.maxFileSize) {
            errors.push(`File "${file.name}" is too large. Maximum size is ${formatFileSize(CONFIG.maxFileSize)}.`);
        }
        
        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!CONFIG.allowedFileTypes.includes(fileExtension)) {
            errors.push(`File "${file.name}" has an unsupported format. Allowed formats: ${CONFIG.allowedFileTypes.join(', ')}`);
        }
        
        // Check for empty files
        if (file.size === 0) {
            errors.push(`File "${file.name}" is empty.`);
        }
    }
    
    return errors;
}

function previewFiles(type) {
    const config = {
        'analysis': {
            input: 'analysis-files',
            preview: 'analysis-file-preview',
            list: 'analysis-file-list'
        },
        'comparison-a': {
            input: 'comparison-files-a',
            preview: 'comparison-a-file-preview',
            list: 'comparison-a-file-list'
        },
        'comparison-b': {
            input: 'comparison-files-b',
            preview: 'comparison-b-file-preview',
            list: 'comparison-b-file-list'
        }
    };
    
    const { input, preview, list } = config[type];
    const fileInput = document.getElementById(input);
    const previewDiv = document.getElementById(preview);
    const fileList = document.getElementById(list);
    
    if (!fileInput || !previewDiv || !fileList) return;
    
    fileList.innerHTML = '';
    const files = Array.from(fileInput.files);
    
    if (files.length > 0) {
        previewDiv.style.display = 'block';
        files.forEach(file => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="file-name">${escapeHtml(file.name)}</span>
                <span class="file-size">(${formatFileSize(file.size)})</span>
            `;
            fileList.appendChild(li);
        });
    } else {
        previewDiv.style.display = 'none';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ===== UTILITY FUNCTIONS =====
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        Toast.error('Element not found');
        return;
    }
    
    const text = element.innerText || element.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        Toast.success('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        Toast.error('Failed to copy text');
    });
}

function toggleLoader(loaderId, show) {
    const loader = document.getElementById(loaderId);
    if (loader) {
        loader.style.display = show ? 'block' : 'none';
    }
}

function setButtonState(button, isLoading, loadingText = 'Processing...') {
    if (!button) return;
    
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${loadingText}`;
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        
        // Reset file previews
        const previews = form.querySelectorAll('.file-preview');
        previews.forEach(preview => {
            preview.style.display = 'none';
        });
        
        // Reset result containers
        const results = form.querySelectorAll('.result-container');
        results.forEach(result => {
            result.style.display = 'none';
        });
    }
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== API CLIENT =====
async function apiCall(endpoint, options = {}) {
    const abortController = new AbortController();
    const requestId = Date.now().toString();
    
    AppState.abortControllers.set(requestId, abortController);
    
    try {
        const response = await fetch(endpoint, {
            ...options,
            signal: abortController.signal,
            headers: {
                'Accept': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request was cancelled');
        }
        throw error;
    } finally {
        AppState.abortControllers.delete(requestId);
    }
}

function cancelAllRequests() {
    AppState.abortControllers.forEach(controller => {
        controller.abort();
    });
    AppState.abortControllers.clear();
}

// ===== DOCUMENT ANALYSIS =====
async function handleAnalysisSubmit(e) {
    e.preventDefault();
    
    const files = Elements.analysisFiles?.files;
    if (!files || files.length === 0) {
        Toast.error('Please select files to analyze.');
        return;
    }
    
    const validationErrors = validateFiles(files);
    if (validationErrors.length > 0) {
        validationErrors.forEach(error => Toast.error(error));
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    
    // UI updates
    toggleLoader('analysis-loader', true);
    setButtonState(Elements.analysisSubmitBtn, true, 'Analyzing...');
    
    try {
        const data = await apiCall(CONFIG.endpoints.analysis, {
            method: 'POST',
            body: formData
        });
        
        if (data.success) {
            Elements.analysisResult.style.display = 'block';
            Elements.analysisResultContent.textContent = 
                JSON.stringify(data.result.analysis, null, 2);
            Toast.success('Document analysis completed successfully!');
        } else {
            Toast.error(data.error || 'Analysis failed. Please try again.');
        }
    } catch (error) {
        console.error('Analysis error:', error);
        Toast.error(error.message || 'Server error. Please try again later.');
    } finally {
        toggleLoader('analysis-loader', false);
        setButtonState(Elements.analysisSubmitBtn, false);
    }
}

// ===== DOCUMENT COMPARISON =====
async function handleComparisonSubmit(e) {
    e.preventDefault();
    
    const filesA = Elements.comparisonFilesA?.files;
    const filesB = Elements.comparisonFilesB?.files;
    
    if (!filesA?.length || !filesB?.length) {
        Toast.error('Please select files for both sets.');
        return;
    }
    
    const errorsA = validateFiles(filesA);
    const errorsB = validateFiles(filesB);
    const allErrors = [...errorsA, ...errorsB];
    
    if (allErrors.length > 0) {
        allErrors.forEach(error => Toast.error(error));
        return;
    }
    
    const formData = new FormData();
    for (let file of filesA) formData.append('files_a', file);
    for (let file of filesB) formData.append('files_b', file);
    
    // UI updates
    toggleLoader('comparison-loader', true);
    setButtonState(Elements.comparisonSubmitBtn, true, 'Comparing...');
    
    try {
        const data = await apiCall(CONFIG.endpoints.comparison, {
            method: 'POST',
            body: formData
        });
        
        if (data.success) {
            Elements.comparisonResult.style.display = 'block';
            Elements.comparisonResultContent.textContent = 
                JSON.stringify(data.result.comparison, null, 2);
            Toast.success('Document comparison completed successfully!');
        } else {
            Toast.error(data.error || 'Comparison failed. Please try again.');
        }
    } catch (error) {
        console.error('Comparison error:', error);
        Toast.error(error.message || 'Server error. Please try again later.');
    } finally {
        toggleLoader('comparison-loader', false);
        setButtonState(Elements.comparisonSubmitBtn, false);
    }
}

// ===== CHATBOT FUNCTIONALITY =====
function initializeChatInterface() {
    if (!Elements.chatFiles || !Elements.chatFileNames) return;
    
    Elements.chatFiles.addEventListener('change', function() {
        const files = Array.from(this.files);
        Elements.chatFileNames.textContent = files.length > 0 
            ? `${files.length} file(s) selected: ${files.map(f => f.name).join(', ')}` 
            : 'No file chosen';
    });
    
    if (Elements.chatUploadForm) {
        Elements.chatUploadForm.addEventListener('submit', handleDocumentUpload);
    }
}

async function handleDocumentUpload(e) {
    e.preventDefault();
    
    const files = Elements.chatFiles?.files;
    if (!files || files.length === 0) {
        Toast.error('Please select files to upload.');
        return;
    }
    
    const validationErrors = validateFiles(files);
    if (validationErrors.length > 0) {
        validationErrors.forEach(error => Toast.error(error));
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    
    // UI updates
    toggleLoader('chat-upload-loader', true);
    setButtonState(Elements.chatUploadBtn, true, 'Uploading...');
    Elements.chatUploadStatus.style.display = 'block';
    Elements.chatUploadStatus.textContent = 'Uploading and processing documents...';
    
    try {
        const data = await apiCall(CONFIG.endpoints.qaChat, {
            method: 'POST',
            body: formData
        });
        
        if (data.success) {
            switchToChatInterface(data.result);
            Toast.success('Documents uploaded successfully! You can now chat with your documents.');
        } else {
            Toast.error(data.error || 'Upload failed. Please try again.');
        }
    } catch (error) {
        console.error('Upload error:', error);
        Toast.error(error.message || 'Network error. Please try again.');
    } finally {
        toggleLoader('chat-upload-loader', false);
        setButtonState(Elements.chatUploadBtn, false);
        Elements.chatUploadStatus.style.display = 'none';
    }
}

function switchToChatInterface(result) {
    Elements.chatUploadSection.style.display = 'none';
    Elements.chatInterface.style.display = 'block';
    
    // Update session state
    AppState.currentChatSession = result.session;
    AppState.currentConversationHistory = result.conversation_history || [];
    
    // Display uploaded files
    const uploadedFiles = result.uploaded_files || [];
    Elements.activeFilesList.textContent = uploadedFiles.join(', ');
    
    updateSessionDisplay();
    displayConversationHistory();
}

function displayConversationHistory() {
    if (!Elements.chatMessages) return;
    
    Elements.chatMessages.innerHTML = '';
    
    if (AppState.currentConversationHistory.length === 0) {
        appendChatMessage('bot', 'Hello! I\'m your कानून-DocChatbot. I\'ve analyzed your documents and I\'m ready to answer your questions.');
        return;
    }
    
    AppState.currentConversationHistory.forEach(entry => {
        if (entry.type === 'document_upload') {
            // Don't show upload message in chat - it's handled by toast
        } else if (entry.type === 'qa') {
            appendChatMessage('user', entry.question);
            appendChatMessage('bot', entry.answer);
        }
    });
}

function handleChatKeypress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.stopImmediatePropagation(); // Add this line
        console.log('Enter key handled');
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const question = Elements.chatInput?.value.trim();
    
    if (!question) {
        Toast.warning('Please enter a question');
        return;
    }
    
    if (!AppState.currentChatSession) {
        Toast.error('Please upload documents first');
        return;
    }
    
    // Show user message immediately
    appendChatMessage('user', question);
    Elements.chatInput.value = '';
    Elements.chatInput.disabled = true;
    
    setButtonState(Elements.chatSendBtn, true, 'Sending...');
    
    try {
        const formData = new FormData();
        formData.append('question', question);
        
        const data = await apiCall(CONFIG.endpoints.qaChat, {
            method: 'POST',
            body: formData
        });
        
        if (data.success) {
            AppState.currentChatSession = data.result.session;
            AppState.currentConversationHistory = data.result.conversation_history;
            updateSessionDisplay();
            
            const latestAnswer = data.result.latest_answer || "I've processed your request.";
            appendChatMessage('bot', latestAnswer);
        } else {
            appendChatMessage('bot', "I apologize, but I'm having trouble processing your request. Please try again.");
            Toast.error(data.error || 'Request failed');
        }
    } catch (error) {
        console.error('Chat error:', error);
        appendChatMessage('bot', "I'm experiencing connection issues. Please check your internet and try again.");
        Toast.error(error.message || 'Network error - please try again');
    } finally {
        Elements.chatInput.disabled = false;
        Elements.chatInput.focus();
        setButtonState(Elements.chatSendBtn, false);
    }
}

async function saveAndEndChat() {
    if (!AppState.currentChatSession) {
        Toast.warning('No active chat session to save');
        return;
    }
    
    try {
        const data = await apiCall(CONFIG.endpoints.qaEnd, {
            method: 'POST'
        });
        
        if (data.success) {
            Toast.success('Chat session saved successfully');
            resetChatInterface();
        } else {
            Toast.error(data.error || 'Failed to save session');
        }
    } catch (error) {
        console.error('End session error:', error);
        Toast.error(error.message || 'Error saving chat session');
    }
}

async function clearChatSession() {
    if (!AppState.currentChatSession) {
        Toast.warning('No active chat session to clear');
        return;
    }
    
    if (!confirm('Are you sure you want to clear the current chat session? This action cannot be undone.')) {
        return;
    }
    
    try {
        const data = await apiCall(CONFIG.endpoints.qaClear, {
            method: 'POST'
        });
        
        if (data.success) {
            Toast.success('Chat session cleared');
            resetChatInterface();
        } else {
            Toast.error(data.error || 'Failed to clear session');
        }
    } catch (error) {
        console.error('Clear session error:', error);
        Toast.error(error.message || 'Error clearing chat session');
    }
}

function resetChatInterface() {
    Elements.chatUploadSection.style.display = 'block';
    Elements.chatInterface.style.display = 'none';
    
    // Reset form and state
    if (Elements.chatUploadForm) {
        Elements.chatUploadForm.reset();
    }
    Elements.chatFileNames.textContent = 'No file chosen';
    Elements.chatMessages.innerHTML = '';
    Elements.activeFilesList.textContent = '';
    Elements.chatInput.value = '';
    
    // Reset state
    AppState.currentChatSession = null;
    AppState.currentConversationHistory = [];
    updateSessionDisplay();
    
    // Add initial message
    appendChatMessage('bot', 'Hello! I\'m your कानून-DocChatbot. Upload your documents to get started.');
}

async function loadExistingSession() {
    try {
        const data = await apiCall(CONFIG.endpoints.qaSession);
        
        if (data.success && data.result.session) {
            switchToChatInterface(data.result);
            Toast.info('Previous chat session restored');
        }
    } catch (error) {
        console.log('No existing session found or error loading session:', error);
    }
}

function appendChatMessage(sender, text) {
    if (!Elements.chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const timestamp = new Date().toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    messageDiv.innerHTML = `
        <div class="message-content">${escapeHtml(text)}</div>
        <div class="message-time">${timestamp}</div>
    `;
    
    Elements.chatMessages.appendChild(messageDiv);
    Elements.chatMessages.scrollTop = Elements.chatMessages.scrollHeight;
}

function updateSessionDisplay() {
    if (Elements.currentSessionId) {
        Elements.currentSessionId.textContent = AppState.currentChatSession || 'None';
    }
}

// ===== ERROR HANDLING =====
function handleGlobalError(event) {
    console.error('Global error:', event.error);
    Toast.error('An unexpected error occurred');
}

function handlePromiseRejection(event) {
    console.error('Unhandled promise rejection:', event.reason);
    Toast.error('An unexpected error occurred');
}

// ===== SESSION MANAGEMENT =====
window.addEventListener('beforeunload', function(e) {
    if (AppState.currentChatSession) {
        // Attempt to save session before leaving
        fetch(CONFIG.endpoints.qaEnd, {
            method: 'POST',
            keepalive: true
        }).catch(err => console.log('Auto-save attempted'));
    }
    
    // Cancel any ongoing requests
    cancelAllRequests();
});

// ===== PUBLIC API =====
// Expose functions to global scope for HTML onclick handlers
window.showService = showService;
window.goToHome = goToHome;
window.showServicesSection = showServicesSection;
window.previewFiles = previewFiles;
window.copyToClipboard = copyToClipboard;
window.handleChatKeypress = handleChatKeypress;
window.sendChatMessage = sendChatMessage;
window.saveAndEndChat = saveAndEndChat;
window.clearChatSession = clearChatSession;
window.showToast = showToast;
window.hideToast = hideToast;
window.Toast = Toast;