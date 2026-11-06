/**
 * TAIO RemakeStudio: Voice Management & Sample Player (voices.js)
 * Theo Mục 5.4, 5.5:
 * - Chọn giọng, nhớ lựa chọn qua localStorage.
 * - Phát mẫu câu 3 giây qua /api/voices/{id}/sample.
 * - Làm mờ giọng có engine chưa sẵn sàng kèm lý do.
 */

let availableVoices = [];

function initVoices(voices) {
    availableVoices = voices || [];
    const select = document.getElementById('voice-select-box');
    if (!select) return;

    select.innerHTML = '';
    let savedVoice = null;
    try {
        savedVoice = localStorage.getItem('taio_selected_voice');
    } catch (e) {
        console.warn('localStorage không khả dụng:', e);
    }

    let defaultOptionSelected = false;

    availableVoices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.name} (${v.region} - ${v.gender === 'female' ? 'Nữ' : 'Nam'})`;
        
        if (!v.enabled) {
            opt.disabled = true;
            opt.textContent += ` [${v.disabled_reason || 'Chưa sẵn sàng'}]`;
        } else if (!defaultOptionSelected) {
            if (savedVoice === v.id || !savedVoice) {
                opt.selected = true;
                defaultOptionSelected = true;
            }
        }

        select.appendChild(opt);
    });

    select.addEventListener('change', () => {
        try {
            localStorage.setItem('taio_selected_voice', select.value);
        } catch (e) {}
    });
}

function playVoiceSample() {
    const select = document.getElementById('voice-select-box');
    const btn = document.getElementById('preview-voice-btn');
    const audio = document.getElementById('voice-sample-player');
    if (!select || !audio) return;

    const voiceId = select.value;
    if (!voiceId) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang tải...</span>';

    audio.src = `/api/voices/${voiceId}/sample`;
    audio.play()
        .then(() => {
            btn.innerHTML = '<i class="fa-solid fa-volume-high text-emerald-400"></i> <span>Đang phát...</span>';
            audio.onended = () => resetVoiceBtn();
            audio.onerror = () => {
                alert('Không thể phát âm thanh mẫu của giọng này.');
                resetVoiceBtn();
            };
        })
        .catch(err => {
            console.error('Lỗi phát mẫu giọng:', err);
            resetVoiceBtn();
        });
}

function resetVoiceBtn() {
    const btn = document.getElementById('preview-voice-btn');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> <span>Nghe thử</span>';
    }
}
