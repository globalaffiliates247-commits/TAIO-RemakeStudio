/**
 * TAIO RemakeStudio: Real Step Progress Tracker (steps.js)
 * Theo Mục 5.6:
 * - Hiển thị tiến trình thật theo từng bước (Tải -> Chép lời -> Dịch -> Tổng hợp).
 * - Trạng thái: Đang chạy / ✓ Hoàn thành / ✗ Lỗi / Bỏ qua.
 * - Bỏ hoàn toàn thanh phần trăm đặt cứng.
 */

function renderTaskSteps(steps) {
    const list = document.getElementById('steps-list');
    const box = document.getElementById('steps-progress-box');
    if (!list || !box) return;

    box.hidden = false;
    list.innerHTML = '';

    steps.forEach((step, idx) => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between p-2.5 rounded-xl border text-xs transition';

        let icon = '<i class="fa-regular fa-circle text-slate-500"></i>';
        let statusClass = 'border-slate-800 bg-slate-900/40 text-slate-400';
        let engineTag = step.engine ? `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">${step.engine}</span>` : '';

        if (step.status === 'running') {
            icon = '<i class="fa-solid fa-circle-notch fa-spin text-blue-400"></i>';
            statusClass = 'border-blue-500/50 bg-blue-950/20 text-blue-200';
        } else if (step.status === 'completed') {
            icon = '<i class="fa-solid fa-circle-check text-emerald-400"></i>';
            statusClass = 'border-emerald-800/40 bg-emerald-950/20 text-emerald-300';
        } else if (step.status === 'failed') {
            icon = '<i class="fa-solid fa-circle-xmark text-rose-400"></i>';
            statusClass = 'border-rose-800/40 bg-rose-950/20 text-rose-300';
        } else if (step.status === 'skipped') {
            icon = '<i class="fa-solid fa-forward text-slate-600"></i>';
            statusClass = 'border-slate-800/40 bg-slate-900/20 text-slate-500';
        }

        item.className += ' ' + statusClass;
        item.innerHTML = `
            <div class="flex items-center space-x-2.5">
                <span class="text-sm">${icon}</span>
                <span class="font-semibold">${step.name}</span>
            </div>
            <div class="flex items-center space-x-2">
                ${engineTag}
                ${step.error ? `<span class="text-[11px] text-rose-400 font-normal">${step.error}</span>` : ''}
            </div>
        `;
        list.appendChild(item);
    });
}
