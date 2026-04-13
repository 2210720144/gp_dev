function switchTab(tab) {
    const loginBtn = document.getElementById('login-tab');
    const registerBtn = document.getElementById('register-tab');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const resetForm = document.getElementById('reset-form');
    const authToggle = document.querySelector('.auth-toggle');

    // Ensure reset form is hidden when switching between login/register
    if (resetForm) {
        resetForm.classList.remove('active');
    }

    // Show auth toggle buttons if they were hidden
    if (authToggle) {
        authToggle.style.display = 'flex'; // Restore display
    }

    if (tab === 'login') {
        loginBtn.classList.add('active');
        registerBtn.classList.remove('active');
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
    } else {
        loginBtn.classList.remove('active');
        registerBtn.classList.add('active');
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
    }
}

function showResetForm() {
    const loginBtn = document.getElementById('login-tab');
    const registerBtn = document.getElementById('register-tab');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const resetForm = document.getElementById('reset-form');
    const authToggle = document.querySelector('.auth-toggle');

    // Deactivate tabs
    loginBtn.classList.remove('active');
    registerBtn.classList.remove('active');

    // Hide main forms
    loginForm.classList.remove('active');
    registerForm.classList.remove('active');

    // Hide toggle buttons
    if (authToggle) {
        authToggle.style.display = 'none';
    }

    // Show reset form
    if (resetForm) {
        resetForm.classList.add('active');
    }
}

function sendCode(btn) {
    // Get the email input associated with this form
    // The button is inside .input-group.code-group, which is sibling to other input-groups
    // We need to find the email input in the same form.
    const form = btn.closest('.auth-form');
    const emailInput = form.querySelector('input[type="email"]');
    const email = emailInput.value.trim();

    if (!email) {
        alert('请先输入邮箱');
        return;
    }

    // Call API to send code
    fetch('/send-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 200) {
            alert('验证码已发送，请查收邮件');
            // Start countdown
            let seconds = 60;
            btn.disabled = true;
            btn.textContent = `${seconds}s后重发`;
            btn.style.backgroundColor = '#333333'; 

            const timer = setInterval(() => {
                seconds--;
                if (seconds > 0) {
                    btn.textContent = `${seconds}s后重发`;
                } else {
                    clearInterval(timer);
                    btn.disabled = false;
                    btn.textContent = '发送验证码';
                    btn.style.backgroundColor = ''; 
                }
            }, 1000);
        } else {
            alert(data.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发送验证码失败，请稍后重试');
    });
}

function togglePassword(element) {
    const input = element.previousElementSibling;
    const eyeIcon = element.querySelector('.eye-icon');
    const eyeOffIcon = element.querySelector('.eye-off-icon');

    if (input.type === "password") {
        input.type = "text";
        // Password visible -> Show 'eye' (open)
        if (eyeIcon) eyeIcon.style.display = 'block';
        if (eyeOffIcon) eyeOffIcon.style.display = 'none';
        
        element.style.color = '#4A6FA5'; // Active color
    } else {
        input.type = "password";
        // Password hidden -> Show 'eye-off' (closed)
        if (eyeIcon) eyeIcon.style.display = 'none';
        if (eyeOffIcon) eyeOffIcon.style.display = 'block';
        
        element.style.color = ''; // Reset color
    }
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Register Form Submission
    const registerSubmitBtn = document.querySelector('.register-submit');
    if (registerSubmitBtn) {
        registerSubmitBtn.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent default button behavior
            
            const registerForm = document.getElementById('register-form');
            const inputs = registerForm.querySelectorAll('input');
            
            // Assuming order: [0]Username, [1]Email, [2]Password, [3]ConfirmPassword, [4]Code
            const username = inputs[0].value.trim();
            const email = inputs[1].value.trim();
            const password = inputs[2].value;
            const confirmPassword = inputs[3].value;
            const code = inputs[4].value.trim();
            
            if (!username || !email || !password || !confirmPassword || !code) {
                alert('请填写所有必填项（包括验证码）');
                return;
            }
            
            if (password !== confirmPassword) {
                alert('两次输入的密码不一致');
                return;
            }
            
            // Prepare data
            const data = {
                username: username,
                email: email,
                password: password,
                code: code
            };
            
            // Send request
            fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.code === 200) {
                    alert(data.msg); // "注册申请提交成功..."
                    // Switch to login tab
                    switchTab('login');
                } else {
                    alert(data.msg); // Show error message
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('注册请求失败，请检查网络或联系管理员');
            });
        });
    }

    // Login Form Submission
    const loginSubmitBtn = document.querySelector('#login-form .submit-btn');
    const loginForm = document.getElementById('login-form');

    if (loginSubmitBtn && loginForm) {
        // Handle Enter key press
        loginForm.querySelectorAll('input').forEach(input => {
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    loginSubmitBtn.click();
                }
            });
        });

        loginSubmitBtn.addEventListener('click', function(e) {
            e.preventDefault();

            const loginForm = document.getElementById('login-form');
            const inputs = loginForm.querySelectorAll('input');
            const loginId = inputs[0].value.trim(); // username/email
            const password = inputs[1].value;

            if (!loginId || !password) {
                alert('请输入用户名/邮箱和密码');
                return;
            }

            const data = {
                login_id: loginId,
                password: password
            };

            fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.code === 200) {
                    // Login successful
                    // Store token (e.g., in localStorage) - Optional but recommended for JWT
                    localStorage.setItem('token', data.data.token);
                    // Store user info
                    localStorage.setItem('user_info', JSON.stringify(data.data.user));
                    
                    // Redirect based on role
                    const role = data.data.user.role;
                    if (role === '管理员用户' || role === '超级管理员') {
                        window.location.href = '/admin';
                    } else {
                        window.location.href = '/user';
                    }
                } else {
                    alert(data.msg);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('登录请求失败，请检查网络');
            });
        });
    }
});
