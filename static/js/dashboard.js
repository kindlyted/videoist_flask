// Dashboard页面JavaScript功能
$(document).ready(function() {
    // 显示通知消息
    function showToast(type, message) {
        const toastEl = $('#liveToast');
        toastEl.find('.toast-body').text(message);
        toastEl.removeClass('bg-success bg-danger').addClass(type === 'success' ? 'bg-success' : 'bg-danger');
        toastEl.toast('show');
    }

    // WordPress表单提交
    $('#wordpressForm').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const formData = new FormData(this);
        const id = formData.get('id');
        const isEdit = !!id;
        
        // 验证ID格式
        if (isEdit && !/^\d+$/.test(id)) {
            showToast('error', '站点ID必须是数字');
            return;
        }

        $.ajax({
            type: isEdit ? 'PUT' : 'POST',
            url: isEdit ? `/api/wordpress/${id}` : '/api/wordpress',
            data: formData,
            processData: false,
            contentType: false,
            cache: false,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': $('input[name="csrf_token"]').val()
            },
            success: function(response) {
                if (response.success) {
                    showToast('success', isEdit ? 'WordPress站点更新成功' : 'WordPress站点添加成功');
                    $('#addWordpressModal').modal('hide');
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    showToast('error', response.message || '操作失败');
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON && xhr.responseJSON.message 
                    ? xhr.responseJSON.message 
                    : '服务器错误，请稍后再试';
                showToast('error', errorMsg);
            }
        });
    });

    // 微信公众号表单提交
    $('#wechatForm').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const formData = new FormData(this);
        const id = formData.get('id');
        const isEdit = !!id;
        
        // 验证ID格式
        if (isEdit && !/^\d+$/.test(id)) {
            showToast('error', '公众号ID必须是数字');
            return;
        }

        // 将FormData转换为JSON
        const jsonData = {};
        formData.forEach((value, key) => jsonData[key] = value);
        
        $.ajax({
            type: 'POST',
            url: '/api/wechat',
            data: JSON.stringify(jsonData),
            contentType: 'application/json',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': $('input[name="csrf_token"]').val()
            },
            success: function(response) {
                if (response.success) {
                    showToast('success', isEdit ? '微信公众号更新成功' : '微信公众号添加成功');
                    $('#addWechatModal').modal('hide');
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    showToast('error', response.message || '操作失败');
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON && xhr.responseJSON.message 
                    ? xhr.responseJSON.message 
                    : '服务器错误，请稍后再试';
                showToast('error', errorMsg);
            }
        });
    });

    // 删除WordPress站点
    $('.delete-wordpress').on('click', function() {
        const id = $(this).data('id');
        if (confirm('确定要删除这个WordPress站点吗？')) {
            $.ajax({
                type: 'DELETE',
                url: `/api/wordpress/${id}`,
                success: function(response) {
                    if (response.success) {
                        showToast('success', 'WordPress站点删除成功');
                        setTimeout(function() {
                            location.reload();
                        }, 1500);
                    }
                },
                error: function(xhr) {
                    showToast('error', '删除失败: ' + (xhr.responseJSON && xhr.responseJSON.message || '服务器错误'));
                }
            });
        }
    });

    // 删除微信公众号
    $('.delete-wechat').on('click', function() {
        const id = $(this).data('id');
        if (confirm('确定要删除这个微信公众号吗？')) {
            $.ajax({
                type: 'DELETE',
                url: `/api/wechat/${id}`,
                success: function(response) {
                    if (response.success) {
                        showToast('success', '公众号删除成功');
                        setTimeout(function() {
                            location.reload();
                        }, 1500);
                    }
                },
                error: function(xhr) {
                    showToast('error', '删除失败: ' + (xhr.responseJSON && xhr.responseJSON.message || '服务器错误'));
                }
            });
        }
    });

    // 编辑按钮事件委托
    $(document).on('click', '.edit-wordpress', function() {
        const modal = $('#addWordpressModal');
        modal.find('input[name="id"]').val($(this).data('id'));
        modal.find('input[name="site_name"]').val($(this).data('site_name'));
        modal.find('input[name="site_url"]').val($(this).data('site_url'));
        modal.find('input[name="username"]').val($(this).data('username'));
        modal.modal('show');
    });

    $(document).on('click', '.edit-wechat', function() {
        const modal = $('#addWechatModal');
        modal.find('input[name="id"]').val($(this).data('id'));
        modal.find('input[name="account_name"]').val($(this).data('account_name'));
        modal.find('input[name="account_id"]').val($(this).data('account_id'));
        modal.find('input[name="app_id"]').val($(this).data('app_id'));
        modal.find('input[name="app_secret"]').val($(this).data('app_secret'));
        modal.modal('show');
    });
});