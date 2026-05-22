document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('add-video-form');
    const testBtn = document.getElementById('test-connection-btn');
    const urlInput = document.querySelector('input[name="url"]');
    const testResult = document.getElementById('test-result');
    const sourceTypeRadios = document.querySelectorAll('input[name="source_type"]');
    const streamGroup = document.getElementById('stream-input-group');
    const fileGroup = document.getElementById('file-input-group');
    const fileInput = document.getElementById('video-file-input');
    const previewContainer = document.getElementById('file-preview-container');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileSizeDisplay = document.getElementById('file-size-display');

    function showTestResult(message, type) {
        testResult.textContent = message;
        testResult.className = `test-result ${type}`;
        testResult.style.display = 'block';
    }

    function hideTestResult() {
        testResult.textContent = '';
        testResult.className = 'test-result';
        testResult.style.display = 'none';
    }

    function setSourceTypeUI(sourceType) {
        const isStream = sourceType === 'stream';

        streamGroup.classList.toggle('hidden', !isStream);
        fileGroup.classList.toggle('hidden', isStream);

        if (isStream) {
            urlInput.setAttribute('required', 'required');
            fileInput.removeAttribute('required');
        } else {
            urlInput.removeAttribute('required');
            fileInput.setAttribute('required', 'required');
            hideTestResult();
        }
    }

    function buildSuccessMessage(data) {
        if (!data) {
            return '连接成功';
        }

        const details = [];
        if (data.format) {
            details.push(data.format);
        }
        if (data.width && data.height) {
            details.push(`${data.width}x${data.height}`);
        }
        if (data.fps) {
            details.push(`${data.fps} FPS`);
        }

        return details.length > 0
            ? `连接成功：${details.join(' / ')}`
            : '连接成功';
    }

    function setTestingState(isTesting) {
        if (!testBtn) {
            return;
        }

        testBtn.classList.toggle('testing', isTesting);
        testBtn.disabled = isTesting;
        testBtn.textContent = isTesting ? '测试中...' : '测试连接';
    }

    function resetFormUI() {
        previewContainer.classList.add('hidden');
        fileNameDisplay.textContent = '';
        fileSizeDisplay.textContent = '';
        hideTestResult();
        setSourceTypeUI('stream');

        const streamRadio = document.querySelector('input[name="source_type"][value="stream"]');
        if (streamRadio) {
            streamRadio.checked = true;
        }
    }

    sourceTypeRadios.forEach(radio => {
        radio.addEventListener('change', function () {
            setSourceTypeUI(this.value);
        });
    });

    setSourceTypeUI(document.querySelector('input[name="source_type"]:checked')?.value || 'stream');

    if (fileInput) {
        fileInput.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (!file) {
                previewContainer.classList.add('hidden');
                fileNameDisplay.textContent = '';
                fileSizeDisplay.textContent = '';
                return;
            }

            const maxSize = 3 * 1024 * 1024 * 1024;
            if (file.size > maxSize) {
                alert('文件大小超出限制，请选择较小的视频文件。');
                fileInput.value = '';
                previewContainer.classList.add('hidden');
                fileNameDisplay.textContent = '';
                fileSizeDisplay.textContent = '';
                return;
            }

            fileNameDisplay.textContent = file.name;
            fileSizeDisplay.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            previewContainer.classList.remove('hidden');

            const nameInput = document.querySelector('input[name="name"]');
            if (nameInput && !nameInput.value) {
                nameInput.value = file.name.replace(/\.[^.]+$/, '');
            }
        });
    }

    if (testBtn) {
        testBtn.addEventListener('click', async function () {
            const selectedType = document.querySelector('input[name="source_type"]:checked')?.value;
            if (selectedType !== 'stream') {
                showTestResult('本地文件无需测试视频流连接。', 'error');
                return;
            }

            const url = urlInput.value.trim();
            if (!url) {
                showTestResult('请输入视频流地址。', 'error');
                return;
            }

            const token = sessionStorage.getItem('token');
            if (!token) {
                showTestResult('登录状态已失效，请重新登录后再试。', 'error');
                return;
            }

            hideTestResult();
            setTestingState(true);

            const controller = new AbortController();
            const timeoutId = window.setTimeout(() => controller.abort(), 12000);

            try {
                const response = await fetch('/api/video-source/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ url }),
                    signal: controller.signal
                });

                const data = await response.json();
                if (response.ok && data.code === 200) {
                    showTestResult(buildSuccessMessage(data.data), 'success');
                } else {
                    showTestResult(data.msg || '测试失败，请检查视频流地址。', 'error');
                }
            } catch (error) {
                console.error('Test stream error:', error);
                if (error.name === 'AbortError') {
                    showTestResult('测试超时，请检查网络或视频流是否可访问。', 'error');
                } else {
                    showTestResult('测试请求失败，请稍后重试。', 'error');
                }
            } finally {
                window.clearTimeout(timeoutId);
                setTestingState(false);
            }
        });
    }

    if (form) {
        const cancelBtn = document.getElementById('cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function () {
                form.reset();
                resetFormUI();
            });
        }

        form.addEventListener('submit', function (event) {
            event.preventDefault();

            const submitBtn = form.querySelector('.submit-btn');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = '保存中...';

            const formData = new FormData(form);
            const token = sessionStorage.getItem('token');

            fetch('/api/video-source/add', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token
                },
                body: formData
            })
                .then(response => {
                    if (response.status === 413) {
                        throw new Error('文件大小超过服务器限制（最大 3GB）。');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.code === 200) {
                        alert('视频源添加成功！');
                        form.reset();
                        resetFormUI();
                    } else {
                        alert('添加失败：' + (data.msg || '未知错误'));
                    }
                })
                .catch(error => {
                    console.error('Add video source error:', error);
                    if (error.message.includes('文件大小')) {
                        alert(error.message);
                    } else {
                        alert('系统错误，请稍后重试。');
                    }
                })
                .finally(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                });
        });
    }
});
