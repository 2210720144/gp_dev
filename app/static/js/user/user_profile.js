document.addEventListener('DOMContentLoaded', function() {
    // 1. 加载用户信息
    loadUserProfile();

    // 2. 绑定修改密码表单提交
    const form = document.getElementById('change-password-form');
    if (form) {
        form.addEventListener('submit', handleChangePassword);
    }

    // 3. 绑定获取验证码按钮
    const sendCodeBtn = document.getElementById('send-code-btn');
    if (sendCodeBtn) {
        sendCodeBtn.addEventListener('click', sendCode);
    }

    // 4. 绑定密码显示/隐藏切换
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const eyeIcon = this.querySelector('.eye-icon');
            const eyeOffIcon = this.querySelector('.eye-off-icon');

            if (input.type === 'password') {
                input.type = 'text';
                eyeIcon.style.display = 'block';
                eyeOffIcon.style.display = 'none';
            } else {
                input.type = 'password';
                eyeIcon.style.display = 'none';
                eyeOffIcon.style.display = 'block';
            }
        });
    });
});

// 全局变量保存当前用户邮箱
let currentUserEmail = '';

function loadUserProfile() {
    // 优先从 localStorage 获取基本信息展示，减少白屏时间
    const userInfoStr = localStorage.getItem('user_info');
    if (userInfoStr) {
        try {
            const user = JSON.parse(userInfoStr);
            currentUserEmail = user.email; // 保存邮箱
            renderProfile(user);
        } catch (e) {
            console.error('Error parsing local user info:', e);
        }
    }

    // 如果需要获取最新信息，可在此处调用 API
}

function sendCode() {
    if (!currentUserEmail) {
        alert('无法获取用户邮箱，请尝试重新登录');
        return;
    }

    const btn = document.getElementById('send-code-btn');
    btn.disabled = true;
    
    // 倒计时逻辑
    let count = 60;
    btn.textContent = `${count}s`;
    const timer = setInterval(() => {
        count--;
        btn.textContent = `${count}s`;
        if (count <= 0) {
            clearInterval(timer);
            btn.disabled = false;
            btn.textContent = '获取验证码';
        }
    }, 1000);

    // 发送请求
    fetch('/send-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            email: currentUserEmail,
            usage: 'change_password' // 明确用途，允许现有邮箱
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 200) {
            alert('验证码已发送至您的邮箱：' + currentUserEmail);
        } else {
            alert(data.msg);
            // 发送失败，重置按钮
            clearInterval(timer);
            btn.disabled = false;
            btn.textContent = '获取验证码';
        }
    })
    .catch(err => {
        console.error(err);
        alert('发送失败，请检查网络');
        clearInterval(timer);
        btn.disabled = false;
        btn.textContent = '获取验证码';
    });
}

function renderProfile(user) {
    document.getElementById('profile-id').textContent = user.user_id || '-';
    document.getElementById('profile-username').textContent = user.username || '-';
    document.getElementById('profile-email').textContent = user.email || '-';
    document.getElementById('profile-role').textContent = user.role || '-';
    document.getElementById('profile-status').textContent = user.status || '-';

    // 格式化时间
    if (user.created_at) {
        try {
            document.getElementById('profile-created').textContent = new Date(user.created_at).toLocaleString();
        } catch(e) {
            document.getElementById('profile-created').textContent = user.created_at;
        }
    }
}

function handleChangePassword(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // 简单校验
    if (!data.code) {
        alert('请输入验证码');
        return;
    }

    if (data.new_password !== data.confirm_password) {
        alert('两次输入的新密码不一致');
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        alert('登录已过期，请重新登录');
        window.location.href = '/auth';
        return;
    }

    // 调用修改密码接口
    fetch('/change-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
            code: data.code,
            new_password: data.new_password
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.code === 200) {
            alert('密码修改成功，请重新登录');
            // 清除 Token 并跳转登录
            localStorage.removeItem('token');
            localStorage.removeItem('user_info');
            window.location.href = '/auth';
        } else {
            alert(result.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('请求失败，请检查网络');
    });
}