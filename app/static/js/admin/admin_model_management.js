/**
 * 模型管理页面脚本
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Model management page loaded.');
    
    // Modal Elements
    const modal = document.getElementById('addModelModal');
    const addModelBtn = document.getElementById('addModelBtn');
    const closeBtn = document.querySelector('.close-btn');
    const cancelBtn = document.getElementById('cancelBtn');
    const confirmBtn = document.getElementById('confirmBtn');
    
    // File Upload Elements
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('modelFileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    
    let selectedFile = null;

    // Show Modal
    if (addModelBtn) {
        addModelBtn.addEventListener('click', () => {
            modal.classList.remove('hidden');
        });
    }

    // Hide Modal
    const hideModal = () => {
        modal.classList.add('hidden');
        resetForm();
    };

    if (closeBtn) closeBtn.addEventListener('click', hideModal);
    if (cancelBtn) cancelBtn.addEventListener('click', hideModal);
    
    // Click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideModal();
    });

    // File Upload Logic
    dropArea.addEventListener('click', () => fileInput.click());

    dropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.classList.add('dragover');
    });

    dropArea.addEventListener('dragleave', () => {
        dropArea.classList.remove('dragover');
    });

    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        dropArea.classList.add('hidden'); // Hide drop area, could also keep it but show file info
        dropArea.style.display = 'none';
        fileInfo.classList.remove('hidden');
    }

    removeFile.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        fileInfo.classList.add('hidden');
        dropArea.style.display = 'block';
    });

    function resetForm() {
        document.getElementById('addModelForm').reset();
        selectedFile = null;
        fileInfo.classList.add('hidden');
        dropArea.style.display = 'block';
    }

    // Confirm Upload
    confirmBtn.addEventListener('click', async () => {
        const modelName = document.getElementById('modelName').value.trim();
        
        if (!modelName) {
            alert('请输入模型名称');
            return;
        }
        if (!selectedFile) {
            alert('请上传模型文件');
            return;
        }

        const formData = new FormData();
        formData.append('model_name', modelName);
        formData.append('model_file', selectedFile);

        try {
            // Get JWT token from local storage or cookie if needed. 
            // Assuming the browser handles cookies or we need to add Authorization header manually.
            // Since this is a pair programming task, I'll assume standard fetch with credentials or token handling.
            // If the app uses sessionStorage for token:
            const token = sessionStorage.getItem('token');
            
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            confirmBtn.disabled = true;
            confirmBtn.textContent = '上传中...';

            const response = await fetch('/api/model/add', {
                method: 'POST',
                headers: headers,
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.code === 200) {
                alert('模型添加成功');
                hideModal();
                location.reload(); // Refresh list
            } else {
                alert('添加失败: ' + (result.msg || '未知错误'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('网络错误，请稍后重试');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.textContent = '确定上传';
        }
    });

    // Load Model List
    fetchModelList();

    function fetchModelList() {
        const token = sessionStorage.getItem('token');
        fetch('/api/model/list', {
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.code === 200) {
                renderModelTable(data.data);
            } else {
                console.error('Failed to load models:', data.msg);
            }
        })
        .catch(error => console.error('Error:', error));
    }

    function renderModelTable(models) {
        const tbody = document.querySelector('.data-table tbody');
        tbody.innerHTML = ''; // Clear existing data

        if (models.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">暂无模型数据</td></tr>';
            return;
        }

        models.forEach(model => {
            const tr = document.createElement('tr');
            if (model.status === '启用') {
                tr.classList.add('active-row');
            }

            const statusHtml = model.status === '启用' 
                ? `<span class="status-tag active">启用</span>` 
                : `<span class="status-tag inactive">停用</span>`;

            // Actions
            let actionsHtml = `
                <button class="action-btn btn-view" onclick="viewModel(${model.model_id})" title="查看详情">查看详情</button>
            `;
            
            if (model.status !== '启用') {
                actionsHtml += `
                    <button class="action-btn btn-enable" onclick="enableModel(${model.model_id})" title="启用">启用</button>
                    <button class="action-btn btn-delete" onclick="deleteModel(${model.model_id})" title="删除">删除</button>
                `;
            }

            tr.innerHTML = `
                <td>${model.model_id}</td>
                <td>${model.model_name}</td>
                <td>${statusHtml}</td>
                <td>${actionsHtml}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Expose functions to global scope for onclick handlers
    window.viewModel = function(id) {
        const token = sessionStorage.getItem('token');
        fetch(`/api/model/detail/${id}`, {
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                const model = data.data;
                document.getElementById('viewModelId').value = model.model_id;
                document.getElementById('viewId').value = model.model_id;
                document.getElementById('viewName').value = model.model_name;
                
                // Truncate path to show only from /gp_dev onwards
                let fullPath = model.full_path;
                // Handle both Windows and Unix separators
                const keyword = 'gp_dev';
                // Try to find /gp_dev or \gp_dev
                let index = fullPath.indexOf('/' + keyword);
                if (index === -1) index = fullPath.indexOf('\\' + keyword);
                
                if (index !== -1) {
                    fullPath = fullPath.substring(index);
                }
                
                document.getElementById('viewPath').value = fullPath;
                document.getElementById('viewStatus').value = model.status;
                document.getElementById('viewUploader').value = model.upload_by;
                document.getElementById('viewTime').value = model.upload_at;
                
                document.getElementById('viewModelModal').classList.remove('hidden');
            } else {
                alert('获取详情失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    };
    
    window.closeViewModal = function() {
        document.getElementById('viewModelModal').classList.add('hidden');
    };
    
    window.saveModelDetail = function() {
        const id = document.getElementById('viewModelId').value;
        const name = document.getElementById('viewName').value;
        
        if (!name) {
            alert('模型名称不能为空');
            return;
        }
        
        const token = sessionStorage.getItem('token');
        fetch(`/api/model/update/${id}`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_name: name })
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                alert('保存成功');
                closeViewModal();
                fetchModelList();
            } else {
                alert('保存失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    };

    window.enableModel = function(id) {
        if(!confirm('确定要启用该模型吗？这将停用当前正在使用的模型。')) return;
        
        const token = sessionStorage.getItem('token');
        fetch(`/api/model/enable/${id}`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                alert('启用成功');
                fetchModelList();
            } else {
                alert('启用失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    };
    window.deleteModel = function(id) {
        if(!confirm('确定要删除该模型吗？此操作不可恢复。')) return;

        const token = sessionStorage.getItem('token');
        fetch(`/api/model/delete/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                alert('删除成功');
                fetchModelList();
            } else {
                alert('删除失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('系统错误');
        });
    };
});
