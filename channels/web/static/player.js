/**
 * TAIO RemakeStudio: Interactive Player & Synced Subtitles (player.js)
 * Theo Mục 5.7:
 * - Hiển thị phụ đề song ngữ chạy theo câu đang nói.
 * - Bấm vào câu nào thì nhảy tới giây tương ứng.
 * - Danh sách file tải về phân loại rõ ràng (TXT, SRT, DOCX, MP3, MP4).
 */

let activeTranscriptSegments = [];

function renderInteractiveTranscript(segments) {
    activeTranscriptSegments = segments || [];
    const container = document.getElementById('synced-transcript-box');
    if (!container) return;

    container.innerHTML = '';
    if (activeTranscriptSegments.length === 0) {
        container.innerHTML = '<span class="text-slate-500">Chưa có dòng phụ đề.</span>';
        return;
    }

    activeTranscriptSegments.forEach((seg, idx) => {
        const item = document.createElement('div');
        item.className = 'p-2 rounded-lg hover:bg-slate-900 cursor-pointer transition border border-transparent hover:border-slate-800 seg-row';
        item.id = `seg-row-${idx}`;
        item.onclick = () => seekToSegment(seg.start);

        const stStr = formatSecs(seg.start);
        const enStr = formatSecs(seg.end);

        item.innerHTML = `
            <div class="flex items-center space-x-2 text-[10px] text-blue-400 font-mono">
                <i class="fa-regular fa-clock"></i>
                <span>[${stStr} - ${enStr}]</span>
            </div>
            <div class="text-slate-400 text-xs mt-0.5">${escapeHtml(seg.original_text)}</div>
            ${seg.translated_text ? `<div class="text-emerald-300 font-semibold text-xs mt-0.5">${escapeHtml(seg.translated_text)}</div>` : ''}
        `;
        container.appendChild(item);
    });
}

function seekToSegment(timeSec) {
    const audio = document.getElementById('main-audio-player');
    const video = document.getElementById('main-video-player');

    if (audio && !audio.paused) {
        audio.currentTime = timeSec;
    } else if (video && !video.paused) {
        video.currentTime = timeSec;
    }
}

function renderDownloadFiles(files) {
    const grid = document.getElementById('download-files-grid');
    if (!grid) return;

    grid.innerHTML = '';
    const kindConfigs = {
        'subtitles': { icon: 'fa-closed-captioning', color: 'bg-emerald-600' },
        'text': { icon: 'fa-file-lines', color: 'bg-slate-700' },
        'docx': { icon: 'fa-file-word', color: 'bg-blue-600' },
        'audio': { icon: 'fa-file-audio', color: 'bg-purple-600' },
        'video': { icon: 'fa-file-video', color: 'bg-rose-600' },
        'summary': { icon: 'fa-brain', color: 'bg-amber-600' }
    };

    files.forEach(f => {
        const conf = kindConfigs[f.kind] || { icon: 'fa-download', color: 'bg-slate-700' };
        const a = document.createElement('a');
        a.href = f.download_url;
        a.download = f.filename || '';
        a.className = `${conf.color} hover:opacity-90 py-2.5 px-3 rounded-xl flex items-center justify-center space-x-2 text-xs font-bold text-white transition`;
        a.innerHTML = `<i class="fa-solid ${conf.icon}"></i> <span>${escapeHtml(f.label)}</span>`;
        grid.appendChild(a);
    });
}

function formatSecs(secs) {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
