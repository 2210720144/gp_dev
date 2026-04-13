document.addEventListener('DOMContentLoaded', function() {
    filterFeedback();
});

// 获取反馈列表并渲染
async function fetchFeedbackList(year, month, showAll) {
    const tbody = document.getElementById('feedback-table-body');
    tbody.innerHTML = '<tr><td colspan="4" class="loading-text">正在加载数据...</td></tr>';

    try {
        const token = localStorage.getItem('token');
        const params = new URLSearchParams();
        if (showAll) {
            params.append('show_all', 'true');
        } else {
            if (year) params.append('year', year);
            if (month) params.append('month', month);
        }

        const response = await fetch(`/api/feedback/list?${params.toString()}`, {
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
                tbody.innerHTML = `<tr><td colspan="4" class="loading-text">${res.msg || '加载失败'}</td></tr>`;
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="4" class="loading-text">系统错误 (Status: ${response.status})</td></tr>`;
        }
    } catch (error) {
        console.error('Error fetching feedback list:', error);
        tbody.innerHTML = '<tr><td colspan="4" class="loading-text">网络错误，请稍后重试</td></tr>';
    }
}

function updateYearFilter(years, currentYear) {
    const yearSelect = document.getElementById('year-filter');
    const currentVal = yearSelect.value;
    
    // 清空现有选项
    yearSelect.innerHTML = '';
    
    if (!years || years.length === 0) {
        // 如果没有年份数据，显示当前年份或者默认值
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

    // 如果之前选中的值不在新列表中（且不是由后端指定的currentYear），可能需要重置？
    // 这里主要依赖后端返回的 current_filters.year 来设置选中状态
}

let feedbackListCache = []; // 全局缓存

function renderTable(data) {
    feedbackListCache = data || []; // 更新缓存
    const tbody = document.getElementById('feedback-table-body');
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-text">无法查询到反馈记录</td></tr>';
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
                <button class="action-btn btn-view" onclick="openViewDetailModal('${item.feedback_id}')">查看详情</button>
                <button class="action-btn btn-cancel" onclick="cancelFeedback('${item.feedback_id}')">撤销</button>
            `;
        } else {
            actionButtons = `
                <button class="action-btn btn-view" onclick="openViewDetailModal('${item.feedback_id}')">查看详情</button>
            `;
        }

        tr.innerHTML = `
            <td>${item.feedback_id}</td>
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

function openAddFeedbackModal() {
    document.getElementById('addFeedbackModal').classList.remove('hidden');
}

function closeAddFeedbackModal() {
    document.getElementById('addFeedbackModal').classList.add('hidden');
    // 清空表单
    document.getElementById('addFeedbackForm').reset();
    document.getElementById('charCount').textContent = '0/100';
    removeFile();
}

function updateCharCount(textarea) {
    const count = textarea.value.length;
    document.getElementById('charCount').textContent = `${count}/100`;
}

// 文件上传处理
const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('feedbackImage');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');

if (dropArea) {
    dropArea.addEventListener('click', () => fileInput.click());

    dropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.classList.add('drag-over');
    });

    dropArea.addEventListener('dragleave', () => {
        dropArea.classList.remove('drag-over');
    });

    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
}

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('请上传图片文件！');
        return;
    }
    
    fileName.textContent = file.name;
    dropArea.style.display = 'none';
    fileInfo.classList.remove('hidden');
}

function removeFile() {
    fileInput.value = '';
    dropArea.style.display = 'block';
    fileInfo.classList.add('hidden');
}

async function submitFeedback() {
    const title = document.getElementById('feedbackTitle').value;
    const content = document.getElementById('feedbackContent').value;
    
    if (!title || !content) {
        alert('请填写必填项！');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    if (fileInput.files[0]) {
        formData.append('image', fileInput.files[0]);
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/feedback/add', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const res = await response.json();

        if (response.ok && res.code === 200) {
            alert('反馈提交成功！');
            closeAddFeedbackModal();
            
            // 提交成功后重新加载列表
            filterFeedback();
        } else {
            alert(res.msg || '提交失败');
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        alert('系统错误，请稍后重试');
    }
}

function openViewDetailModal(feedbackId) {
    console.log('Opening detail modal for ID:', feedbackId);
    
    // 从缓存中查找数据
    // 确保 ID 类型一致（都转为字符串进行比较）
    const feedback = feedbackListCache.find(f => String(f.feedback_id) === String(feedbackId));
    
    if (!feedback) {
        console.error('Feedback not found in cache:', feedbackId, 'Cache:', feedbackListCache);
        alert('未找到该反馈详情，请刷新重试');
        return;
    }

    document.getElementById('viewDetailModal').classList.remove('hidden');
    
    // 填充数据
    document.getElementById('detail-feedback-id').textContent = feedback.feedback_id;
    document.getElementById('detail-user-id').textContent = feedback.user_id;
    document.getElementById('detail-title').textContent = feedback.title;
    document.getElementById('detail-content').textContent = feedback.content;
    document.getElementById('detail-status').textContent = feedback.status;

    // 处理图片
    const imgContainer = document.getElementById('detail-image-container');
    imgContainer.innerHTML = '';
    if (feedback.attachment_url) {
        const filename = feedback.attachment_url.split('/').pop();
        const imgSrc = `/api/feedback/image/${filename}`;
        
        const img = document.createElement('img');
        img.src = imgSrc;
        img.className = 'detail-image';
        img.alt = '反馈截图';
        img.onclick = function() { window.open(imgSrc, '_blank'); };
        img.onerror = function() {
            this.style.display = 'none';
            imgContainer.innerHTML += '<span class="no-image">图片加载失败</span>';
        };
        imgContainer.appendChild(img);
    } else {
        imgContainer.innerHTML = '<span class="no-image">无图片</span>';
    }

    // 处理回复
    const replyBox = document.getElementById('detail-reply');
    const replyTime = document.getElementById('detail-reply-time');
    const replyBy = document.getElementById('detail-reply-by');

    if (feedback.status === '待处理') {
        replyBox.textContent = '还未回复，请等待！';
        replyBox.classList.add('no-reply');
        replyTime.textContent = '-';
        replyBy.textContent = '-';
    } else {
        replyBox.textContent = feedback.admin_reply || '（无文字回复）';
        replyBox.classList.remove('no-reply');
        replyTime.textContent = feedback.replied_at || '-';
        replyBy.textContent = feedback.replied_by || '-';
    }
}

function closeViewDetailModal() {
    document.getElementById('viewDetailModal').classList.add('hidden');
}

async function cancelFeedback(id) {
    if (!confirm('确定要撤销这条反馈吗？此操作不可恢复。')) {
        return;
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/api/feedback/delete/${id}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const res = await response.json();

        if (response.ok && res.code === 200) {
            alert('撤销成功');
            // 刷新列表
            filterFeedback();
        } else {
            alert(res.msg || '撤销失败');
        }
    } catch (error) {
        console.error('Error canceling feedback:', error);
        alert('系统错误，请稍后重试');
    }
}