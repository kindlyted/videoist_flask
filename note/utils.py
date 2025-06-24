import os 
def process_pdf_to_image(pdf_path):
    # 这里将返回一个模拟的图片路径
    from flask import current_app
    output_dir = os.path.join(current_app.root_path, 'note', 'static', 'output')
    print(f"Output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    # 返回相对于static目录的路径
    return 'note_sample.png'