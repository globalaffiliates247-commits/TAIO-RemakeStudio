/**
 * TAIO RemakeStudio: Main Application Controller (app.js)
 * Theo Mục 5:
 * - Bước 1: Dán link / Chọn file -> Probe tự động
 * - Bước 2: Chọn ý định (4 thẻ), áp dụng ma trận 5.3
 * - Bước 3: Xem tiến trình thật theo bước (steps.js)
 * - Bước 4: Xem kết quả Mức 1 & Mở rộng Mức 2-4 qua /api/task/{id}/extend
 */

let currentSourceMode = 'link';
let probedInputData = null;
let selectedIntent = 'listen_vi';
let activeTaskId = null;
let taskPollTimer = null;
let systemConfig = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadSystemReadinessAndConfig();
    updateIntentMatrixFields();
});

async function loadSystemReadinessAndConfig() {
    try {
        const [confRes, readyRes] = await Promise.all([
            fetch('/api/config'),
            fetch('/api/readiness')
        ]);
        systemConfig = await confRes.json();
        const readiness = await readyRes.json();

        // 1. Cập nhật Badge Readiness trên Header
        const dot = document.getElementById('readiness-dot');
        const stText = document.getElementById('readiness-status-text');
        if (readiness.status === 'healthy') {
            dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400';
            stText.textContent = 'Hệ thống sẵn sàng 100%';
        } else {
            dot.className = 'w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse';
            stText.textContent = 'Cần cấu hình API Key';
        }

        // 2. Render Panel Tình trạng
        renderReadinessPanel(readiness);

        // 3. Khởi tạo danh sách Giọng đọc
        initVoices(systemConfig.voices);

        // 4. Cập nhật trạng thái Thẻ Ý Định (Mục 5.2: Không chạy được thì thẻ bị mờ kèm lý do)
        updateIntentCardsAvailability(readiness.intents);

    } catch (err) {
        console.error('Lỗi tải cấu hình hệ thống:', err);
    }
}

function toggleReadinessPanel() {
    const p = document.getElementById('readiness-panel');
    p.hidden = !p.hidden;
}

function renderReadinessPanel(readiness) {
    const grid = document.getElementById('readiness-steps-grid');
    const missBox = document.getElementById('readiness-missing-box');
    const missKeys = document.getElementById('readiness-missing-keys');

    if (!grid) return;
    grid.innerHTML = '';

    for (const [key, step] of Object.entries(readiness.steps)) {
        const card = document.createElement('div');
        card.className = `p-3 rounded-xl border ${step.ready ? 'border-emerald-800/40 bg-emerald-950/20' : 'border-amber-800/40 bg-amber-950/20'} text-xs space-y-1.5`;
        
        let enginesList = step.engines.map(e => {
            const mark = e.ready ? '<span class="text-emerald-400">✓</span>' : '<span class="text-slate-500">✗</span>';
            return `<div>${mark} ${e.name} ${!e.ready ? `<span class="text-[10px] text-amber-400/80">(${e.message})</span>` : ''}</div>`;
        }).join('');

        card.innerHTML = `
            <div class="font-bold text-white flex items-center justify-between">
                <span>${step.name}</span>
                <span class="${step.ready ? 'text-emerald-400' : 'text-amber-400'} font-normal text-[11px]">${step.ready ? 'Sẵn sàng' : 'Chưa đủ'}</span>
            </div>
            <div class="space-y-0.5 text-[11px] text-slate-300 font-mono">${enginesList}</div>
        `;
        grid.appendChild(card);
    }

    if (readiness.missing_env && readiness.missing_env.length > 0) {
        missBox.hidden = false;
        missKeys.textContent = readiness.missing_env.join(', ');
    } else {
        missBox.hidden = true;
    }
}

function updateIntentCardsAvailability(intentStates) {
    if (!intentStates) return;
    for (const [iId, state] of Object.entries(intentStates)) {
        const card = document.getElementById(`intent-card-${iId}`);
        if (!card) continue;

        const hint = card.querySelector('.disabled-hint');
        if (!state.enabled) {
            card.classList.add('disabled');
            if (hint) {
                hint.hidden = false;
                hint.textContent = `⚠️ ${state.reason}`;
            }
        } else {
            card.classList.remove('disabled');
            if (hint) hint.hidden = true;
        }
    }
}

