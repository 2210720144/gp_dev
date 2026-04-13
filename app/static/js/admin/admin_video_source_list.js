document.addEventListener('DOMContentLoaded', function() {
    const tableBody = document.getElementById('video-table-body');
    
    // Modal elements
    const modal = document.getElementById('detailModal');
    const closeModalBtn = document.querySelector('.close-modal');
    const cancelModalBtn = document.querySelector('.btn-cancel-modal');
    const detailForm = document.getElementById('detailForm');
    let currentVideoId = null;
    let videoListCache = []; // Store fetched data locally

    // Close modal events
    closeModalBtn.onclick = () => modal.classList.remove('show');
    cancelModalBtn.onclick = () => modal.classList.remove('show');
    window.onclick = (e) => {
        if (e.target === modal) modal.classList.remove('show');
    };

    // Handle form submission
    detailForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!currentVideoId) return;

        const newName = document.getElementById('detail-name').value;
        const newLocation = document.getElementById('detail-location').value;
        const token = localStorage.getItem('token');

        // Simple validation
        if (!newName.trim() || !newLocation.trim()) {
            alert('名称和区域不能为空');
            return;
        }

        fetch(`/api/video-source/update/${currentVideoId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                video_name: newName,
                location: newLocation
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.code === 200) {
                alert('修改成功');
                modal.classList.remove('show');
                fetchVideoList(); // Refresh table
            } else {
                alert('修改失败: ' + data.msg);
            }
        })
        .catch(err => {
            console.error(err);
            alert('请求出错');
        });
    });

    // Fetch data from API
    fetchVideoList();

    function fetchVideoList() {
        const token = localStorage.getItem('token');
        fetch('/api/video-source/list', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.code === 200) {
                videoListCache = data.data; // Cache data for modal
                renderTable(data.data);
            } else {
                tableBody.innerHTML = `<tr><td colspan="5" class="error-text">加载失败: ${data.msg}</td></tr>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            tableBody.innerHTML = `<tr><td colspan="5" class="error-text">系统错误，请重试</td></tr>`;
        });
    }

    function renderTable(data) {
        tableBody.innerHTML = '';
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="empty-text">暂无视频源数据</td></tr>`;
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            
            let statusClass = '';
            // 根据后端状态映射样式
            if (item.config_status === '已配置') statusClass = 'status-active';
            else if (item.config_status === '未配置') statusClass = 'status-pending';
            else statusClass = 'status-disabled';

            tr.innerHTML = `
                <td>${item.video_id}</td>
                <td>${item.video_name || '未命名'}</td>
                <td>${item.format}</td>
                <td><span class="status-badge ${statusClass}">${item.config_status}</span></td>
                <td>
                    <button class="action-btn btn-view" onclick="viewVideo('${item.video_id}')">查看详情</button>
                    <button class="action-btn btn-preview" onclick="previewVideo('${item.video_id}', '${item.video_url}')">预览</button>
                    <button class="action-btn btn-delete" onclick="deleteVideo('${item.video_id}')">删除</button>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    }

    // Window functions for buttons
    window.viewVideo = function(id) {
        // Find data from cache
        const video = videoListCache.find(v => v.video_id == id);
        if (!video) return;

        currentVideoId = id;
        
        // Fill form
        document.getElementById('detail-id').value = video.video_id;
        document.getElementById('detail-name').value = video.video_name || '';
        document.getElementById('detail-url').value = video.video_url;
        document.getElementById('detail-location').value = video.location || '';
        document.getElementById('detail-format').value = video.format;
        document.getElementById('detail-upload-time').value = video.upload_time;
        document.getElementById('detail-upload-by').value = video.upload_by;
        document.getElementById('detail-status').value = video.config_status;
        document.getElementById('detail-camera-id').value = video.camera_id || '无';

        // Show modal
        modal.classList.add('show');
    };

    // Preview Logic
    const previewModal = document.getElementById('previewModal');
    const closePreviewBtn = document.querySelector('.close-preview');
    const videoPlayer = document.getElementById('previewPlayer');
    const previewMessage = document.getElementById('previewMessage');
    let flvPlayer = null;
    let hls = null;

    function closePreview() {
        previewModal.classList.remove('show');
        videoPlayer.pause();
        videoPlayer.src = '';
        videoPlayer.load();
        previewMessage.classList.add('hidden');
        
        // Destroy players
        if (flvPlayer) {
            flvPlayer.destroy();
            flvPlayer = null;
        }
        if (hls) {
            hls.destroy();
            hls = null;
        }
    }

    if (closePreviewBtn) {
        closePreviewBtn.onclick = closePreview;
    }
    
    // Close preview when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === previewModal) {
            closePreview();
        }
    });

    // Time limit check (10 seconds)
    videoPlayer.addEventListener('timeupdate', function() {
        if (this.currentTime >= 10) {
            this.pause();
            // Only show message if we actually hit the limit
            if (!this.ended) {
                 previewMessage.classList.remove('hidden');
            }
        }
    });
    
    // Hide message on seek or play
    videoPlayer.addEventListener('play', function() {
        if (this.currentTime < 10) {
            previewMessage.classList.add('hidden');
        }
    });

    window.previewVideo = function(id, url) {
        // Reset state
        previewMessage.classList.add('hidden');
        videoPlayer.currentTime = 0;
        
        // Determine URL
        let finalUrl = url;
        if (!url.startsWith('http') && !url.startsWith('rtsp') && !url.startsWith('rtmp')) {
            // It's a local file
            finalUrl = '/uploads/' + url;
        }

        // Handle Formats
        if (finalUrl.endsWith('.flv')) {
            if (typeof flvjs === 'undefined') {
                alert('FLV 播放器组件正在加载中，请稍后重试...');
                return;
            }
            if (flvjs.isSupported()) {
                // Show modal only if supported
                previewModal.classList.add('show');
                flvPlayer = flvjs.createPlayer({
                    type: 'flv',
                    url: finalUrl
                });
                flvPlayer.attachMediaElement(videoPlayer);
                flvPlayer.load();
                flvPlayer.play();
            } else {
                alert('您的浏览器不支持 FLV 播放');
            }
        } else if (finalUrl.endsWith('.m3u8')) {
            if (typeof Hls === 'undefined') {
                alert('HLS 播放器组件正在加载中，请稍后重试...');
                return;
            }
            if (Hls.isSupported()) {
                previewModal.classList.add('show');
                hls = new Hls();
                hls.loadSource(finalUrl);
                hls.attachMedia(videoPlayer);
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    videoPlayer.play();
                });
            } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
                previewModal.classList.add('show');
                videoPlayer.src = finalUrl;
                videoPlayer.play();
            }
        } else if (url.startsWith('rtsp') || url.startsWith('rtmp')) {
             // RTSP/RTMP cannot be played directly in browser
             alert('浏览器不支持直接预览 RTSP/RTMP 流，请使用专用客户端查看。');
             // closePreview(); // No need to close if not opened
             return;
        } else {
            // MP4, WebM, etc.
            previewModal.classList.add('show');
            videoPlayer.src = finalUrl;
            videoPlayer.play().catch(e => console.log('Autoplay blocked:', e));
        }
    };

    window.deleteVideo = function(id) {
        if(confirm('确定要删除该视频源吗？')) {
            const token = localStorage.getItem('token');
            fetch(`/api/video-source/delete/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': 'Bearer ' + token
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.code === 200) {
                    alert('删除成功');
                    fetchVideoList(); // Refresh list
                } else {
                    alert('删除失败: ' + data.msg);
                }
            })
            .catch(err => {
                console.error(err);
                alert('删除出错');
            });
        }
    };
});