document.addEventListener('DOMContentLoaded', function() {
    // 1. 权限控制：检查是否为超级管理员
    const userInfoStr = sessionStorage.getItem('user_info');
    if (userInfoStr) {
        try {
            const userInfo = JSON.parse(userInfoStr);
            const isAdminYes = document.getElementById('admin-yes');
            
            // 只有超级管理员可以选择"是"
            if (userInfo.role !== '超级管理员') {
                if (isAdminYes) {
                    isAdminYes.disabled = true;
                    document.getElementById('admin-no').checked = true;
                    
                    // 添加提示信息
                    const radioGroup = document.querySelector('.radio-group');
                    if (radioGroup) {
                        const hint = document.createElement('div');
                        hint.textContent = '仅超级管理员可创建管理员账号';
                        hint.style.fontSize = '12px';
                        hint.style.color = '#666'; // 使用灰色提示文字
                        hint.style.marginTop = '4px';
                        radioGroup.parentNode.appendChild(hint);
                    }
                }
            } else {
                if (isAdminYes) isAdminYes.disabled = false;
            }
        } catch (e) {
            console.error('Error parsing user info:', e);
        }
    }

    // 2. 密码可见性切换
    const toggleDivs = document.querySelectorAll('.toggle-password');
    toggleDivs.forEach(div => {
        div.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const eyeIcon = this.querySelector('.eye-icon');
            const eyeOffIcon = this.querySelector('.eye-off-icon');

            if (input) {
                if (input.type === 'password') {
                    input.type = 'text';
                    // Show eye (open), hide eye-off (closed)
                    if (eyeIcon) eyeIcon.style.display = 'block';
                    if (eyeOffIcon) eyeOffIcon.style.display = 'none';
                    this.style.color = 'var(--text-main)'; // Highlight
                } else {
                    input.type = 'password';
                    // Hide eye, show eye-off
                    if (eyeIcon) eyeIcon.style.display = 'none';
                    if (eyeOffIcon) eyeOffIcon.style.display = 'block';
                    this.style.color = ''; // Reset color
                }
            }
        });
    });
});

document.getElementById('create-account-form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    // 简单校验
    if (data.password !== data.confirm_password) {
        alert('两次输入的密码不一致');
        return;
    }

    // 这里调用新的通用创建接口
    // 注意：需要从 sessionStorage 获取 Token，因为这是一个受保护的接口
    const token = sessionStorage.getItem('token');

    if (!token) {
        alert('登录已过期，请重新登录');
        window.location.href = '/auth'; // 假设登录页路由是 /auth
        return;
    }

    fetch('/admin/create-account', {
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
            alert('账号创建成功！');
            // 可以选择重置表单或跳转回列表页
            this.reset();
        } else {
            alert(result.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('请求失败，请检查网络或权限');
    });
});