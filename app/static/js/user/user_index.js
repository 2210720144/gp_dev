document.addEventListener('DOMContentLoaded', function() {
    let pollIntervals = [];

    // 1. 鉴权逻辑：检查 Token 是否存在
    const token = localStorage.getItem('token');
    if (!token) {
        alert('您尚未登录，请先登录');
        window.location.href = '/auth'; // 跳转到登录页
        return;
    }

    // 2. 验证 Token 有效性（调用后端接口）
    fetch('/me', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 401 || response.status === 422) {
            // Token 无效或过期
            throw new Error('Unauthorized');
        }
        return response.json();
    })
    .then(data => {
        if (data.code === 200) {
            // Token 有效，更新本地存储的用户信息（保持同步）
            localStorage.setItem('user_info', JSON.stringify(data.data));
            
            // 更新页面显示
            updateUserInfo(data.data);
            
            // 加载我的摄像头
            loadMyCameras(token);
            
            // 加载违停告警
            loadAlerts(token);
            loadAlertCount(token);
            setInterval(() => {
                loadAlerts(token);
                loadAlertCount(token);
            }, 5000); // 每5秒刷新一次告警
        } else {
            throw new Error(data.msg || 'Verification failed');
        }
    })
    .catch(error => {
        console.error('Auth verification failed:', error);
        alert('登录状态已失效，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user_info');
        window.location.href = '/auth';
    });

    // 辅助函数：更新页面用户信息
    function updateUserInfo(user) {
        try {
            // 尝试获取带有ID的元素，如果不存在则尝试通过类名获取（兼容性）
            const usernameSpan = document.getElementById('header-username') || document.querySelector('.user-info span');
            if (usernameSpan && user.username) {
                usernameSpan.textContent = user.username;
            }
        } catch (e) {
            console.error('Error updating user info:', e);
        }
    }
    
    function loadMyCameras(token) {
        // Clear existing polling intervals
        pollIntervals.forEach(clearInterval);
        pollIntervals = [];

        fetch('/api/camera/my-list', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(res => res.json())
        .then(data => {
            const grid = document.getElementById('camera-grid');
            grid.innerHTML = '';
            
            if(data.code === 200 && data.data.length > 0) {
                data.data.forEach(cam => {
                    renderCameraCard(grid, cam);
                });
            } else {
                grid.innerHTML = '<div class="empty-text" style="color: #ccc; text-align: center; width: 100%; padding: 50px;">暂无授权的摄像头或未配置视频源</div>';
            }
        })
        .catch(err => {
            console.error(err);
            document.getElementById('camera-grid').innerHTML = '<div class="error-text">加载失败</div>';
        });
    }

    function renderCameraCard(container, cam) {
        const card = document.createElement('div');
        card.className = 'camera-card';
        
        // 视频源处理 (如果video_url为空，显示占位符)
        let videoContent = '';
        if(cam.video_url) {
            // 使用后端流媒体接口 (带 YOLO 检测)
            videoContent = `
                <div class="video-container" style="background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                    <img src="/api/camera/stream/${cam.camera_id}" 
                         style="width: 100%; height: 100%; object-fit: contain;"
                         alt="正在连接摄像头..."
                         onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=\'color:#fff\'>视频流连接失败</div>'">
                </div>
            `;
        } else {
            videoContent = `
                <div class="placeholder">
                    <div>
                        <i class="fas fa-video-slash"></i>
                        <p>未配置视频源</p>
                    </div>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="card-header">
                <span class="card-title">${cam.location || cam.camera_name}</span>
                <span class="status normal" id="status-badge-${cam.camera_id}">正常</span>
            </div>
            <div class="video-container">
                ${videoContent}
            </div>
            <div class="card-footer" id="footer-text-${cam.camera_id}">
                当前检测到：0辆单车 | 违停：0辆
            </div>
        `;
        
        container.appendChild(card);

        if (cam.video_url) {
            const intervalId = setInterval(() => {
                fetch(`/api/camera/status/${cam.camera_id}`, {
                    headers: { 'Authorization': 'Bearer ' + token }
                })
                .then(res => res.json())
                .then(res => {
                    if (res.code === 200) {
                        updateCardStatus(cam.camera_id, res.data);
                    }
                })
                .catch(err => console.error('Status poll failed:', err));
            }, 2000);
            pollIntervals.push(intervalId);
        }
    }

    function updateCardStatus(cameraId, status) {
        const footer = document.getElementById(`footer-text-${cameraId}`);
        const badge = document.getElementById(`status-badge-${cameraId}`);
        
        if (footer) {
            footer.innerHTML = `当前检测到：${status.bicycle_count}辆单车 | 违停：<span style="${status.violation_count > 0 ? 'color: #FF7875; font-weight: bold;' : ''}">${status.violation_count}辆</span>`;
        }
        
        if (badge) {
            if (status.violation_count > 0) {
                badge.textContent = '发生违停';
                badge.className = 'status alert';
            } else {
                badge.textContent = '正常';
                badge.className = 'status normal';
            }
        }
    }

    function loadAlerts(token) {
        fetch('/api/camera/alerts', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(res => res.json())
        .then(res => {
            if (res.code === 200) {
                renderAlerts(res.data);
            }
        })
        .catch(err => console.error('Failed to load alerts:', err));
    }

    function renderAlerts(alerts) {
        const list = document.querySelector('.alert-list');
        if (!list) return;
        
        if (alerts.length === 0) {
            list.innerHTML = '<li style="text-align:center; color:#888; padding:20px;">暂无违停告警</li>';
            return;
        }
        
        list.innerHTML = alerts.map(alert => `
            <li class="alert-item">
                <div class="alert-time">${alert.time}</div>
                <div class="alert-content">${alert.msg}</div>
            </li>
        `).join('');
    }

    function loadAlertCount(token) {
        fetch('/api/user/alert-count', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                const badge = document.getElementById('alert-badge');
                if (badge) {
                    badge.textContent = data.data.count;
                }
            }
        })
        .catch(err => console.error('Failed to load alert count:', err));
    }
});

// 关闭/展开告警侧边栏
document.getElementById('close-alert').addEventListener('click', function() {
    const sidebar = document.querySelector('.alert-sidebar');
    const icon = this.querySelector('i');
    
    // 切换 collapsed 类来标记状态
    if (sidebar.classList.contains('collapsed')) {
        // 展开
        sidebar.classList.remove('collapsed');
        sidebar.style.transform = 'translateX(0)';
        icon.className = 'fas fa-chevron-right';
        this.title = "收起";
    } else {
        // 收起
        sidebar.classList.add('collapsed');
        sidebar.style.transform = 'translateX(100%)';
        icon.className = 'fas fa-chevron-left';
        this.title = "展开";
    }
});

// 模拟播放点击 (Removed as we use native controls now)
// document.querySelectorAll('.video-container').forEach(container => {
//     container.addEventListener('click', function() {
//         alert('正在连接摄像头视频流...');
//         // 这里后续可以接入 HLS/FLV 播放器逻辑
//     });
// });