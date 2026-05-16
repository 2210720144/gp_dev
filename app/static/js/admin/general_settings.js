document.addEventListener('DOMContentLoaded', function() {
    loadConfigs();

    document.getElementById('save-btn').addEventListener('click', saveConfigs);
});

function loadConfigs() {
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.code === 200) {
                const configs = data.data;
                
                // Update Violation Judgment Time (Backend key: '违停判定时间')
                if (configs['违停判定时间']) {
                    const config = configs['违停判定时间'];
                    document.getElementById('violation_judgment_time').value = config.config_value;
                    document.getElementById('unit_violation_judgment_time').textContent = config.unit;
                    document.getElementById('desc_violation_judgment_time').setAttribute('data-tooltip', config.description);
                }

                // Update Alert Refresh Interval (Backend key: '告警刷新时间')
                if (configs['告警刷新时间']) {
                    const config = configs['告警刷新时间'];
                    document.getElementById('alert_refresh_interval').value = config.config_value;
                    document.getElementById('unit_alert_refresh_interval').textContent = config.unit;
                    document.getElementById('desc_alert_refresh_interval').setAttribute('data-tooltip', config.description);
                }

                // Update YOLO Confidence Threshold (Backend key: 'YOLO置信度阈值')
                if (configs['YOLO置信度阈值']) {
                    const config = configs['YOLO置信度阈值'];
                    document.getElementById('yolo_confidence_threshold').value = config.config_value;
                    document.getElementById('unit_yolo_confidence_threshold').textContent = config.unit;
                    document.getElementById('desc_yolo_confidence_threshold').setAttribute('data-tooltip', config.description);
                }
            } else {
                alert('加载配置失败: ' + data.msg);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('加载配置出错');
        });
}

function saveConfigs() {
    const violationTime = document.getElementById('violation_judgment_time').value;
    const alertInterval = document.getElementById('alert_refresh_interval').value;
    const yoloConfidenceThreshold = document.getElementById('yolo_confidence_threshold').value;
    const yoloConfidenceValue = parseFloat(yoloConfidenceThreshold);

    if (Number.isNaN(yoloConfidenceValue) || yoloConfidenceValue < 0 || yoloConfidenceValue > 1) {
        alert('YOLO置信度阈值必须在0到1之间');
        return;
    }

    const data = {
        '违停判定时间': parseFloat(violationTime),
        '告警刷新时间': parseFloat(alertInterval),
        'YOLO置信度阈值': yoloConfidenceValue
    };

    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 200) {
            alert('设置保存成功');
        } else {
            alert('保存失败: ' + data.msg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('保存出错');
    });
}
