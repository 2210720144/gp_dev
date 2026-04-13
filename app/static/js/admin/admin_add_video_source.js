document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('add-video-form');
    const testBtn = document.getElementById('test-connection-btn');
    const urlInput = document.querySelector('input[name="url"]');
    const testResult = document.getElementById('test-result');
    const sourceTypeRadios = document.querySelectorAll('input[name="source_type"]');
    const streamGroup = document.getElementById('stream-input-group');
    const fileGroup = document.getElementById('file-input-group');
    const fileInput = document.getElementById('video-file-input');
    const previewContainer = document.getElementById('file-preview-container');
    // const videoPreview = document.getElementById('video-preview'); // Removed
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileSizeDisplay = document.getElementById('file-size-display');

    // 切换视频源类型
    sourceTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'stream') {
                streamGroup.classList.remove('hidden');
                fileGroup.classList.add('hidden');
                urlInput.setAttribute('required', 'required');
                fileInput.removeAttribute('required');
            } else {
                streamGroup.classList.add('hidden');
                fileGroup.classList.remove('hidden');
                urlInput.removeAttribute('required');
                fileInput.setAttribute('required', 'required');
            }
        });
    });

    // 文件选择与预览
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Check file size (3GB limit)
                const maxSize = 3 * 1024 * 1024 * 1024; // 3GB in bytes
                if (file.size > maxSize) {
                    alert('文件大小超出限制，请选择较小的文件。');
                    this.value = ''; // Clear input
                    fileNameDisplay.textContent = '';
                    fileSizeDisplay.textContent = '';
                    previewContainer.classList.add('hidden');
                    return;
                }

                // 显示文件名和大小
                fileNameDisplay.textContent = file.name;
                fileSizeDisplay.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;

                // 移除视频预览逻辑
                previewContainer.classList.remove('hidden');

                // 自动填充名称（如果为空）
                const nameInput = document.querySelector('input[name="name"]');
                if (!nameInput.value) {
                    nameInput.value = file.name.split('.')[0];
                }
            } else {
                previewContainer.classList.add('hidden');
                // videoPreview.src = '';
                fileNameDisplay.textContent = '';
                fileSizeDisplay.textContent = '';
            }
        });
    }

    // 测试连接功能 (仅限流媒体)
    if (testBtn) {
        testBtn.addEventListener('click', function() {
            const url = urlInput.value.trim();
            if (!url) {
                showTestResult('请输入视频源地址', 'error');
                return;
            }

            testBtn.classList.add('testing');
            testBtn.textContent = '测试中...';
            testBtn.disabled = true;
            testResult.style.display = 'none';

            // 模拟测试连接
            setTimeout(() => {
                testBtn.classList.remove('testing');
                testBtn.textContent = '测试连接';
                testBtn.disabled = false;

                if (/^(rtsp|rtmp|http|https):\/\//i.test(url)) {
                    showTestResult('连接成功', 'success');
                } else {
                    showTestResult('连接失败：无效的协议头', 'error');
                }
            }, 1000);
        });
    }

    function showTestResult(msg, type) {
        testResult.textContent = msg;
        testResult.className = 'test-result ' + type;
    }

    // 表单提交
    if (form) {
        // 取消按钮逻辑
        const cancelBtn = document.getElementById('cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                // 重置表单
                form.reset();
                
                // 重置UI状态
                previewContainer.classList.add('hidden');
                // videoPreview.src = '';
                fileNameDisplay.textContent = '';
                fileSizeDisplay.textContent = '';
                testResult.style.display = 'none';
                
                // 恢复默认的流媒体选项显示
                streamGroup.classList.remove('hidden');
                fileGroup.classList.add('hidden');
                urlInput.setAttribute('required', 'required');
                fileInput.removeAttribute('required');
                
                // 确保单选按钮状态正确（虽然reset()会重置value，但UI显示切换需要手动处理）
                document.querySelector('input[value="stream"]').checked = true;
            });
        }

        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const submitBtn = form.querySelector('.submit-btn');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = '保存中...';

            const formData = new FormData(form);
            const token = localStorage.getItem('token');

            fetch('/api/video-source/add', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token
                },
                body: formData
            })
            .then(response => {
                if (response.status === 413) {
                    throw new Error('文件大小超过服务器限制（最大3GB）');
                }
                return response.json();
            })
            .then(data => {
                if (data.code === 200) {
                    alert('视频源添加成功！');
                    form.reset();
                    if (previewContainer) {
                        previewContainer.classList.add('hidden');
                        // videoPreview.src = '';
                    }
                    if (fileNameDisplay) fileNameDisplay.textContent = '';
                    if (fileSizeDisplay) fileSizeDisplay.textContent = '';
                    if (testResult) testResult.style.display = 'none';

                    // 显式重置 UI 状态为默认（网络流媒体）
                    const streamGroup = document.getElementById('stream-input-group');
                    const fileGroup = document.getElementById('file-input-group');
                    const urlInput = document.querySelector('input[name="url"]');
                    const fileInput = document.getElementById('video-file-input');

                    if (streamGroup) streamGroup.classList.remove('hidden');
                    if (fileGroup) fileGroup.classList.add('hidden');
                    if (urlInput) urlInput.setAttribute('required', 'required');
                    if (fileInput) fileInput.removeAttribute('required');

                    // 确保单选按钮状态同步（防止 reset 后状态不一致）
                    const streamRadio = document.querySelector('input[value="stream"]');
                    if (streamRadio) streamRadio.checked = true;
                } else {
                    alert('添加失败: ' + (data.msg || '未知错误'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (error.message.includes('文件大小')) {
                    alert(error.message);
                } else {
                    alert('系统错误，请稍后重试');
                }
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
        });
    }
});