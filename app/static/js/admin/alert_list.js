document.addEventListener('DOMContentLoaded', function() {
    // 初始化加载数据
    fetchAlertList();

    // 绑定筛选事件
    document.getElementById('camera-filter').addEventListener('change', fetchAlertList);
    document.getElementById('year-filter').addEventListener('change', fetchAlertList);
    document.getElementById('month-filter').addEventListener('change', fetchAlertList);

    // 绑定显示所有事件的复选框逻辑
    const showAllCheckbox = document.getElementById('show-all-check');
    if (showAllCheckbox) {
        showAllCheckbox.addEventListener('change', function() {
            toggleShowAll(this);
            fetchAlertList();
        });
    }

    // 绑定导出按钮事件
    const exportPdfBtn = document.getElementById('export-pdf');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportData('pdf');
        });
    }

    const exportExcelBtn = document.getElementById('export-excel');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportData('excel');
        });
    }
});

function toggleShowAll(checkbox) {
    const cameraSelect = document.getElementById('camera-filter');
    const yearSelect = document.getElementById('year-filter');
    const monthSelect = document.getElementById('month-filter');

    if (checkbox.checked) {
        cameraSelect.disabled = true;
        yearSelect.disabled = true;
        monthSelect.disabled = true;
        cameraSelect.style.opacity = '0.5';
        yearSelect.style.opacity = '0.5';
        monthSelect.style.opacity = '0.5';
    } else {
        cameraSelect.disabled = false;
        yearSelect.disabled = false;
        monthSelect.disabled = false;
        cameraSelect.style.opacity = '1';
        yearSelect.style.opacity = '1';
        monthSelect.style.opacity = '1';
    }
}

async function fetchAlertList() {
    const tbody = document.getElementById('alert-table-body');
    tbody.innerHTML = '<tr><td colspan="6" class="loading-text">正在加载数据...</td></tr>';

    try {
        const token = sessionStorage.getItem('token');
        const showAll = document.getElementById('show-all-check').checked;
        const cameraId = document.getElementById('camera-filter').value;
        const year = document.getElementById('year-filter').value;
        const month = document.getElementById('month-filter').value;

        const params = new URLSearchParams();
        if (showAll) {
            params.append('show_all', 'true');
        } else {
            if (cameraId && cameraId !== 'all') params.append('camera_id', cameraId);
            if (year) params.append('year', year);
            if (month && month !== 'all') params.append('month', month);
        }

        const response = await fetch(`/api/alert/admin/list?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const res = await response.json();
            if (res.code === 200) {
                // 更新筛选器选项
                updateFilters(res.data);
                renderTable(res.data.list);
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="error-text">${res.msg || '加载失败'}</td></tr>`;
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="6" class="error-text">请求失败 (${response.status})</td></tr>`;
        }
    } catch (error) {
        console.error('Error fetching alert list:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="error-text">网络错误</td></tr>';
    }
}

function updateFilters(data) {
    const cameraSelect = document.getElementById('camera-filter');
    const yearSelect = document.getElementById('year-filter');

    // 更新摄像头列表（仅当列表为空或仅有默认项时，避免重复渲染）
    if (cameraSelect.options.length <= 1 && data.authorized_cameras) {
        const currentVal = cameraSelect.value;
        cameraSelect.innerHTML = '<option value="all">全部监控</option>';
        data.authorized_cameras.forEach(cam => {
            const option = document.createElement('option');
            option.value = cam.id;
            option.textContent = cam.name;
            cameraSelect.appendChild(option);
        });
        cameraSelect.value = currentVal;
    }

    // 更新年份列表（根据当前摄像头选择动态变化）
    if (data.available_years) {
        const currentYear = yearSelect.value;
        yearSelect.innerHTML = '';

        if (data.available_years.length === 0) {
            const option = document.createElement('option');
            option.value = new Date().getFullYear();
            option.textContent = `${new Date().getFullYear()}年`;
            yearSelect.appendChild(option);
        } else {
            data.available_years.forEach(y => {
                const option = document.createElement('option');
                option.value = y;
                option.textContent = `${y}年`;
                yearSelect.appendChild(option);
            });
        }

        // 尝试保持当前选择，否则默认选择第一项
        let hasCurrent = false;
        for (let i = 0; i < yearSelect.options.length; i++) {
            if (yearSelect.options[i].value === currentYear) {
                yearSelect.value = currentYear;
                hasCurrent = true;
                break;
            }
        }
        if (!hasCurrent && yearSelect.options.length > 0) {
            yearSelect.value = yearSelect.options[0].value;
        }
    }
}

function renderTable(list) {
    const tbody = document.getElementById('alert-table-body');
    if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = list.map(item => `
        <tr>
            <td>${item.event_id}</td>
            <td>${item.camera_id}</td>
            <td>${item.camera_name}</td>
            <td>${item.start_time}</td>
            <td>${item.end_time}</td>
            <td>
                <span class="status-badge ${item.status === '已处理' ? 'status-processed' : 'status-pending'}">
                    ${item.status}
                </span>
            </td>
        </tr>
    `).join('');
}

async function exportData(type) {
    const token = sessionStorage.getItem('token');
    const showAll = document.getElementById('show-all-check').checked;
    const params = new URLSearchParams();

    if (showAll) {
        params.append('show_all', 'true');
    } else {
        const cameraId = document.getElementById('camera-filter').value;
        const year = document.getElementById('year-filter').value;
        const month = document.getElementById('month-filter').value;

        if (cameraId && cameraId !== 'all') params.append('camera_id', cameraId);
        if (year) params.append('year', year);
        if (month && month !== 'all') params.append('month', month);
    }

    try {
        const response = await fetch(`/api/alert/admin/export/${type}?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const res = await response.json();
                alert(res.msg || '导出失败');
            } else {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                let filename = `admin_alert_records.${type === 'excel' ? 'xlsx' : 'pdf'}`;
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (filenameMatch && filenameMatch.length === 2)
                        filename = filenameMatch[1];
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);
            }
        } else {
            try {
                const errorData = await response.json();
                alert(`导出请求失败: ${errorData.msg || '未知错误'} (状态码: ${response.status})`);
            } catch (e) {
                alert(`导出请求失败 (状态码: ${response.status})`);
            }
        }
    } catch (error) {
        console.error('Export error:', error);
        alert('网络错误，导出失败');
    }
}