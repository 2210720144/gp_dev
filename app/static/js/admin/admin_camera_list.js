document.addEventListener('DOMContentLoaded', function() {
    // 加载摄像头列表
    fetchCameraList();

    // 模态框点击外部关闭
    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('show');
        }
        // Close multi-select dropdown if clicked outside
        if (!event.target.closest('.custom-multi-select')) {
            const dropdown = document.getElementById('config-user-multi-select');
            if (dropdown && dropdown.classList.contains('open')) {
                dropdown.classList.remove('open');
            }
        }
        
        // Handle native select wrapper active state removal on outside click
        // Note: The click on the select itself is handled by its own listener below
        if (!event.target.closest('.select-wrapper')) {
            document.querySelectorAll('.select-wrapper.active').forEach(el => {
                el.classList.remove('active');
            });
        }
    };
    
    // Setup native select arrow animation
    function setupNativeSelect(id) {
        const select = document.getElementById(id);
        if(!select) return;
        const wrapper = select.parentElement;
        if(!wrapper.classList.contains('select-wrapper')) return;

        // Toggle on click
        select.addEventListener('click', function(e) {
            // If the select is already open (OS menu), this click might be closing it or selecting
            // But usually 'change' or 'blur' handles closing logic.
            // We just want to ensure 'active' class reflects user intent.
            // Simple toggle is risky if OS menu behavior differs.
            // Better: If not active, make active. If active, do nothing (let blur/change handle close)
            // Actually, if user clicks to close without selecting, we need toggle.
            wrapper.classList.toggle('active');
        });

        select.addEventListener('blur', function() {
            wrapper.classList.remove('active');
        });

        select.addEventListener('change', function() {
            wrapper.classList.remove('active');
            select.blur(); // Optional: remove focus to reset state fully
        });
    }

    setupNativeSelect('add-video-select');
    setupNativeSelect('config-video-select');
    
    // 添加摄像头表单提交
    document.getElementById('addForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const name = document.getElementById('add-name').value;
        const videoId = document.getElementById('add-video-select').value;
        
        if(!name) {
            alert('请填写摄像头名称');
            return;
        }

        const token = sessionStorage.getItem('token');
        fetch('/api/camera/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                camera_name: name,
                video_id: videoId || null
            })
        })
        .then(res => res.json())
        .then(data => {
            if(data.code === 200) {
                alert('添加成功');
                closeAddModal();
                fetchCameraList();
            } else {
                alert('添加失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    });

    document.getElementById('configForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const cameraId = document.getElementById('config-camera-id-hidden').value;
        const cameraName = document.getElementById('config-camera-name').value;
        const videoId = document.getElementById('config-video-select').value;
        
        // Get selected users
        const selectedUsers = [];
        document.querySelectorAll('input[name="authorized_users"]:checked').forEach(cb => {
            selectedUsers.push(cb.value);
        });

        if(!cameraName) {
            alert('请填写摄像头名称');
            return;
        }

        const token = sessionStorage.getItem('token');
        fetch('/api/camera/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                camera_id: cameraId,
                camera_name: cameraName,
                video_id: videoId || null,
                authorized_user_ids: selectedUsers
            })
        })
        .then(res => res.json())
        .then(data => {
            if(data.code === 200) {
                alert('配置保存成功');
                closeConfigModal();
                fetchCameraList();
            } else {
                alert('保存失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    });
});

function fetchCameraList() {
    const token = sessionStorage.getItem('token');
    fetch('/api/camera/list', {
        headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(res => res.json())
    .then(data => {
        if(data.code === 200) {
            renderTable(data.data);
        } else {
            document.getElementById('camera-table-body').innerHTML = `<tr><td colspan="4" class="error-text">加载失败: ${data.msg}</td></tr>`;
        }
    })
    .catch(err => {
        console.error(err);
        document.getElementById('camera-table-body').innerHTML = `<tr><td colspan="4" class="error-text">系统错误</td></tr>`;
    });
}

function renderTable(data) {
    const tbody = document.getElementById('camera-table-body');
    tbody.innerHTML = '';
    
    if(!data || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-text">暂无摄像头数据</td></tr>`;
        return;
    }

    data.forEach(item => {
        const videoSourceDisplay = item.video_id 
            ? `<span class="tag-bound">${item.video_id}</span>` 
            : `<span class="tag-unbound">未配置</span>`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.camera_id}</td>
            <td>${item.camera_name}</td>
            <td>${videoSourceDisplay}</td>
            <td>
                <button class="action-btn btn-view" onclick="viewDetail('${item.camera_id}')">查看详情</button>
                <button class="action-btn btn-config" onclick="openConfigModal('${item.camera_id}', '${item.camera_name}')">配置</button>
                <button class="action-btn btn-delete" onclick="deleteCamera('${item.camera_id}')">删除</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 模态框操作
window.toggleUserDropdown = function() {
    const dropdown = document.getElementById('config-user-multi-select');
    dropdown.classList.toggle('open');
};

function updateSelectedUsersDisplay() {
    const container = document.getElementById('selected-users-display');
    const checkboxes = document.querySelectorAll('input[name="authorized_users"]:checked');
    
    container.innerHTML = '';
    
    if (checkboxes.length === 0) {
        container.innerHTML = '<span class="select-placeholder">请选择授权用户...</span>';
        return;
    }
    
    checkboxes.forEach(cb => {
        const tag = document.createElement('div');
        tag.className = 'selected-tag';
        tag.innerHTML = `
            ${cb.dataset.username}
            <span class="tag-remove" onclick="removeUserTag('${cb.value}', event)">&times;</span>
        `;
        container.appendChild(tag);
    });
}

window.removeUserTag = function(userId, event) {
    event.stopPropagation(); // Prevent dropdown toggle
    const checkbox = document.querySelector(`input[name="authorized_users"][value="${userId}"]`);
    if (checkbox) {
        checkbox.checked = false;
        updateSelectedUsersDisplay();
    }
};

window.openAddModal = function() {
    document.getElementById('addForm').reset();
    
    // 加载可用视频源
    const select = document.getElementById('add-video-select');
    select.innerHTML = '<option value="">正在加载...</option>';
    
    const token = sessionStorage.getItem('token');
    fetch('/api/camera/video-sources/available', {
        headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(res => res.json())
    .then(data => {
        select.innerHTML = '<option value="">-- 请选择视频源 --</option>';
        if(data.code === 200) {
            data.data.forEach(v => {
                const option = document.createElement('option');
                option.value = v.video_id;
                option.textContent = `ID:${v.video_id} - ${v.video_name || '未命名'}`;
                select.appendChild(option);
            });
        }
    })
    .catch(err => {
        console.error(err);
        select.innerHTML = '<option value="">加载失败</option>';
    });

    document.getElementById('addModal').classList.add('show');
};

window.closeAddModal = function() {
    document.getElementById('addModal').classList.remove('show');
};

window.openConfigModal = function(id, name) {
    const token = sessionStorage.getItem('token');
    
    document.getElementById('config-camera-id').value = id;
    document.getElementById('config-camera-id-hidden').value = id;
    document.getElementById('config-camera-name').value = name;
    
    // 1. Fetch Available Video Sources + Current Camera Detail (to get current video) + Ordinary Users
    // We can do this in parallel or chained.
    
    // Reset inputs
    const videoSelect = document.getElementById('config-video-select');
    const userOptionsDiv = document.getElementById('config-user-options');
    const selectedDisplay = document.getElementById('selected-users-display');
    
    videoSelect.innerHTML = '<option value="">正在加载...</option>';
    userOptionsDiv.innerHTML = '<div class="option-item" style="color: #777;">正在加载数据...</div>';
    selectedDisplay.innerHTML = '<span class="select-placeholder">加载中...</span>';
    
    document.getElementById('configModal').classList.add('show');

    Promise.all([
        // Get Camera Detail (for current video & permissions)
        fetch(`/api/camera/${id}`, { headers: { 'Authorization': 'Bearer ' + token } }).then(res => res.json()),
        // Get Available Videos
        fetch('/api/camera/video-sources/available', { headers: { 'Authorization': 'Bearer ' + token } }).then(res => res.json()),
        // Get Ordinary Users
        fetch('/api/camera/users/ordinary', { headers: { 'Authorization': 'Bearer ' + token } }).then(res => res.json())
    ])
    .then(([cameraRes, videosRes, usersRes]) => {
        if(cameraRes.code !== 200) throw new Error(cameraRes.msg);
        
        const camera = cameraRes.data;
        const availableVideos = videosRes.data || [];
        const users = usersRes.data || [];
        
        // --- Populate Video Select ---
        videoSelect.innerHTML = '<option value="">-- 未绑定视频源 --</option>';
        
        // Add current video logic (same as before)
        if (camera.video_id) {
             const info = camera.video_source_info;
             if(info !== '未配置') {
                 const currentVideoOption = document.createElement('option');
                 currentVideoOption.value = camera.video_id;
                 currentVideoOption.textContent = info + " (当前)";
                 currentVideoOption.selected = true;
                 videoSelect.appendChild(currentVideoOption);
             }
        }
        
        availableVideos.forEach(v => {
            const option = document.createElement('option');
            option.value = v.video_id;
            option.textContent = `ID:${v.video_id} - ${v.video_name || '未命名'}`;
            videoSelect.appendChild(option);
        });
        
        // --- Populate User Dropdown ---
        userOptionsDiv.innerHTML = '';
        const authorizedIds = camera.authorized_user_ids || [];
        
        if(users.length === 0) {
            userOptionsDiv.innerHTML = '<div class="option-item" style="color: #777;">暂无普通用户</div>';
        } else {
            users.forEach(u => {
                const label = document.createElement('label');
                label.className = 'option-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'authorized_users';
                checkbox.value = u.user_id;
                checkbox.dataset.username = u.username; // Store name for display
                
                if(authorizedIds.includes(u.user_id)) {
                    checkbox.checked = true;
                }
                
                // Add event listener to update display on change
                checkbox.addEventListener('change', updateSelectedUsersDisplay);
                
                const span = document.createElement('span');
                span.textContent = `${u.username} (ID:${u.user_id})`;
                
                label.appendChild(checkbox);
                label.appendChild(span);
                userOptionsDiv.appendChild(label);
            });
        }
        
        // Initial update of the display
        updateSelectedUsersDisplay();
    })
    .catch(err => {
        console.error(err);
        alert('数据加载失败: ' + err.message);
        closeConfigModal();
    });
};

window.closeConfigModal = function() {
    document.getElementById('configModal').classList.remove('show');
};

window.viewDetail = function(id) {
    const token = sessionStorage.getItem('token');
    
    // 显示加载状态或清空旧数据
    document.getElementById('detail-camera-id').value = '加载中...';
    document.getElementById('detail-camera-name').value = '加载中...';
    document.getElementById('detail-video-source').value = '加载中...';
    document.getElementById('detail-authorized-users').value = '加载中...';
    document.getElementById('detail-created-by').value = '加载中...';
    document.getElementById('detail-created-at').value = '加载中...';
    
    document.getElementById('detailModal').classList.add('show');

    fetch(`/api/camera/${id}`, {
        headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(res => res.json())
    .then(data => {
        if(data.code === 200) {
            const info = data.data;
            document.getElementById('detail-camera-id').value = info.camera_id;
            document.getElementById('detail-camera-name').value = info.camera_name;
            document.getElementById('detail-video-source').value = info.video_source_info;
            document.getElementById('detail-authorized-users').value = info.authorized_users_info;
            document.getElementById('detail-created-by').value = info.created_by;
            document.getElementById('detail-created-at').value = info.created_at;
        } else {
            alert('获取详情失败: ' + data.msg);
            closeDetailModal();
        }
    })
    .catch(err => {
        console.error(err);
        alert('系统错误');
        closeDetailModal();
    });
};

window.closeDetailModal = function() {
    document.getElementById('detailModal').classList.remove('show');
};

window.deleteCamera = function(id) {
    if(confirm('确定要删除该摄像头吗？')) {
        const token = sessionStorage.getItem('token');
        fetch(`/api/camera/delete/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(res => res.json())
        .then(data => {
            if(data.code === 200) {
                alert('删除成功');
                fetchCameraList();
            } else {
                alert('删除失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    }
};