function switchInputSource(mode) {
    currentSourceMode = mode;
    const linkBtn = document.getElementById('tab-link-btn');
    const fileBtn = document.getElementById('tab-file-btn');
    const linkBox = document.getElementById('source-link-box');
    const fileBox = document.getElementById('source-file-box');

    if (mode === 'link') {
        linkBtn.className = 'py-1 px-3 rounded-lg bg-blue-600 text-white font-semibold';
        fileBtn.className = 'py-1 px-3 rounded-lg text-slate-400 hover:text-white font-semibold';
        linkBox.hidden = false;
        fileBox.hidden = true;
    } else {
        fileBtn.className = 'py-1 px-3 rounded-lg bg-blue-600 text-white font-semibold';
        linkBtn.className = 'py-1 px-3 rounded-lg text-slate-400 hover:text-white font-semibold';
        fileBox.hidden = false;
        linkBox.hidden = true;
    }
}

async function probeMediaInput() {
    const url = document.getElementById('video-url-input').value.trim();
    const errBox = document.getElementById('probe-error-box');
    const errMsg = document.getElementById('probe-error-msg');
    const errBtn = document.getElementById('probe-error-action-btn');
    const card = document.getElementById('probe-card');

    if (currentSourceMode === 'link' && !url) return;

    errBox.hidden = true;
    const formData = new FormData();
    if (currentSourceMode === 'link') {
        formData.append('url', url);
    }

    try {
        const res = await fetch('/api/probe', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            const errDetail = data.detail || data;
            errMsg.textContent = errDetail.error || 'Link video không hợp lệ.';
            if (errDetail.action === 'upload') {
                errBtn.hidden = false;
                errBtn.textContent = 'Tải file lên';
            } else {
                errBtn.hidden = true;
            }
            errBox.hidden = false;
            card.hidden = true;
            probedInputData = null;
            return;
        }

        probedInputData = data;
        renderProbePreview(data);

    } catch (e) {
        errMsg.textContent = 'Lỗi kết nối máy chủ khi kiểm tra video.';
        errBox.hidden = false;
        card.hidden = true;
    }
}

function onLocalFilePicked(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        document.getElementById('file-label-text').textContent = `${file.name} (${(file.size / (1024*1024)).toFixed(1)} MB)`;

        const formData = new FormData();
        formData.append('file', file);

        fetch('/api/probe', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                probedInputData = data;
                renderProbePreview(data);
            })
            .catch(err => console.error(err));
    }
}

function renderProbePreview(data) {
    const card = document.getElementById('probe-card');
    card.hidden = false;

    document.getElementById('probe-title').textContent = data.title || 'Video tải lên';
    document.getElementById('probe-platform').textContent = (data.platform || 'Local').toUpperCase();
    document.getElementById('probe-duration').textContent = `${data.duration || 0}s`;
    document.getElementById('probe-cost').textContent = `Sẽ trừ khoảng ${data.cost_minutes || 1} phút hạn mức`;

    const img = document.getElementById('probe-thumb');
    const icon = document.getElementById('probe-thumb-icon');
    if (data.thumbnail) {
        img.src = data.thumbnail;
        img.classList.remove('hidden');
        icon.classList.add('hidden');
    } else {
        img.classList.add('hidden');
        icon.classList.remove('hidden');
    }
}

function selectIntent(intentId) {
    const card = document.getElementById(`intent-card-${intentId}`);
    if (card && card.classList.contains('disabled')) {
        return; // Thẻ bị mờ do thiếu key, không cho chọn
    }

    selectedIntent = intentId;
    document.querySelectorAll('.intent-card').forEach(c => c.classList.remove('selected'));
    if (card) card.classList.add('selected');

    updateIntentMatrixFields();
}

function updateIntentMatrixFields() {
    // Ma trận hiển thị trường Mục 5.3
    const fieldVoice = document.getElementById('field-voice-select');
    const fieldSong = document.getElementById('field-song-mode');
    const fieldTargetLang = document.getElementById('field-target-lang');

    if (selectedIntent === 'listen_vi') {
        fieldVoice.hidden = false;
        fieldSong.hidden = false;
        fieldTargetLang.hidden = true;
    } else if (selectedIntent === 'revoice') {
        fieldVoice.hidden = false;
        fieldSong.hidden = true;
        fieldTargetLang.hidden = true;
    } else if (selectedIntent === 'music_stems') {
        fieldVoice.hidden = true;
        fieldSong.hidden = true;
        fieldTargetLang.hidden = true;
    } else if (selectedIntent === 'translate_intl') {
        fieldVoice.hidden = false;
        fieldSong.hidden = true;
        fieldTargetLang.hidden = false;
    }
}

