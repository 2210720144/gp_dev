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
            fetchAlertList(); // 重新加载数据
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
    tbody.innerHTML = '<tr><td colspan="5" class="loading-text">正在加载数据...</td></tr>';

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

        const response = await fetch(`/api/alert/list?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const res = await response.json();
            if (res.code === 200) {
                // 更新筛选器选项 (仅当不是显示所有模式时，或者是初次加载时)
                // 注意：如果正在筛选特定的摄像头，后端返回的 available_years 已经过滤过了
                if (!showAll) {
                    updateFilters(res.data);
                }
                
                // 渲染表格
                renderTable(res.data.list);
            } else {
                tbody.innerHTML = `<tr><td colspan="5" class="loading-text">${res.msg || '加载失败'}</td></tr>`;
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="loading-text">系统错误 (Status: ${response.status})</td></tr>`;
        }
    } catch (error) {
        console.error('Error fetching alert list:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="loading-text">网络错误，请稍后重试</td></tr>';
    }
}

function updateFilters(data) {
    // 1. 更新摄像头下拉框 (如果当前选的是all，才更新列表，防止正在选的时候跳变? 或者总是更新但保持选中?)
    // 通常摄像头列表是固定的授权列表，变化不大，但在初始化时需要填充
    const cameraSelect = document.getElementById('camera-filter');
    const currentCameraId = cameraSelect.value;
    
    // 如果下拉框只有默认选项(长度<=1)，或者需要刷新
    // 这里简单处理：保留当前选中值，重新填充
    if (cameraSelect.options.length <= 1 || data.authorized_cameras.length > 0) {
        // 保存当前选中的值
        const selectedValue = cameraSelect.value;
        
        // 清空除了"全部"之外的选项
        cameraSelect.innerHTML = '<option value="all">全部监控</option>';
        
        data.authorized_cameras.forEach(cam => {
            const option = document.createElement('option');
            option.value = cam.id;
            option.textContent = cam.name;
            cameraSelect.appendChild(option);
        });
        
        // 恢复选中
        cameraSelect.value = selectedValue;
    }

    // 2. 更新年份下拉框
    const yearSelect = document.getElementById('year-filter');
    const currentYear = yearSelect.value;
    
    yearSelect.innerHTML = '';
    
    if (data.available_years.length === 0) {
        // 如果没有数据，显示当前年份
        const thisYear = new Date().getFullYear();
        const option = document.createElement('option');
        option.value = thisYear;
        option.textContent = `${thisYear}年`;
        yearSelect.appendChild(option);
    } else {
        data.available_years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `${year}年`;
            yearSelect.appendChild(option);
        });
    }
    
    // 尝试恢复选中年份，如果不存在则选中第一个
    // 注意：如果用户切换了摄像头，导致当前年份不可用，则会自动选中第一个可用年份
    // 这一步由浏览器自动处理（如果value不匹配，select会显示第一个? 不一定）
    // 我们手动检查
    let yearExists = false;
    for (let i = 0; i < yearSelect.options.length; i++) {
        if (yearSelect.options[i].value === currentYear) {
            yearSelect.value = currentYear;
            yearExists = true;
            break;
        }
    }
    if (!yearExists && yearSelect.options.length > 0) {
        // 如果之前选的年份不在新列表中，默认选第一个（最近的年份）
        yearSelect.value = yearSelect.options[0].value;
    }
}

function renderTable(list) {
    const tbody = document.getElementById('alert-table-body');
    tbody.innerHTML = '';

    if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading-text">无法查询到违停事件</td></tr>';
        return;
    }

    list.forEach(item => {
        const tr = document.createElement('tr');
        
        let statusClass = item.status === '已处理' ? 'status-processed' : 'status-pending';
        
        tr.innerHTML = `
            <td>${item.event_id}</td>
            <td>${item.camera_name}</td>
            <td>${item.start_time}</td>
            <td>${item.end_time}</td>
            <td><span class="status-badge ${statusClass}">${item.status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

async function exportData(type) {
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
    
    const url = `/api/alert/export/${type}?${params.toString()}`;
    
    try {
        // 创建临时提示
        const originalText = type === 'pdf' ? document.getElementById('export-pdf').innerText : document.getElementById('export-excel').innerText;
        if (type === 'pdf') document.getElementById('export-pdf').innerText = '导出中...';
        else document.getElementById('export-excel').innerText = '导出中...';

        const response = await fetch(url, {
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
                
                // 获取文件名
                let filename = `alert_records.${type === 'excel' ? 'xlsx' : 'pdf'}`;
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
            // 尝试读取错误信息
            try {
                const errorData = await response.json();
                alert(`导出请求失败: ${errorData.msg || '未知错误'} (状态码: ${response.status})`);
            } catch (e) {
                alert(`导出请求失败 (状态码: ${response.status})`);
            }
        }
    } catch (error) {
        console.error('Export error:', error);
        alert('导出出错，请稍后重试');
    } finally {
        // 恢复按钮文字
        if (type === 'pdf') document.getElementById('export-pdf').innerText = '导出PDF';
        else document.getElementById('export-excel').innerText = '导出EXCEL';
    }
}