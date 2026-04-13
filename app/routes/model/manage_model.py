import os
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models import db
from app.models.yolo_model import YoloModel
from . import model_bp

@model_bp.route('/add', methods=['POST'])
@jwt_required()
def add_model():
    try:
        model_name = request.form.get('model_name')
        if not model_name:
            return jsonify({'code': 400, 'msg': 'Model name is required'}), 400

        if 'model_file' not in request.files:
            return jsonify({'code': 400, 'msg': 'No file part'}), 400
        
        file = request.files['model_file']
        if file.filename == '':
            return jsonify({'code': 400, 'msg': 'No selected file'}), 400

        # Ensure yolo_models directory exists in project root
        base_dir = current_app.config['BASE_DIR']
        save_dir = os.path.join(base_dir, 'yolo_models')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        filename = secure_filename(file.filename)
        
        # Generate unique filename to avoid overwrite and conflicts
        import time
        name, ext = os.path.splitext(filename)
        timestamp = int(time.time())
        unique_filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join(save_dir, unique_filename)
        file.save(file_path)

        # Get current user
        current_user_id = get_jwt_identity()

        # Check if there are any existing models
        # If no models exist, the first one is '启用', otherwise '停用'
        existing_count = YoloModel.query.count()
        initial_status = '启用' if existing_count == 0 else '停用'

        # Save to DB
        new_model = YoloModel(
            model_name=model_name,
            model_url=unique_filename, 
            upload_by=current_user_id,
            status=initial_status
        )
        db.session.add(new_model)
        db.session.commit()

        return jsonify({'code': 200, 'msg': 'Model added successfully'})

    except Exception as e:
        current_app.logger.error(f"Error adding model: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500

@model_bp.route('/list', methods=['GET'])
@jwt_required()
def get_model_list():
    try:
        # Fetch all models
        models = YoloModel.query.order_by(YoloModel.upload_at.desc()).all()
        
        # Sort: '启用' first, then others
        # Since Python sort is stable, we can sort by status being '启用'
        sorted_models = sorted(models, key=lambda x: x.status != '启用')
        
        return jsonify({
            'code': 200, 
            'msg': 'Success', 
            'data': [m.to_dict() for m in sorted_models]
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching model list: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500

@model_bp.route('/enable/<int:model_id>', methods=['POST'])
@jwt_required()
def enable_model(model_id):
    try:
        # Find the target model
        target_model = db.session.get(YoloModel, model_id)
        if not target_model:
            return jsonify({'code': 404, 'msg': 'Model not found'}), 404

        # Update all models to '停用'
        YoloModel.query.update({YoloModel.status: '停用'})
        
        # Set target model to '启用'
        target_model.status = '启用'
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': 'Model enabled successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error enabling model: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500

@model_bp.route('/detail/<int:model_id>', methods=['GET'])
@jwt_required()
def get_model_detail(model_id):
    try:
        model = db.session.get(YoloModel, model_id)
        if not model:
            return jsonify({'code': 404, 'msg': 'Model not found'}), 404
            
        base_dir = current_app.config['BASE_DIR']
        full_path = os.path.join(base_dir, 'yolo_models', model.model_url)
        
        data = model.to_dict()
        data['full_path'] = full_path
        
        return jsonify({'code': 200, 'msg': 'Success', 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error fetching model detail: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500

@model_bp.route('/update/<int:model_id>', methods=['POST'])
@jwt_required()
def update_model(model_id):
    try:
        model = db.session.get(YoloModel, model_id)
        if not model:
            return jsonify({'code': 404, 'msg': 'Model not found'}), 404
            
        new_name = request.json.get('model_name')
        if not new_name:
             return jsonify({'code': 400, 'msg': 'Model name is required'}), 400
             
        model.model_name = new_name
        db.session.commit()
        
        return jsonify({'code': 200, 'msg': 'Model updated successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating model: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500

@model_bp.route('/delete/<int:model_id>', methods=['DELETE'])
@jwt_required()
def delete_model(model_id):
    try:
        model = db.session.get(YoloModel, model_id)
        if not model:
            return jsonify({'code': 404, 'msg': 'Model not found'}), 404

        # Prevent deleting the active model if it's the only one? 
        # Requirement says "one and only one active". 
        # If we delete the active one, we might violate this if we don't activate another.
        # However, usually user deletes then enables another. 
        # But let's just allow delete. If they delete the active one, no model is active.
        # Wait, requirement: "有且只有一条记录的状态是“启用”".
        # If I delete the active one, 0 are active.
        # I should probably warn or auto-activate another?
        # For now, let's just allow delete. The user can enable another.
        # Or I can forbid deleting the active model.
        if model.status == '启用':
             return jsonify({'code': 400, 'msg': '无法删除正在使用的模型，请先启用其他模型。'}), 400

        # Delete file
        base_dir = current_app.config['BASE_DIR']
        file_path = os.path.join(base_dir, 'yolo_models', model.model_url)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"Error deleting file: {e}")

        db.session.delete(model)
        db.session.commit()
        return jsonify({'code': 200, 'msg': 'Model deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting model: {e}")
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500