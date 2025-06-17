// Dashboard页面JavaScript功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Toast通知
    const toastEl = document.getElementById('liveToast');
    const toast = new bootstrap.Toast(toastEl);
    
    // 显示通知消息
    function showToast(message, isSuccess = true) {
        const toastBody = toastEl.querySelector('.toast-body');
        toastBody.textContent = message;
        toastEl.classList.remove('bg-success', 'bg-danger');
        toastEl.classList.add(isSuccess ? 'bg-success' : 'bg-danger');
        toast.show();
    }

    // WordPress表单提交
    const wordpressForm = document.getElementById('wordpressForm');
    if (wordpressForm) {
        wordpressForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const isEdit = !!formData.get('id');
            
            fetch('/api/wordpress', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(isEdit ? 'WordPress站点更新成功' : 'WordPress站点添加成功');
                    $('#addWordpressModal').modal('hide');
                    refreshData();
                } else {
                    showToast(data.message || '操作失败', false);
                }
            })
            .catch(error => {
                showToast('网络错误: ' + error.message, false);
            });
        });
    }

    // WeChat表单提交
    const wechatForm = document.getElementById('wechatForm');
    if (wechatForm) {
        wechatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const isEdit = !!formData.get('id');
            
            fetch('/api/wechat', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(isEdit ? '微信公众号更新成功' : '微信公众号添加成功');
                    $('#addWechatModal').modal('hide');
                    refreshData();
                } else {
                    showToast(data.message || '操作失败', false);
                }
            })
            .catch(error => {
                showToast('网络错误: ' + error.message, false);
            });
        });
    }

    // 删除WordPress站点
    document.querySelectorAll('.delete-wordpress').forEach(btn => {
        btn.addEventListener('click', function() {
            if (confirm('确定要删除这个WordPress站点吗？')) {
                const id = this.dataset.id;
                fetch(`/api/wordpress/${id}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showToast('WordPress站点删除成功');
                        refreshData();
                    } else {
                        showToast(data.error || '删除失败', false);
                    }
                });
            }
        });
    });

    // 删除微信公众号
    document.querySelectorAll('.delete-wechat').forEach(btn => {
        btn.addEventListener('click', function() {
            if (confirm('确定要删除这个微信公众号吗？')) {
                const id = this.dataset.id;
                fetch(`/api/wechat/${id}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showToast('微信公众号删除成功');
                        refreshData();
                    } else {
                        showToast(data.error || '删除失败', false);
                    }
                });
            }
        });
    });

    // 刷新数据
    function refreshData() {
        // 简单刷新整个页面
        window.location.reload();
        
        // 更优雅的方式是使用AJAX重新加载数据并更新DOM
        // 但这需要更复杂的实现
    }

    // 编辑按钮事件委托
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('edit-wordpress')) {
            const modal = $('#addWordpressModal');
            modal.find('input[name="id"]').val(e.target.dataset.id);
            modal.find('input[name="site_name"]').val(e.target.dataset.site_name);
            modal.find('input[name="site_url"]').val(e.target.dataset.site_url);
            modal.find('input[name="username"]').val(e.target.dataset.username);
            modal.modal('show');
        }
        
        if (e.target.classList.contains('edit-wechat')) {
            const modal = $('#addWechatModal');
            modal.find('input[name="id"]').val(e.target.dataset.id);
            modal.find('input[name="account_name"]').val(e.target.dataset.account_name);
            modal.find('input[name="account_id"]').val(e.target.dataset.account_id);
            modal.find('input[name="app_id"]').val(e.target.dataset.app_id);
            modal.find('input[name="app_secret"]').val(e.target.dataset.app_secret);
            modal.modal('show');
        }
    });
});