async function submitIntentProcess() {
    const btn = document.getElementById('start-task-btn');
    const card = document.getElementById(`intent-card-${selectedIntent}`);
    if (card && card.classList.contains('disabled')) {
        alert('Ý định này chưa sẵn sàng hoạt động do thiếu cấu hình API Key.');
        return;
    }

    const url = document.getElementById('video-url-input').value.trim();
    const inputId = probedInputData ? probedInputData.input_id : null;

    if (!url && !inputId) {
        alert('Vui lòng nhập link video hoặc chọn file tải lên!');
        return;
    }

    const formData = new FormData();
    if (inputId) formData.append('input_id', inputId);
    if (url) formData.append('video_url', url);
    formData.append('intent', selectedIntent);

    if (selectedIntent !== 'music_stems') {
        const vBox = document.getElementById('voice-select-box');
        if (vBox && vBox.value) formData.append('voice_id', vBox.value);
    }
    if (selectedIntent === 'translate_intl') {
        const tLang = document.getElementById('target-lang-select').value;
        formData.append('target_lang', tLang);
    }
    if (selectedIntent === 'listen_vi') {
        const songOn = document.getElementById('song-mode-checkbox').checked;
        formData.append('song_mode', songOn);
    }

    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');

    try {
        const res = await fetch('/api/process', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            const err = data.detail || data;
            alert(`Lỗi: ${err.error || 'Không thể tạo tác vụ'}`);
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
            return;
        }

        activeTaskId = data.task_id;
        startTaskPolling(activeTaskId);

    } catch (e) {
        alert(`Lỗi kết nối máy chủ: ${e}`);
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
}

function startTaskPolling(taskId) {
    if (taskPollTimer) clearInterval(taskPollTimer);

    taskPollTimer = setInterval(async () => {
        try {
            const res = await fetch(`/api/task/${taskId}`);
            const task = await res.json();

            // Cập nhật tiến trình thật theo bước (Mục 5.6)
            if (task.steps) {
                renderTaskSteps(task.steps);
            }

            if (task.status === 'completed') {
                clearInterval(taskPollTimer);
                showTaskResults(task);
                resetSubmitBtn();
            } else if (task.status === 'failed') {
                clearInterval(taskPollTimer);
                const err = task.error || {};
                alert(`Xử lý thất bại: ${err.error || 'Lỗi không xác định'}`);
                resetSubmitBtn();
            }
        } catch (e) {
            console.error('Lỗi polling task:', e);
        }
    }, 1000);
}

function resetSubmitBtn() {
    const btn = document.getElementById('start-task-btn');
    btn.disabled = false;
    btn.classList.remove('opacity-50', 'cursor-not-allowed');
}

function showTaskResults(task) {
    const view = document.getElementById('results-view');
    view.hidden = false;

    document.getElementById('res-video-title').textContent = (probedInputData && probedInputData.title) || 'Tác phẩm hoàn thành';
    document.getElementById('res-video-meta').textContent = `Ngôn ngữ: ${task.detected_language} | Luồng: ${task.flow || task.intent}`;

    // Render interactive transcript (Mục 5.7)
    if (task.transcript && task.transcript.segments) {
        renderInteractiveTranscript(task.transcript.segments);
    }

    // Render downloadable files
    if (task.files) {
        renderDownloadFiles(task.files);
    }

    view.scrollIntoView({ behavior: 'smooth' });
}

async function extendTask(targetLevel) {
    if (!activeTaskId) return;

    const vBox = document.getElementById('voice-select-box');
    const voiceId = vBox ? vBox.value : 'vi_north_female_1';

    const formData = new FormData();
    formData.append('level', targetLevel);
    formData.append('voice_id', voiceId);

    const btn = document.getElementById(`btn-extend-level${targetLevel}`);
    if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang xử lý...</span>';

    try {
        const res = await fetch(`/api/task/${activeTaskId}/extend`, { method: 'POST', body: formData });
        const updatedTask = await res.json();

        if (res.ok) {
            renderDownloadFiles(updatedTask.files);

            // Hiển thị player tương ứng
            const mediaRow = document.getElementById('media-preview-row');
            mediaRow.hidden = false;

            if (targetLevel === 2) {
                const aBox = document.getElementById('audio-preview-container');
                const aPlayer = document.getElementById('main-audio-player');
                aBox.hidden = false;
                aPlayer.src = `/api/download/${activeTaskId}/voice_vietnamese.mp3`;
                aPlayer.load();
            } else if (targetLevel === 3) {
                const vBox = document.getElementById('video-preview-container');
                const vPlayer = document.getElementById('main-video-player');
                vBox.hidden = false;
                vPlayer.src = `/api/download/${activeTaskId}/video_dubbed.mp4`;
                vPlayer.load();
            }

            if (btn) btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i> <span>Đã hoàn thành!</span>';
        } else {
            alert(`Lỗi mở rộng mức: ${updatedTask.detail ? updatedTask.detail.error : 'Thất bại'}`);
            if (btn) btn.innerHTML = 'Thử lại';
        }
    } catch (e) {
        alert(`Lỗi kết nối: ${e}`);
        if (btn) btn.innerHTML = 'Thử lại';
    }
}
