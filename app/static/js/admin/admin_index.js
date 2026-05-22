// 注册插件
if (typeof Chart !== 'undefined' && typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
} else {
    console.warn('ChartDataLabels plugin not loaded or Chart.js missing.');
}

// 折叠菜单交互
document.addEventListener('DOMContentLoaded', function() {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js library is not loaded. Charts will not be rendered.');
        // Do not return here, as it blocks auth logic
    }

    // 1. 鉴权逻辑：检查 Token 是否存在
    // 1. 鉴权逻辑：检查 Token 是否存在
    const token = sessionStorage.getItem('token');
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
            sessionStorage.setItem('user_info', JSON.stringify(data.data));
            
            // 更新页面显示
            updateUserInfo(data.data);
            
            // 获取统计数据
            fetchStats();
        } else {
            throw new Error(data.msg || 'Verification failed');
        }
    })
    .catch(error => {
        console.error('Auth verification failed:', error);
        alert('登录状态已失效，请重新登录');
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user_info');
        window.location.href = '/auth';
    });

    // 辅助函数：更新页面用户信息
    function updateUserInfo(userInfo) {
        try {
            const nameSpan = document.querySelector('.header .user-info span:first-child');
            const roleSpan = document.querySelector('.header .user-info .role-tag');
            
            if (nameSpan) nameSpan.textContent = userInfo.username;
            if (roleSpan) roleSpan.textContent = userInfo.role;
        } catch (e) {
            console.error('Failed to update user info', e);
        }
    }

    // 辅助函数：获取统计数据
    function fetchStats() {
        console.log('Fetching stats...');
        fetch('/api/admin/stats', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(res => {
            console.log('Stats response:', res);
            if (res.code === 200) {
                const data = res.data;
                
                // 1. 摄像头总数
                const cameraTotal = document.getElementById('camera-total');
                const cameraDetail = document.getElementById('camera-detail');
                if (cameraTotal) cameraTotal.textContent = data.camera.total;
                if (cameraDetail) cameraDetail.textContent = `摄像头总数（在线：${data.camera.online} / 离线：${data.camera.offline}）`;
                
                // 2. 注册用户数
                const userTotal = document.getElementById('user-total');
                const userDetail = document.getElementById('user-detail');
                if (userTotal) userTotal.textContent = data.user.total;
                if (userDetail) userDetail.textContent = `注册用户数（已审核：${data.user.audited} / 待审核：${data.user.pending}）`;
                
                // 3. 用户反馈数
                const feedbackTotal = document.getElementById('feedback-total');
                const feedbackDetail = document.getElementById('feedback-detail');
                if (feedbackTotal) feedbackTotal.textContent = data.feedback.total;
                if (feedbackDetail) feedbackDetail.textContent = `（未回复：${data.feedback.pending} / 已回复：${data.feedback.processed}）`;
                
                // 4. 违停告警数
                const alertTotal = document.getElementById('alert-total');
                const alertDetail = document.getElementById('alert-detail');
                if (alertTotal) alertTotal.textContent = data.alert.total;
                if (alertDetail) alertDetail.textContent = `（未处理：${data.alert.unprocessed} / 已处理：${data.alert.processed}）`;
                
                // 渲染图表
                if (data.trend) {
                    console.log('Rendering trend chart with data:', data.trend);
                    renderTrendChart(data.trend);
                } else {
                    console.warn('No trend data received');
                }
                
                if (data.camera_share) {
                    console.log('Rendering pie chart with data:', data.camera_share);
                    renderPieChart(data.camera_share);
                } else {
                    console.warn('No camera share data received');
                }
            }
        })
        .catch(error => {
            console.error('Failed to fetch stats:', error);
        });
    }

    // 图表实例
    let trendChartInstance = null;
    let pieChartInstance = null;

    function renderTrendChart(trendData) {
        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        if (typeof Chart === 'undefined') {
            ctx.parentNode.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:#ff4d4f;">图表组件加载失败，请检查网络</div>';
            return;
        }
        
        if (trendChartInstance) trendChartInstance.destroy();
        
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.labels,
                datasets: [{
                    label: '违停告警数',
                    data: trendData.data,
                    borderColor: '#096dd9',
                    backgroundColor: 'rgba(9,109,217,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: { displayColors: false }
                },
                scales: { 
                    x: {
                        ticks: { color: '#ffffff' },
                        grid: { color: 'rgba(255, 255, 255, 0.3)' },
                        border: { color: '#ffffff' }
                    },
                    y: { 
                        beginAtZero: true, 
                        ticks: { stepSize: 1, color: '#ffffff' },
                        grid: { color: 'rgba(255, 255, 255, 0.3)' },
                        border: { color: '#ffffff' }
                    } 
                }
            }
        });
    }

    function renderPieChart(shareData) {
        const ctx = document.getElementById('pieChart');
        if (!ctx) return;

        if (typeof Chart === 'undefined') {
             ctx.parentNode.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:#ff4d4f;">图表组件加载失败，请检查网络</div>';
             return;
        }

        if (pieChartInstance) pieChartInstance.destroy();

        // 计算总数用于百分比
        const total = shareData.data.reduce((a, b) => a + b, 0);
        const isNoData = total === 0;

        // 动态生成颜色
        const colors = [
            '#096dd9', '#00a86b', '#ff4d4f', '#722ed1', '#faad14', 
            '#eb2f96', '#13c2c2', '#fa8c16', '#a0d911', '#52c41a'
        ];
        
        let displayLabels = shareData.labels;
        let displayData = shareData.data;
        let displayColors = shareData.labels.map((_, i) => colors[i % colors.length]);

        // 如果没有数据，显示一个灰色的占位饼图
        if (isNoData) {
            displayLabels = ['暂无数据'];
            displayData = [1]; // 占位数据
            displayColors = ['#d9d9d9']; // 灰色
        }

        pieChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: displayLabels,
                datasets: [{
                    data: displayData,
                    backgroundColor: displayColors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        color: '#fff',
                        font: { weight: 'bold' },
                        formatter: (value, ctx) => {
                            if (isNoData) return '无数据';
                            if (total === 0) return '0%';
                            let percentage = Math.round((value / total) * 100) + '%';
                            return percentage;
                        },
                        display: function(context) {
                            if (isNoData) return true; // Show label for placeholder
                            return context.dataset.data[context.dataIndex] > 0;
                        }
                    },
                    legend: { 
                        position: 'bottom', 
                        display: !isNoData, // 没数据时不显示图例
                        labels: { 
                            boxWidth: 12, 
                            color: '#ffffff',
                            font: { size: 12 },
                            generateLabels: function(chart) {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map(function(label, i) {
                                        const meta = chart.getDatasetMeta(0);
                                        const ds = data.datasets[0];
                                        const value = shareData.data[i]; // Use original data for value display
                                        const fill = ds.backgroundColor[i];
                                        
                                        return {
                                            text: `${label}`,
                                            fillStyle: fill,
                                            fontColor: '#ffffff',
                                            hidden: isNaN(ds.data[i]) || meta.data[i].hidden,
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        } 
                    },
                    tooltip: {
                        enabled: !isNoData, // 没数据时不显示提示框
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                let value = shareData.data[context.dataIndex]; // Use original data
                                let percentage = total > 0 ? Math.round((value / total) * 100) + '%' : '0%';
                                return `${label}: ${percentage} (${value}次)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Logout Logic
    const logoutBtn = document.querySelector('.header .right button');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            sessionStorage.removeItem('token');
            sessionStorage.removeItem('user_info');
            window.location.href = '/auth'; // Redirect to login page
        });
    }

    // Menu Toggle
    document.querySelectorAll('.menu-title').forEach(item => {
    item.addEventListener('click', function(e) {
        // 如果点击的是链接（没有子菜单），不阻止默认行为
        const submenu = this.nextElementSibling;
        if (!submenu) return;

        e.preventDefault(); // 阻止链接跳转（如果有href="#"）
        
        // 切换 active 类
        this.classList.toggle('active');
        
        // 根据 active 类状态控制子菜单显示
        if (this.classList.contains('active')) {
            submenu.style.display = 'block';
        } else {
            submenu.style.display = 'none';
        }
    });
});
}); // End DOMContentLoaded

