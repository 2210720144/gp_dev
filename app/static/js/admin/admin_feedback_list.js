document.addEventListener('DOMContentLoaded', function() {
    filterFeedback();
});

// 获取反馈列表并渲染
async function fetchFeedbackList(year, month, showAll) {
    const tbody = document.getElementById('feedback-table-body');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-text">正在加载数据...</td></tr>';

    try {
        const token = sessionStorage.getItem('token');
        const params = new URLSearchParams();
        if (showAll) {
            params.append('show_all', 'true');
        } else {
            if (year) params.append('year', year);
            if (month) params.append('month', month);
        }

        // 使用admin API
        const response = await fetch(`/api/admin/feedback/list?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const res = await response.json();
            if (res.code === 200) {
                // 更新年份下拉框
                updateYearFilter(res.data.available_years, res.data.current_filters.year);
                // 渲染表格
                renderTable(res.data.list);
            } else {
                tbody.innerHTML = `<tr><td colspan="5" class="loading-text">${res.msg || '加载失败'}</td></tr>`;
            }
        } else {
            // 如果接口不存在(404)，为了展示页面效果，这里可以模拟空数据或错误提示
            // 考虑到用户要求“后端逻辑暂时不用实现”，这里如果404，我们也可以不做处理，或者提示“接口未实现”
            tbody.innerHTML = `<tr><td colspan="5" class="loading-text">系统错误 (Status: ${response.status})</td></tr>`;
        }
    } catch (error) {
        console.error('Error fetching feedback list:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="loading-text">网络错误，请稍后重试</td></tr>';
    }
}

function updateYearFilter(years, currentYear) {
    const yearSelect = document.getElementById('year-filter');
    yearSelect.innerHTML = '';

    if (!years || years.length === 0) {
        const option = document.createElement('option');
        const thisYear = new Date().getFullYear();
        option.value = thisYear;
        option.textContent = `${thisYear}年`;
        yearSelect.appendChild(option);
        return;
    }

    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `${year}年`;
        if (String(year) === String(currentYear)) {
            option.selected = true;
        }
        yearSelect.appendChild(option);
    });
}

let feedbackListCache = []; // 全局缓存

function renderTable(data) {
    feedbackListCache = data || []; // 更新缓存
    const tbody = document.getElementById('feedback-table-body');
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-text">无法查询到反馈记录</td></tr>';
        return;
    }

    data.forEach(item => {
        const tr = document.createElement('tr');

        // 状态样式
        let statusClass = '';
        if (item.status === '已处理') {
            statusClass = 'status-processed';
        } else {
            statusClass = 'status-pending';
        }

        // 操作按钮逻辑
        let actionButtons = '';
        if (item.status === '待处理') {
            actionButtons = `
                <button class="action-btn btn-reply" onclick="openReplyModal('${item.feedback_id}')">回复</button>
            `;
        } else {
            actionButtons = `
                <button class="action-btn btn-view" onclick="openViewDetailModal('${item.feedback_id}')">查看详情</button>
            `;
        }

        // 多了一个 User ID 列
        tr.innerHTML = `
            <td>${item.feedback_id}</td>
            <td>${item.user_name || item.user_id}</td>
            <td>${item.title}</td>
            <td><span class="status-badge ${statusClass}">${item.status}</span></td>
            <td>${actionButtons}</td>
        `;

        tbody.appendChild(tr);
    });
}

function filterFeedback() {
    const showAll = document.getElementById('show-all-check').checked;
    const year = document.getElementById('year-filter').value;
    const month = document.getElementById('month-filter').value;

    fetchFeedbackList(year, month, showAll);
}

function toggleShowAll(checkbox) {
    const yearSelect = document.getElementById('year-filter');
    const monthSelect = document.getElementById('month-filter');

    if (checkbox.checked) {
        yearSelect.disabled = true;
        monthSelect.disabled = true;
        yearSelect.style.opacity = '0.5';
        monthSelect.style.opacity = '0.5';
    } else {
        yearSelect.disabled = false;
        monthSelect.disabled = false;
        yearSelect.style.opacity = '1';
        monthSelect.style.opacity = '1';
    }

    filterFeedback();
}

// 详情模态框
function openViewDetailModal(feedbackId) {
    const item = feedbackListCache.find(f => String(f.feedback_id) === String(feedbackId));
    if (!item) return;

    // Left Column
    document.getElementById('detail-feedback-id').textContent = item.feedback_id;
    document.getElementById('detail-user-id').textContent = item.user_name || item.user_id;
    document.getElementById('detail-title').textContent = item.title;
    document.getElementById('detail-content').textContent = item.content;

    // Image
    const imgBox = document.getElementById('detail-image-container');
    if (item.attachment_url) {
        const filename = item.attachment_url.split('/').pop();
        const imageUrl = `/api/feedback/image/${filename}`;
        imgBox.innerHTML = `<img src="${imageUrl}" alt="反馈图片" class="detail-image" onclick="window.open(this.src)">`;
    } else {
        imgBox.innerHTML = '<div class="no-image">无相关图片</div>';
    }

    // Right Column
    document.getElementById('detail-status').textContent = item.status;
    
    // Status color
    const statusDiv = document.getElementById('detail-status');
    if (item.status === '已处理') {
        statusDiv.style.color = '#2ecc71';
    } else {
        statusDiv.style.color = '#f1c40f';
    }

    const replyBox = document.getElementById('detail-reply');
    if (item.admin_reply) {
        replyBox.textContent = item.admin_reply;
    } else {
        replyBox.innerHTML = '<div class="no-reply">暂无回复</div>';
    }

    document.getElementById('detail-reply-time').textContent = item.replied_at || '-';
    document.getElementById('detail-reply-by').textContent = item.replied_by || '-';

    document.getElementById('viewDetailModal').classList.remove('hidden');
}

function closeViewDetailModal() {
    document.getElementById('viewDetailModal').classList.add('hidden');
}

// 回复模态框
let currentReplyId = null;

function openReplyModal(feedbackId) {
    currentReplyId = feedbackId;
    
    const item = feedbackListCache.find(f => String(f.feedback_id) === String(feedbackId));
    if (!item) return;

    // Populate Left Side (Feedback Details)
    document.getElementById('reply-detail-feedback-id').textContent = item.feedback_id;
    document.getElementById('reply-detail-user').textContent = item.user_name || item.user_id;
    document.getElementById('reply-detail-title').textContent = item.title;
    document.getElementById('reply-detail-content').textContent = item.content;

    // Image
    const imgBox = document.getElementById('reply-detail-image-box');
    if (item.attachment_url) {
        const filename = item.attachment_url.split('/').pop();
        const imageUrl = `/api/feedback/image/${filename}`;
        imgBox.innerHTML = `<img src="${imageUrl}" alt="反馈图片" class="detail-image" onclick="window.open(this.src)">`;
    } else {
        imgBox.innerHTML = '<div class="no-image">无相关图片</div>';
    }

    // Clear Textarea and Char Count
    document.getElementById('reply-textarea').value = '';
    document.getElementById('replyCharCount').textContent = '0/150';
    
    document.getElementById('replyModal').classList.remove('hidden');
}

function updateReplyCharCount(textarea) {
    const maxLength = 150;
    const currentLength = textarea.value.length;
    document.getElementById('replyCharCount').textContent = `${currentLength}/${maxLength}`;
}

function closeReplyModal() {
    document.getElementById('replyModal').classList.add('hidden');
    currentReplyId = null;
}

async function submitReply() {
    if (!currentReplyId) return;

    const content = document.getElementById('reply-textarea').value.trim();
    if (!content) {
        alert('请输入回复内容');
        return;
    }

    try {
        const token = sessionStorage.getItem('token');
        const response = await fetch('/api/admin/feedback/reply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                feedback_id: currentReplyId,
                reply_content: content
            })
        });

        const res = await response.json();
        if (res.code === 200) {
            alert('回复成功');
            closeReplyModal();
            filterFeedback(); // 刷新列表
        } else {
            alert(res.msg || '回复失败');
        }
    } catch (error) {
        console.error('Error replying feedback:', error);
        alert('网络错误，请稍后重试');
    }
}