// Dashboard页面JavaScript功能
// 确保jQuery已加载
if (typeof jQuery == 'undefined') {
    console.error('错误：jQuery未正确加载！请检查：');
    console.error('1. base.html中是否包含jQuery引用');
    console.error('2. jQuery是否在dashboard.js之前加载');
    throw new Error('jQuery未正确加载');
}

$(document).ready(function() {
        // WordPress编辑按钮点击事件
        $('.edit-wordpress').on('click', function() {
            const $modal = $('#addWordpressModal');
            const $form = $('#wordpressForm');
            
            // 更新模态框标题
            $('#wordpressModalTitle').text('编辑 WordPress 站点');
            
            // 填充表单数据
            $form.find('input[name="id"]').val($(this).data('id'));
            $form.find('input[name="site_name"]').val($(this).data('site-name'));
            $form.find('input[name="site_url"]').val($(this).data('site-url'));
            $form.find('input[name="username"]').val($(this).data('username'));
            
            // 显示模态框
            $modal.modal('show');
        });

        // 添加按钮点击事件 - 重置表单和标题
        $('[data-bs-target="#addWordpressModal"]').on('click', function() {
            $('#wordpressModalTitle').text('添加 WordPress 站点');
            $('#wordpressForm')[0].reset();
        });

        // 微信公众号编辑按钮点击事件
        $(document).on('click', '.edit-wechat', function() {
            const $modal = $('#addWechatModal');
            const $form = $('#wechatForm');
            
            // 更新模态框标题
            $('#wechatModalTitle').text('编辑微信公众号');
            
            // 填充表单数据
            $form.find('input[name="id"]').val($(this).data('id'));
            $form.find('input[name="account_name"]').val($(this).data('account-name'));
            $form.find('input[name="account_id"]').val($(this).data('account-id'));
            $form.find('input[name="app_id"]').val($(this).data('app-id'));
            
            // 显示模态框
            $modal.modal('show');
            
            // 阻止默认行为
            return false;
        });

        // 微信公众号添加按钮点击事件 - 重置表单和标题
        $('[data-bs-target="#addWechatModal"]').on('click', function() {
            $('#wechatModalTitle').text('添加微信公众号');
            $('#wechatForm')[0].reset();
        });

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
            type: 'POST',
            url: '/api/wordpress',
            contentType: 'application/json',
            data: JSON.stringify({
                id: isEdit ? id : null,
                site_name: $('#site-name').val(),
                site_url: $('#site-url').val(),
                username: $('#username').val(),
                api_key: $('#api-key').val()
            }),
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

        $.ajax({
            type: 'POST',
            url: '/api/wechat',
            data: {
                id: isEdit ? id : null,
                account_name: $('#account-name').val(),
                app_id: $('#app-id').val(),
                app_secret: $('#app-secret').val(),
                csrf_token: $('input[name="csrf_token"]').val()
            },
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
        modal.modal('show');
    });

    // 调试WordPress模态框
    console.log('初始化WordPress模态框事件');
    
    $('#addWordpressModal').on('show.bs.modal', function() {
        console.log('WordPress模态框显示');
    });
    
    $('#addWordpressModal').on('hidden.bs.modal', function () {
        console.log('WordPress模态框隐藏');
        // 重置表单
        $(this).find('form')[0].reset();
        // 重置标题
        $(this).find('.modal-title').text('添加 WordPress 站点');
        // 清除隐藏的ID字段
        $(this).find('input[name="id"]').val('');
    });

    // 手动绑定取消按钮
    $(document).on('click', '[data-bs-dismiss="modal"]', function() {
        console.log('取消按钮点击');
        $(this).closest('.modal').modal('hide');
    });

    // 微信公众号模态框隐藏事件
    $('#addWechatModal').on('hidden.bs.modal', function () {
        // 重置表单
        $(this).find('form')[0].reset();
        // 重置标题
        $(this).find('.modal-title').text('添加微信公众号');
        // 清除隐藏的ID字段
        $(this).find('input[name="id"]').val('');
    });
});