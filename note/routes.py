from flask import render_template, Blueprint, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
from . import note_bp as bp

bp = Blueprint('note', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/notes-generator')
def index():
    return render_template('note/index.html')

@bp.route('/notes-generator', methods=['GET', 'POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 保存上传的文件（实际项目中应该保存到特定目录）
        # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # 调用桩函数处理PDF
        image_path = process_pdf_to_image(filename)
    
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'image_url': url_for('static', filename='output/' + os.path.basename(image_path))
        })
    
    return jsonify({'success': False, 'message': '文件类型不支持'})

# 桩函数 - 待替换为实际PDF处理逻辑
def process_pdf_to_image(pdf_path):
    # 这里将返回一个模拟的图片路径
    from flask import current_app
    output_dir = os.path.join(current_app.root_path, 'note', 'static', 'output')
    print(f"Output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    # 返回相对于static目录的路径
    return 'note_sample.png'