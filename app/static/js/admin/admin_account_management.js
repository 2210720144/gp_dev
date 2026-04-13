document.addEventListener('DOMContentLoaded', function() {
    loadUserList();
});

let allUsers = []; // Store all users locally for filtering

function loadUserList() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/auth';
        return;
    }

    fetch('/admin/user-list', {
        headers: {
            'Authorization': 'Bearer ' + token
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.code === 200) {
            allUsers = result.data; // Save data
            filterUsers('all'); // Default show all
        } else {
            alert('加载失败: ' + result.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('user-table-body').innerHTML = '<tr><td colspan="7" class="loading-text">加载出错，请检查网络</td></tr>';
    });
}

function filterUsers(type) {
    // Update active button state
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => {
        if (btn.textContent.toLowerCase() === type || (type === 'all' && btn.textContent === '全部')) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    let filtered = [];
    if (type === 'all') {
        filtered = allUsers;
    } else if (type === 'user') {
        filtered = allUsers.filter(u => u.role === '普通用户');
    } else if (type === 'admin') {
        filtered = allUsers.filter(u => u.role === '管理员用户' || u.role === '超级管理员');
    }

    renderTable(filtered);
}

function renderTable(users) {
    const tbody = document.getElementById('user-table-body');
    tbody.innerHTML = '';

    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-text">暂无用户数据</td></tr>';
        return;
    }

    // 获取当前登录用户信息
    let currentUserId = null;
    let currentUserRole = null;
    try {
        const userInfo = JSON.parse(localStorage.getItem('user_info'));
        currentUserId = userInfo ? userInfo.user_id : null;
        currentUserRole = userInfo ? userInfo.role : null;
    } catch(e) {}

    users.forEach(user => {
        const tr = document.createElement('tr');

        // 状态标签样式
        let statusClass = '';
        switch(user.status) {
            case '正常': statusClass = 'status-active'; break;
            case '待审核': statusClass = 'status-pending'; break;
            case '禁用': statusClass = 'status-disabled'; break;
            case '已注销': statusClass = 'status-deleted'; break;
            default: statusClass = '';
        }

        // 权限判断: Root可以管理所有人(除自己)，Admin只能管理普通用户
        let canManage = false;
        if (user.user_id !== currentUserId) {
            if (currentUserRole === '超级管理员') {
                canManage = true;
            } else if (currentUserRole === '管理员用户') {
                if (user.role === '普通用户') {
                    canManage = true;
                }
            }
        }

        // 操作按钮逻辑
        let actions = '';

        // 如果是待审核状态，显示通过/驳回
        if (user.status === '待审核') {
            actions += `
                <button class="action-btn btn-approve" onclick="auditUser(${user.user_id}, 'approve')">通过</button>
                <button class="action-btn btn-reject" onclick="auditUser(${user.user_id}, 'reject')">驳回</button>
            `;
        }
        // 如果是正常状态，显示禁用
        else if (user.status === '正常') {
            if (canManage) {
                actions += `<button class="action-btn btn-disable" onclick="manageUser(${user.user_id}, 'disable')">禁用</button>`;
            }
        }
        // 如果是禁用状态，显示启用
        else if (user.status === '禁用') {
            if (canManage) {
                actions += `<button class="action-btn btn-enable" onclick="manageUser(${user.user_id}, 'enable')">启用</button>`;
            }
        }
        
        // 注销按钮 (仅当有管理权限时显示)
        if (canManage) {
            actions += `<button class="action-btn btn-delete" onclick="deleteUser(${user.user_id})">注销</button>`;
        }

        tr.innerHTML = `
            <td>${user.user_id}</td>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td>${user.role}</td>
            <td><span class="status-badge ${statusClass}">${user.status}</span></td>
            <td>${new Date(user.created_at).toLocaleString()}</td>
            <td>${actions}</td>
        `;
        tbody.appendChild(tr);
    });
}

// 审核用户
window.auditUser = function(userId, action) {
    if (!confirm(action === 'approve' ? '确认通过该用户审核？' : '确认驳回该用户申请？')) return;

    callApi('/admin/audit', { user_id: userId, action: action });
};

// 管理用户状态
window.manageUser = function(userId, action) {
    let confirmMsg = action === 'disable' ? '确认禁用该用户？' : '确认启用该用户？';
    if (!confirm(confirmMsg)) return;

    callApi('/admin/manage-user', { user_id: userId, action: action });
};

// 注销用户
window.deleteUser = function(userId) {
    if (!confirm('确认要注销该用户吗？注销后将删除该用户及其所有相关权限，此操作不可恢复。')) return;

    const token = localStorage.getItem('token');
    fetch(`/admin/user/delete/${userId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': 'Bearer ' + token
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.code === 200) {
            alert(result.msg);
            loadUserList(); // 刷新列表
        } else {
            alert(result.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('操作失败');
    });
};

// 通用API调用
function callApi(url, data) {
    const token = localStorage.getItem('token');
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.code === 200) {
            alert(result.msg);
            loadUserList(); // 刷新列表
        } else {
            alert(result.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('操作失败');
    });
}