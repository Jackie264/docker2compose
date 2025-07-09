/**
 * D2C Web UI JavaScript 应用
 * 处理前端交互逻辑和API调用
 */

class D2CWebUI {
    constructor() {
        this.selectedContainers = new Set();
        this.containerGroups = [];
        this.currentYaml = '';
        
        this.init();
    }

    /**
     * 初始化应用
     */
    init() {
        this.bindEvents();
        this.bindNewButtonEvents();
        this.loadContainers();
        this.loadFileList();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 刷新按钮
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadContainers();
        });

        // 生成Compose按钮（编辑器区域）
        const generateComposeBtn = document.getElementById('generateComposeBtn');
        if (generateComposeBtn) {
            generateComposeBtn.addEventListener('click', () => {
                this.generateCompose();
            });
        }

        // 保存按钮
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveCompose();
            });
        }

        // 复制按钮
        const copyBtn = document.getElementById('copyBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                this.copyToClipboard();
            });
        }

        // 通知关闭按钮
        document.querySelector('.notification-close').addEventListener('click', () => {
            this.hideNotification();
        });

        // YAML编辑器变化监听
        document.getElementById('yamlEditor').addEventListener('input', () => {
            this.updateSaveButtonState();
        });
        
        // 全部展开/收缩按钮
        document.getElementById('expandAllBtn').addEventListener('click', () => this.expandAllGroups());
        document.getElementById('collapseAllBtn').addEventListener('click', () => this.collapseAllGroups());
        
        // 文件列表相关
        document.getElementById('refreshFilesBtn').addEventListener('click', () => this.loadFileList());
    }

    /**
     * 绑定新增按钮事件
     */
    bindNewButtonEvents() {
        // 生成全量Compose按钮
        const generateAllBtn = document.getElementById('generateAllBtn');
        if (generateAllBtn) {
            generateAllBtn.addEventListener('click', () => {
                this.generateAllCompose();
            });
        }

        // 设置按钮
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.openSettings();
            });
        }

        // 设置弹窗保存按钮
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => {
                this.saveSettings();
            });
        }
        
        // 任务计划控制按钮
        const startSchedulerBtn = document.getElementById('startSchedulerBtn');
        if (startSchedulerBtn) {
            startSchedulerBtn.addEventListener('click', () => {
                this.startScheduler();
            });
        }
        
        const stopSchedulerBtn = document.getElementById('stopSchedulerBtn');
        if (stopSchedulerBtn) {
            stopSchedulerBtn.addEventListener('click', () => {
                this.stopScheduler();
            });
        }
        
        const runOnceBtn = document.getElementById('runOnceBtn');
        if (runOnceBtn) {
            runOnceBtn.addEventListener('click', () => {
                this.runOnce();
            });
        }
        
        // 任务状态按钮
        const schedulerStatusBtn = document.getElementById('schedulerStatusBtn');
        if (schedulerStatusBtn) {
            schedulerStatusBtn.addEventListener('click', () => {
                this.openSchedulerStatus();
            });
        }
        
        // 任务状态弹窗中的快速操作按钮
        const quickStartBtn = document.getElementById('quickStartBtn');
        if (quickStartBtn) {
            quickStartBtn.addEventListener('click', () => {
                this.startScheduler();
                this.refreshSchedulerStatus();
            });
        }
        
        const quickStopBtn = document.getElementById('quickStopBtn');
        if (quickStopBtn) {
            quickStopBtn.addEventListener('click', () => {
                this.stopScheduler();
                this.refreshSchedulerStatus();
            });
        }
        
        const quickRunOnceBtn = document.getElementById('quickRunOnceBtn');
        if (quickRunOnceBtn) {
            quickRunOnceBtn.addEventListener('click', () => {
                this.runOnce();
                this.refreshSchedulerStatus();
            });
        }
        
        // 更新CRON表达式按钮
        const updateCronBtn = document.getElementById('updateCronBtn');
        if (updateCronBtn) {
            updateCronBtn.addEventListener('click', () => {
                this.updateCronExpression();
            });
        }
        
        // 日志操作按钮
        const refreshLogsBtn = document.getElementById('refreshLogsBtn');
        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', () => {
                this.refreshLogs();
            });
        }
        
        const clearLogsBtn = document.getElementById('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                this.clearLogs();
            });
        }
        
        // 自动刷新切换按钮
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('click', () => {
                this.toggleAutoRefresh();
            });
        }
        
        // 关于我按钮
        const aboutMeBtn = document.getElementById('aboutMeBtn');
        if (aboutMeBtn) {
            aboutMeBtn.addEventListener('click', () => {
                this.openAboutMe();
            });
        }
    }

    /**
     * 加载容器列表
     */
    async loadContainers() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/containers');
            const result = await response.json();

            if (result.success) {
                this.containerGroups = result.data;
                this.renderContainerGroups();
                this.showNotification('容器列表加载成功', 'success');
            } else {
                throw new Error(result.error || '加载失败');
            }
        } catch (error) {
            console.error('加载容器失败:', error);
            this.showNotification(`加载容器失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 渲染容器分组
     */
    renderContainerGroups() {
        const container = document.getElementById('containerGroups');
        
        if (this.containerGroups.length === 0) {
            container.innerHTML = `
                <div class="loading">
                    <i class="fas fa-exclamation-circle"></i>
                    <div>未找到运行中的容器</div>
                </div>
            `;
            return;
        }

        // 对每个分组内的容器按名称排序（英文首字母排序）
        const sortedGroups = this.containerGroups.map(group => ({
            ...group,
            containers: [...group.containers].sort((a, b) => {
                const nameA = a.name.toLowerCase();
                const nameB = b.name.toLowerCase();
                return nameA < nameB ? -1 : nameA > nameB ? 1 : 0;
            })
        }));

        container.innerHTML = sortedGroups.map((group, index) => {
            // 计算分组状态
            const runningCount = group.containers.filter(c => c.status === 'running').length;
            const stoppedCount = group.containers.length - runningCount;
            const groupStatus = runningCount > 0 ? 'running' : 'stopped';
            const statusIcon = groupStatus === 'running' ? 
                '<span class="group-status-icon running">R</span>' : 
                '<span class="group-status-icon stopped">S</span>';
            
            return `
            <div class="container-group">
                <div class="group-header ${index === 0 ? 'expanded' : ''}" onclick="app.toggleGroup('${group.id}')">
                    <div class="group-title">
                        ${statusIcon}
                        <span class="group-badge">${group.count}</span>
                        <i class="fas ${group.type === 'single' ? 'fa-cube' : 'fa-cubes'}"></i>
                        <span>${group.name}</span>
                    </div>
                    <div class="group-actions">
                        <i class="fas fa-chevron-right group-toggle"></i>
                    </div>
                </div>
                <div class="group-containers" style="display: ${index === 0 ? 'block' : 'none'}">
                    ${group.containers.map((container, containerIndex) => {
                        const statusClass = container.status === 'running' ? 'running' : 'stopped';
                        const statusIcon = container.status === 'running' ? 
                            '<span class="container-status-badge running">R</span>' : 
                            '<span class="container-status-badge stopped">S</span>';
                        
                        return `
                        <div class="container-item ${index === 0 && containerIndex === 0 ? 'focused' : ''}" data-id="${container.id}" onclick="app.toggleContainer('${container.id}')">
                            <div class="container-checkbox ${this.selectedContainers.has(container.id) ? 'checked' : ''}"></div>
                            <div class="container-info">
                                <div class="container-name-row">
                                    <i class="fas fa-box container-icon" style="color: #3498db;"></i>
                                    <span class="container-name" title="${container.name}">${container.name.length > 14 ? container.name.substring(0, 14) + '...' : container.name}</span>
                                    <span class="container-status ${container.status.toLowerCase()}" title="${container.status}">${container.status}</span>
                                </div>
                                <div class="container-details-row">
                                    <span class="container-image" title="${container.image}"><i class="fas fa-layer-group" style="color: #e74c3c;"></i> ${container.image}</span>
                                    <span class="container-network" title="${container.network_mode}"><i class="fas fa-network-wired" style="color: #27ae60;"></i> ${container.network_mode}</span>
                                </div>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>
            </div>
            `;
        }).join('');

        this.updateSelectionInfo();
    }

    /**
     * 切换分组展开/折叠状态
     */
    toggleGroup(groupId) {
        const groupHeader = document.querySelector(`[onclick="app.toggleGroup('${groupId}')"]`);
        const groupContainers = groupHeader.nextElementSibling;
        const toggle = groupHeader.querySelector('.group-toggle');
        
        if (groupContainers.style.display === 'none') {
            groupContainers.style.display = 'block';
            groupHeader.classList.add('expanded');
            toggle.style.transform = 'rotate(90deg)';
        } else {
            groupContainers.style.display = 'none';
            groupHeader.classList.remove('expanded');
            toggle.style.transform = 'rotate(0deg)';
        }
    }

    /**
     * 切换容器选择状态
     */
    toggleContainer(containerId) {
        if (this.selectedContainers.has(containerId)) {
            this.selectedContainers.delete(containerId);
        } else {
            this.selectedContainers.add(containerId);
        }

        // 更新UI
        this.updateContainerSelection();
        this.updateSelectionInfo();
        this.updateGenerateButtonState();
    }

    /**
     * 加载容器对应的compose文件
     */
    async loadContainerComposeFile(containerId) {
        try {
            const response = await fetch(`/api/compose-file/${containerId}`);
            const result = await response.json();
            
            if (result.success) {
                // 加载对应的compose文件内容
                this.showYamlEditor(result.data.content);
                document.getElementById('filenameInput').value = result.data.filename;
                this.showNotification('已加载容器对应的compose文件', 'success');
            } else {
                // 如果没有找到对应文件，继续使用生成的compose
                console.log('未找到对应的compose文件，使用生成的compose');
            }
        } catch (error) {
            console.log('加载compose文件失败，使用生成的compose:', error);
        }
    }

    /**
     * 更新容器选择状态UI
     */
    updateContainerSelection() {
        document.querySelectorAll('.container-item').forEach(item => {
            const containerId = item.getAttribute('data-id');
            const checkbox = item.querySelector('.container-checkbox');
            
            if (containerId && this.selectedContainers.has(containerId)) {
                item.classList.add('selected');
                checkbox.classList.add('checked');
            } else {
                item.classList.remove('selected');
                checkbox.classList.remove('checked');
            }
        });
    }

    /**
     * 更新选择信息
     */
    updateSelectionInfo() {
        document.getElementById('selectedCount').textContent = this.selectedContainers.size;
    }

    /**
     * 获取选中的容器ID列表
     * @returns {Array} 选中容器的ID数组
     */
    getSelectedContainers() {
        return Array.from(this.selectedContainers);
    }

    /**
     * 更新生成按钮状态
     */
    updateGenerateButtonState() {
        const generateBtn = document.getElementById('generateComposeBtn');
        if (generateBtn) {
            generateBtn.disabled = this.selectedContainers.size === 0;
        }
    }

    /**
     * 更新保存按钮状态
     */
    updateSaveButtonState() {
        const saveBtn = document.getElementById('saveBtn');
        const yamlEditor = document.getElementById('yamlEditor');
        saveBtn.disabled = !yamlEditor.value.trim();
    }

    /**
     * 生成Compose文件
     */
    async generateCompose() {
        if (this.selectedContainers.size === 0) {
            this.showNotification('请先选择容器', 'error');
            return;
        }

        try {
            this.showLoading(true);
            const response = await fetch('/api/compose', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    container_ids: Array.from(this.selectedContainers)
                })
            });

            const result = await response.json();

            if (result.success) {
                this.currentYaml = result.data.yaml;
                this.showYamlEditor(this.currentYaml);
                this.showNotification('Compose文件生成成功', 'success');
            } else {
                throw new Error(result.error || '生成失败');
            }
        } catch (error) {
            console.error('生成Compose失败:', error);
            this.showNotification(`生成失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 显示YAML编辑器
     */
    showYamlEditor(content) {
        const placeholder = document.getElementById('editorPlaceholder');
        const editor = document.getElementById('yamlEditor');
        
        placeholder.style.display = 'none';
        editor.style.display = 'block';
        editor.classList.add('active');
        editor.value = content;
        
        this.updateSaveButtonState();
    }

    /**
     * 保存Compose文件
     */
    async saveCompose() {
        const filename = document.getElementById('filenameInput').value.trim();
        const content = document.getElementById('yamlEditor').value.trim();

        if (!filename) {
            this.showNotification('请输入文件名', 'error');
            return;
        }

        if (!content) {
            this.showNotification('内容不能为空', 'error');
            return;
        }

        try {
            this.showLoading(true);
            const response = await fetch('/api/save-compose', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: filename,
                    content: content
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(`文件保存成功: ${result.path}`, 'success');
                this.loadFileList();
            } else {
                throw new Error(result.error || '保存失败');
            }
        } catch (error) {
            console.error('保存文件失败:', error);
            this.showNotification(`保存失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 复制到剪贴板
     */
    async copyToClipboard() {
        const content = document.getElementById('yamlEditor').value;
        
        if (!content.trim()) {
            this.showNotification('没有内容可复制', 'error');
            return;
        }

        try {
            await navigator.clipboard.writeText(content);
            this.showNotification('已复制到剪贴板', 'success');
        } catch (error) {
            console.error('复制失败:', error);
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = content;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showNotification('已复制到剪贴板', 'success');
        }
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        const messageElement = notification.querySelector('.notification-message');
        
        // 清除之前的类型类
        notification.classList.remove('success', 'error', 'info');
        notification.classList.add(type);
        
        messageElement.textContent = message;
        notification.classList.add('show');

        // 自动隐藏
        setTimeout(() => {
            this.hideNotification();
        }, type === 'error' ? 5000 : 3000);
    }

    /**
     * 隐藏通知
     */
    hideNotification() {
        const notification = document.getElementById('notification');
        notification.classList.remove('show');
    }

    /**
     * 显示高优先级错误提示（用于任务启动失败等重要错误）
     */
    showHighPriorityError(message) {
        // 创建高层级的错误弹框
        const errorModal = document.createElement('div');
        errorModal.className = 'modal fade error-modal';
        errorModal.setAttribute('tabindex', '-1');
        errorModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>任务执行错误
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger mb-0">
                            <i class="fas fa-times-circle me-2"></i>
                            ${message}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(errorModal);
        
        const modal = new bootstrap.Modal(errorModal);
        modal.show();
        
        // 弹框关闭后移除DOM元素
        errorModal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(errorModal);
        });
    }

    /**
     * 显示/隐藏加载遮罩
     */
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }

    /**
     * 全部展开分组
     */
    expandAllGroups() {
        document.querySelectorAll('.group-header').forEach(header => {
            const groupContainers = header.nextElementSibling;
            const toggle = header.querySelector('.group-toggle');
            
            groupContainers.style.display = 'block';
            header.classList.add('expanded');
            toggle.style.transform = 'rotate(90deg)';
        });
    }

    /**
     * 全部收缩分组
     */
    collapseAllGroups() {
        document.querySelectorAll('.group-header').forEach(header => {
            const groupContainers = header.nextElementSibling;
            const toggle = header.querySelector('.group-toggle');
            
            groupContainers.style.display = 'none';
            header.classList.remove('expanded');
            toggle.style.transform = 'rotate(0deg)';
        });
    }

    /**
     * 加载文件列表
     */
    async loadFileList() {
        try {
            const response = await fetch('/api/files');
            const result = await response.json();
            
            if (result.success) {
                this.renderFileList(result.data);
            } else {
                throw new Error(result.error || '加载文件列表失败');
            }
        } catch (error) {
            console.error('加载文件列表失败:', error);
            document.getElementById('fileList').innerHTML = `
                <div class="loading">
                    <i class="fas fa-exclamation-triangle"></i>
                    加载失败
                </div>
            `;
        }
    }

    /**
     * 渲染文件列表
     */
    renderFileList(data) {
        const fileList = document.getElementById('fileList');
        if (!data || (!data.root.length && !Object.keys(data.folders).length)) {
            fileList.innerHTML = '<div class="text-center text-muted p-3">暂无文件</div>';
            return;
        }

        let html = '';
        
        // 渲染根目录文件
        if (data.root.length > 0) {
            html += '<div class="folder-section">';
            html += '<div class="folder-header" onclick="app.toggleFolder(this)">';
            html += '<i class="fas fa-folder folder-icon"></i>';
            html += '<span class="folder-name">根目录</span>';
            html += '<i class="fas fa-chevron-down toggle-icon"></i>';
            html += '</div>';
            html += '<div class="folder-content collapsed" style="max-height: 0;">';
            
            data.root.forEach(file => {
                const modifiedDate = new Date(file.modified * 1000).toLocaleString('zh-CN');
                const fileSize = this.formatFileSize(file.size);
                
                html += `
                    <div class="file-item" onclick="app.loadFile('${file.path.replace(/'/g, "\\'").replace(/"/g, '\\"')}', this)">
                        <i class="fas fa-file-code file-icon"></i>
                        <div class="file-info">
                            <div class="file-name">${file.name}</div>
                            <div class="file-date">${modifiedDate} • ${fileSize}</div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger delete-btn" onclick="event.stopPropagation(); app.deleteFile('${file.path.replace(/'/g, "\\'").replace(/"/g, '\\"')}', event)">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
            });
            
            html += '</div></div>';
        }
        
        // 渲染文件夹（按修改时间排序）
        const sortedFolders = Object.values(data.folders).sort((a, b) => b.modified - a.modified);
        
        sortedFolders.forEach(folder => {
            html += '<div class="folder-section">';
            html += '<div class="folder-header" onclick="app.toggleFolder(this)">';
            html += '<i class="fas fa-folder folder-icon"></i>';
            html += `<span class="folder-name">${folder.name}</span>`;
            html += '<div class="folder-actions">';
            html += `<button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); app.deleteFile('${folder.path.replace(/'/g, "\\'").replace(/"/g, '\\"')}', event)" title="删除文件夹">`;
            html += '<i class="fas fa-trash"></i>';
            html += '</button>';
            html += '<i class="fas fa-chevron-down toggle-icon"></i>';
            html += '</div>';
            html += '</div>';
            html += '<div class="folder-content collapsed" style="max-height: 0;">';
            
            folder.files.forEach(file => {
                const modifiedDate = new Date(file.modified * 1000).toLocaleString('zh-CN');
                const fileSize = this.formatFileSize(file.size);
                
                html += `
                    <div class="file-item" onclick="app.loadFile('${file.path.replace(/'/g, "\\'").replace(/"/g, '\\"')}', this)">
                        <i class="fas fa-file-code file-icon"></i>
                        <div class="file-info">
                            <div class="file-name">${file.name}</div>
                            <div class="file-date">${modifiedDate} • ${fileSize}</div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger delete-btn" onclick="event.stopPropagation(); app.deleteFile('${file.path.replace(/'/g, "\\'").replace(/"/g, '\\"')}', event)">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
            });
            
            html += '</div></div>';
        });

        fileList.innerHTML = html;
    }

    /**
     * 切换文件夹展开/收缩状态
     */
    toggleFolder(headerElement) {
        const content = headerElement.nextElementSibling;
        const toggleIcon = headerElement.querySelector('.toggle-icon');
        
        if (content.classList.contains('collapsed')) {
            content.classList.remove('collapsed');
            content.style.maxHeight = content.scrollHeight + 'px';
            toggleIcon.style.transform = 'rotate(180deg)';
        } else {
            content.classList.add('collapsed');
            content.style.maxHeight = '0';
            toggleIcon.style.transform = 'rotate(0deg)';
        }
    }

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 生成全量Compose文件
     */
    async generateAllCompose() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/generate-all-compose', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`全量Compose文件生成成功: ${result.filename}`, 'success');
                this.loadFileList(); // 重新加载文件列表
                // 刷新页面以更新容器列表
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error(result.error || '生成失败');
            }
        } catch (error) {
            console.error('生成全量Compose失败:', error);
            this.showNotification(`生成失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 打开设置弹窗
     */
    async openSettings() {
        try {
            // 加载当前设置
            const response = await fetch('/api/settings');
            const result = await response.json();
            
            if (result.success) {
                const settings = result.settings;
                document.getElementById('nasInput').value = settings.NAS || 'debian';
                document.getElementById('networkInput').value = settings.NETWORK || 'true';
                document.getElementById('tzInput').value = settings.TZ || 'Asia/Shanghai';
                
                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
                modal.show();
            } else {
                throw new Error(result.error || '加载设置失败');
            }
        } catch (error) {
            console.error('加载设置失败:', error);
            this.showNotification(`加载设置失败: ${error.message}`, 'error');
        }
    }

    /**
     * 保存设置
     */
    async saveSettings() {
        try {
            const settings = {
                NAS: document.getElementById('nasInput').value,
                NETWORK: document.getElementById('networkInput').value,
                TZ: document.getElementById('tzInput').value
            };
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ settings })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('设置保存成功', 'success');
                // 关闭模态框
                const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
                modal.hide();
            } else {
                throw new Error(result.error || '保存失败');
            }
        } catch (error) {
            console.error('保存设置失败:', error);
            this.showNotification(`保存失败: ${error.message}`, 'error');
        }
    }

    /**
     * 生成选中容器的Compose
     */
    async generateCompose() {
        const selectedContainers = this.getSelectedContainers();
        if (selectedContainers.length === 0) {
            this.showNotification('请先选择要生成的容器', 'warning');
            return;
        }
        
        try {
            this.showLoading(true);
            const response = await fetch('/api/compose', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ container_ids: selectedContainers })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showYamlEditor(result.data.yaml);
                this.showNotification('Compose文件生成成功', 'success');
            } else {
                throw new Error(result.error || '生成失败');
            }
        } catch (error) {
            console.error('生成Compose失败:', error);
            this.showNotification(`生成失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 删除文件或文件夹
     */
    async deleteFile(filePath, event) {
        console.log('deleteFile called with:', filePath);
        event.stopPropagation();
        
        if (!confirm('确定要删除这个文件吗？此操作不可恢复。')) {
            console.log('用户取消删除操作');
            return;
        }
        
        console.log('开始删除文件:', filePath);
        
        try {
            this.showLoading(true);
            console.log('发送删除请求到:', '/api/delete-file');
            console.log('请求数据:', { file_path: filePath });
            
            const response = await fetch('/api/delete-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ file_path: filePath })
            });
            
            console.log('收到响应:', response.status, response.statusText);
            const result = await response.json();
            console.log('响应数据:', result);
            
            if (result.success) {
                console.log('删除成功，重新加载文件列表');
                this.showNotification('文件删除成功', 'success');
                this.loadFileList(); // 重新加载文件列表
            } else {
                throw new Error(result.error || '删除失败');
            }
        } catch (error) {
            console.error('删除文件失败:', error);
            this.showNotification(`删除失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 加载文件内容
     */
    async loadFile(filePath, targetElement = null) {
        try {
            // 先更新UI状态，避免闪烁
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            if (targetElement) {
                targetElement.classList.add('selected');
            }
            
            // 显示轻量级加载指示器，而不是全屏遮罩
            const editor = document.getElementById('yamlEditor');
            const originalContent = editor.value;
            editor.style.transition = 'opacity 0.2s ease';
            editor.style.opacity = '0.7';
            editor.disabled = true;
            
            // 添加加载状态指示
            const filenameInput = document.getElementById('filenameInput');
            const originalFilename = filenameInput.value;
            filenameInput.value = '加载中...';
            filenameInput.disabled = true;
            
            const response = await fetch('/api/file-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ file_path: filePath })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 平滑更新内容
                setTimeout(() => {
                    this.showYamlEditor(result.data.content);
                    document.getElementById('filenameInput').value = result.data.filename;
                    this.showNotification('文件加载成功', 'success');
                }, 100);
            } else {
                throw new Error(result.error || '加载文件失败');
            }
        } catch (error) {
            console.error('加载文件失败:', error);
            this.showNotification(`加载文件失败: ${error.message}`, 'error');
            
            // 恢复选择状态
            if (targetElement) {
                targetElement.classList.remove('selected');
            }
        } finally {
            // 恢复编辑器状态
            const editor = document.getElementById('yamlEditor');
            const filenameInput = document.getElementById('filenameInput');
            
            setTimeout(() => {
                editor.style.opacity = '1';
                editor.disabled = false;
                filenameInput.disabled = false;
            }, 150);
        }
    }
    
    /**
     * 启动定时任务
     */
    async startScheduler() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/scheduler/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification('定时任务启动成功', 'success');
            } else {
                // 处理不同类型的错误
                if (response.status === 409) {
                    // 调度器已运行的情况，显示简单提示
                    let message = '调度器已在运行中';
                    if (result.scheduler_type === 'python') {
                        message = 'Python精确调度器已在运行中，请先停止当前调度器再启动新的。';
                    } else if (result.scheduler_type === 'system_cron') {
                        message = '系统CRON调度器已在运行中，请先停止当前调度器再启动新的。';
                    }
                    this.showNotification(message, 'warning');
                    return; // 直接返回，不抛出异常
                } else {
                    throw new Error(result.error || '启动失败');
                }
            }
        } catch (error) {
            console.error('启动定时任务失败:', error);
            // 为任务启动失败显示高层级错误提示
            this.showHighPriorityError(`启动失败: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 停止定时任务
     */
    async stopScheduler() {
        try {
            this.showLoading(true);
            
            // 先检查任务状态
            const statusResponse = await fetch('/api/scheduler/status');
            const statusResult = await statusResponse.json();
            
            if (statusResult.success && !statusResult.status.running) {
                this.showNotification('CRON任务未启动，无需停止', 'info');
                return;
            }
            
            const response = await fetch('/api/scheduler/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('定时任务停止成功', 'success');
            } else {
                throw new Error(result.error || '停止失败');
            }
        } catch (error) {
            console.error('停止定时任务失败:', error);
            this.showNotification(`停止失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 立即执行一次任务
     */
    async runOnce() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/scheduler/run-once', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('任务执行成功', 'success');
                // 刷新文件列表以显示新生成的文件
                this.loadFileList();
            } else {
                throw new Error(result.error || '执行失败');
            }
        } catch (error) {
            console.error('执行任务失败:', error);
            // 为任务启动失败显示高层级错误提示
            this.showHighPriorityError(`执行失败: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }
    
    /**
     * 打开任务状态弹窗
     */
    openSchedulerStatus() {
        // 初始化自动刷新状态
        this.autoRefreshInterval = null;
        this.isAutoRefreshActive = false;
        
        // 显示弹窗
        const modal = new bootstrap.Modal(document.getElementById('schedulerStatusModal'));
        modal.show();
        
        // 加载初始状态
        this.refreshSchedulerStatus();
        this.refreshLogs();
    }

    /**
     * 打开关于我模态框
     */
    openAboutMe() {
        const modal = new bootstrap.Modal(document.getElementById('aboutMeModal'));
        modal.show();
    }
    
    /**
     * 刷新任务状态信息
     */
    async refreshSchedulerStatus() {
        try {
            // 获取当前设置
            const settingsResponse = await fetch('/api/settings');
            const settingsResult = await settingsResponse.json();
            
            if (settingsResult.success) {
                const settings = settingsResult.settings;
                const currentCron = settings.CRON || '*/5 * * * *';
                
                document.getElementById('schedulerCron').textContent = currentCron;
                
                // 更新CRON输入框的placeholder
                const cronInput = document.getElementById('schedulerCronInput');
                if (cronInput) {
                    cronInput.placeholder = `当前: ${currentCron}`;
                }
                
                // 计算下次执行时间（如果是cron表达式）
                if (settings.CRON && settings.CRON !== 'once') {
                    this.calculateNextCronTime(settings.CRON);
                } else {
                    document.getElementById('schedulerNextRun').textContent = '仅执行一次';
                }
            }
            
            // 获取任务状态
            const statusResponse = await fetch('/api/scheduler/status');
            const statusResult = await statusResponse.json();
            
            if (statusResult.success) {
                const status = statusResult.status;
                const statusElement = document.getElementById('schedulerCurrentStatus');
                
                if (status.running) {
                    let statusText = '运行中';
                    let schedulerInfo = '';
                    
                    // 根据调度器类型显示详细信息
                    if (status.scheduler_type === 'python') {
                        schedulerInfo = ' (Python精确调度器)';
                    } else if (status.scheduler_type === 'system_cron') {
                        schedulerInfo = ' (系统CRON调度器)';
                    } else if (status.scheduler_type === 'both') {
                        schedulerInfo = ' (多调度器运行)';
                    }
                    
                    statusElement.innerHTML = `<span class="status-indicator running">${statusText}${schedulerInfo}</span>`;
                    statusElement.className = 'status-value running';
                } else {
                    statusElement.innerHTML = '<span class="status-indicator stopped">已停止</span>';
                    statusElement.className = 'status-value stopped';
                }
                
                // 更新最后执行时间
                if (status.last_run) {
                    document.getElementById('schedulerLastRun').textContent = new Date(status.last_run).toLocaleString();
                } else {
                    document.getElementById('schedulerLastRun').textContent = '从未执行';
                }
            }
        } catch (error) {
            console.error('刷新任务状态失败:', error);
            document.getElementById('schedulerCurrentStatus').innerHTML = '<span class="status-indicator stopped">获取状态失败</span>';
        }
    }
    
    /**
     * 计算下次cron执行时间
     */
    calculateNextCronTime(cronExpression) {
        const nextRunElement = document.getElementById('schedulerNextRun');
        
        try {
            const parts = cronExpression.split(' ');
            if (parts.length < 5) {
                nextRunElement.textContent = '无效的CRON表达式';
                return;
            }
            
            const [minute, hour, day, month, weekday] = parts;
            let description = '';
            
            // 解析分钟
            if (minute.includes(',')) {
                const minutes = minute.split(',');
                description += `每小时的第${minutes.join('、')}分钟`;
            } else if (minute.startsWith('*/')) {
                const interval = parseInt(minute.substring(2));
                description += `每${interval}分钟`;
            } else if (minute === '*') {
                description += '每分钟';
            } else {
                description += `第${minute}分钟`;
            }
            
            // 解析小时
            if (hour !== '*') {
                if (hour.includes(',')) {
                    const hours = hour.split(',');
                    description = `每天${hours.join('、')}点的` + description;
                } else if (hour.startsWith('*/')) {
                    const interval = parseInt(hour.substring(2));
                    description = `每${interval}小时的` + description;
                } else {
                    description = `每天${hour}点` + description;
                }
            } else if (minute !== '*') {
                description = '每小时' + description;
            }
            
            // 解析日期
            if (day !== '*') {
                if (day.includes(',')) {
                    const days = day.split(',');
                    description = `每月${days.join('、')}号` + description;
                } else {
                    description = `每月${day}号` + description;
                }
            }
            
            // 解析月份
            if (month !== '*') {
                if (month.includes(',')) {
                    const months = month.split(',');
                    description = `每年${months.join('、')}月` + description;
                } else {
                    description = `每年${month}月` + description;
                }
            }
            
            // 解析星期
            if (weekday !== '*') {
                const weekNames = ['日', '一', '二', '三', '四', '五', '六'];
                if (weekday.includes(',')) {
                    const weeks = weekday.split(',').map(w => {
                        const num = parseInt(w);
                        return weekNames[num] || w;
                    });
                    description = `每周${weeks.join('、')}` + description;
                } else {
                    const num = parseInt(weekday);
                    const weekName = weekNames[num] || weekday;
                    description = `每周${weekName}` + description;
                }
            }
            
            // 特殊情况处理
            if (minute.includes(',') && hour === '*' && day === '*' && month === '*' && weekday === '*') {
                const minutes = minute.split(',');
                description = `每小时的第${minutes.join('、')}分钟执行`;
            }
            
            nextRunElement.textContent = description + '执行';
            
        } catch (error) {
            console.error('解析CRON表达式失败:', error);
            nextRunElement.textContent = '无法解析执行时间';
        }
    }
    
    /**
     * 刷新日志
     */
    async refreshLogs() {
        try {
            const response = await fetch('/api/scheduler/logs');
            const result = await response.json();
            
            const logContainer = document.getElementById('logContainer');
            
            if (result.success && result.logs && result.logs.length > 0) {
                const logContent = result.logs.map(log => {
                    const timestamp = new Date(log.timestamp).toLocaleString();
                    const level = log.level || 'info';
                    return `<div class="log-line ${level}"><span class="log-timestamp">${timestamp}</span>${log.message}</div>`;
                }).join('');
                
                logContainer.innerHTML = `<div class="log-content">${logContent}</div>`;
                
                // 滚动到底部
                logContainer.scrollTop = logContainer.scrollHeight;
            } else {
                logContainer.innerHTML = `
                    <div class="log-placeholder">
                        <i class="fas fa-file-alt"></i>
                        <p>暂无日志信息</p>
                        <small class="text-muted">执行任务后将显示相关日志</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error('刷新日志失败:', error);
            const logContainer = document.getElementById('logContainer');
            logContainer.innerHTML = `
                <div class="log-placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>加载日志失败</p>
                    <small class="text-muted">${error.message}</small>
                </div>
            `;
        }
    }
    
    /**
     * 清空日志
     */
    async clearLogs() {
        if (!confirm('确定要清空所有日志吗？')) {
            return;
        }
        
        try {
            const response = await fetch('/api/scheduler/clear-logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('日志清空成功', 'success');
                this.refreshLogs();
            } else {
                throw new Error(result.error || '清空失败');
            }
        } catch (error) {
            console.error('清空日志失败:', error);
            this.showNotification(`清空失败: ${error.message}`, 'error');
        }
    }
    
    /**
     * 切换自动刷新
     */
    toggleAutoRefresh() {
        const button = document.getElementById('autoRefreshToggle');
        
        if (this.isAutoRefreshActive) {
            // 停止自动刷新
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
            this.isAutoRefreshActive = false;
            button.innerHTML = '<i class="fas fa-sync-alt"></i> 开启自动刷新';
            button.classList.remove('auto-refresh-active');
        } else {
            // 开启自动刷新
            this.isAutoRefreshActive = true;
            button.innerHTML = '<i class="fas fa-sync-alt"></i> 关闭自动刷新';
            button.classList.add('auto-refresh-active');
            
            // 每5秒刷新一次
            this.autoRefreshInterval = setInterval(() => {
                this.refreshSchedulerStatus();
                this.refreshLogs();
            }, 5000);
        }
    }
    
    /**
      * 更新CRON表达式
      */
     async updateCronExpression() {
         const cronInput = document.getElementById('schedulerCronInput');
         const newCron = cronInput.value.trim();
         
         if (!newCron) {
             this.showNotification('请输入CRON表达式', 'error');
             return;
         }
        
        try {
            this.showLoading(true);
            
            // 获取当前设置
            const settingsResponse = await fetch('/api/settings');
            const settingsResult = await settingsResponse.json();
            
            if (!settingsResult.success) {
                throw new Error('获取当前设置失败');
            }
            
            // 更新CRON设置
            const settings = {
                ...settingsResult.settings,
                CRON: newCron
            };
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ settings })
            });
            
            const result = await response.json();
            
            if (result.success) {
                let message = 'CRON表达式更新成功';
                if (result.message) {
                    message = result.message;
                }
                this.showNotification(message, 'success');
                this.refreshSchedulerStatus();
                cronInput.value = ''; // 清空输入框
            } else {
                throw new Error(result.error || '更新失败');
            }
        } catch (error) {
            console.error('更新CRON表达式失败:', error);
            this.showNotification(`更新失败: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }
}

// 全局应用实例
let app;

// DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new D2CWebUI();
});

// 全局错误处理
window.addEventListener('error', (event) => {
    console.error('全局错误:', event.error);
    if (app) {
        app.showNotification('发生未知错误，请刷新页面重试', 'error');
    }
});

// 网络错误处理
window.addEventListener('unhandledrejection', (event) => {
    console.error('未处理的Promise拒绝:', event.reason);
    if (app) {
        app.showNotification('网络请求失败，请检查连接', 'error');
    }
});