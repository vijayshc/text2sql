"""Admin file browser routes."""

from __future__ import annotations

import logging
from http import HTTPStatus

from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
    session,
)

from src.routes.auth_routes import admin_required
from src.services.file_browser_service import file_browser_service
from src.utils.user_manager import UserManager

logger = logging.getLogger("text2sql.admin.file_browser")

admin_file_browser_bp = Blueprint(
    "admin_file_browser",
    __name__,
    url_prefix="/admin/file-browser",
)

user_manager = UserManager()


@admin_file_browser_bp.route("/")
@admin_required
def file_browser_home() -> str:
    """Render the admin file browser page."""
    user_manager.log_audit_event(
        user_id=session.get("user_id"),
        action="access_file_browser",
        details="Accessed admin file browser",
        ip_address=request.remote_addr,
    )
    return render_template(
        "admin/file_browser.html",
        allowed_extensions=sorted(file_browser_service.allowed_extensions),
        available_templates=["admin/file_browser.html"],
    )


@admin_file_browser_bp.route("/api/list", methods=["GET"])
@admin_required
def list_directory() -> Response:
    relative_path = request.args.get("path", "")
    try:
        listing = file_browser_service.list_directory(relative_path)
        for item in listing["items"]:
            uploader_id = item.get("uploadedBy")
            item["uploadedByName"] = (
                user_manager.get_username_by_id(uploader_id) if uploader_id else None
            )
        return jsonify(listing)
    except FileNotFoundError:
        return jsonify({"error": "Directory not found"}), HTTPStatus.NOT_FOUND
    except NotADirectoryError:
        return jsonify({"error": "Path is not a directory"}), HTTPStatus.BAD_REQUEST
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected error while listing directory: %s", exc)
        return jsonify({"error": "Failed to list directory"}), HTTPStatus.INTERNAL_SERVER_ERROR


@admin_file_browser_bp.route("/api/upload-file", methods=["POST"])
@admin_required
def upload_file() -> Response:
    uploaded_file = request.files.get("file")
    target_path = request.form.get("path", "")
    user_id = session.get("user_id")

    if not uploaded_file:
        return jsonify({"error": "No file provided"}), HTTPStatus.BAD_REQUEST

    try:
        stored_path = file_browser_service.save_uploaded_file(target_path, uploaded_file, user_id)
        user_manager.log_audit_event(
            user_id=user_id,
            action="upload_file",
            details=f"Uploaded file: {stored_path}",
            ip_address=request.remote_addr,
        )
        uploader_name = user_manager.get_username_by_id(user_id) if user_id else None
        return jsonify({"success": True, "path": stored_path, "uploadedBy": uploader_name})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except NotADirectoryError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected error during file upload: %s", exc)
        return jsonify({"error": "Failed to upload file"}), HTTPStatus.INTERNAL_SERVER_ERROR


@admin_file_browser_bp.route("/api/upload-folder", methods=["POST"])
@admin_required
def upload_folder() -> Response:
    files = request.files.getlist("files")
    relative_paths = request.form.getlist("relative_paths")
    target_path = request.form.get("path", "")
    user_id = session.get("user_id")

    if not files:
        return jsonify({"error": "No files provided"}), HTTPStatus.BAD_REQUEST
    if len(files) != len(relative_paths):
        return jsonify({"error": "Relative path metadata missing"}), HTTPStatus.BAD_REQUEST

    try:
        stored_paths = file_browser_service.save_uploaded_folder(
            target_path,
            files,
            relative_paths,
            user_id,
        )
        user_manager.log_audit_event(
            user_id=user_id,
            action="upload_folder",
            details=f"Uploaded folder containing {len(stored_paths)} files to {target_path or '/'}",
            ip_address=request.remote_addr,
        )
        return jsonify({"success": True, "files": stored_paths})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except NotADirectoryError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected error during folder upload: %s", exc)
        return jsonify({"error": "Failed to upload folder"}), HTTPStatus.INTERNAL_SERVER_ERROR


@admin_file_browser_bp.route("/api/download-file", methods=["GET"])
@admin_required
def download_file() -> Response:
    relative_path = request.args.get("path")
    if not relative_path:
        return jsonify({"error": "Missing path"}), HTTPStatus.BAD_REQUEST
    try:
        file_path = file_browser_service.get_file_path(relative_path)
        if not file_path.is_file():
            return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
        user_manager.log_audit_event(
            user_id=session.get("user_id"),
            action="download_file",
            details=f"Downloaded file: {relative_path}",
            ip_address=request.remote_addr,
        )
        return send_file(file_path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@admin_file_browser_bp.route("/api/download-folder", methods=["GET"])
@admin_required
def download_folder() -> Response:
    relative_path = request.args.get("path", "")
    try:
        buffer, filename = file_browser_service.stream_folder_as_zip(relative_path)
        user_manager.log_audit_event(
            user_id=session.get("user_id"),
            action="download_folder",
            details=f"Downloaded folder: {relative_path or '/'}",
            ip_address=request.remote_addr,
        )
        return send_file(
            buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename,
        )
    except FileNotFoundError:
        return jsonify({"error": "Folder not found"}), HTTPStatus.NOT_FOUND
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@admin_file_browser_bp.route("/api/file-content", methods=["GET"])
@admin_required
def get_file_content() -> Response:
    relative_path = request.args.get("path")
    if not relative_path:
        return jsonify({"error": "Missing path"}), HTTPStatus.BAD_REQUEST
    try:
        content = file_browser_service.get_file_content(relative_path)
        return jsonify({"path": relative_path, "content": content})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@admin_file_browser_bp.route("/api/file-content", methods=["PUT"])
@admin_required
def update_file_content() -> Response:
    payload = request.get_json(force=True)
    relative_path = payload.get("path") if payload else None
    content = payload.get("content") if payload else None
    user_id = session.get("user_id")

    if not relative_path:
        return jsonify({"error": "Missing path"}), HTTPStatus.BAD_REQUEST
    if content is None:
        return jsonify({"error": "Missing content"}), HTTPStatus.BAD_REQUEST

    try:
        file_browser_service.update_file_content(relative_path, content, user_id)
        user_manager.log_audit_event(
            user_id=user_id,
            action="edit_file",
            details=f"Edited file: {relative_path}",
            ip_address=request.remote_addr,
        )
        uploader_name = user_manager.get_username_by_id(user_id) if user_id else None
        return jsonify({"success": True, "uploadedBy": uploader_name})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@admin_file_browser_bp.route("/api/item", methods=["DELETE"])
@admin_required
def delete_item() -> Response:
    payload = request.get_json(force=True)
    relative_path = payload.get("path") if payload else None

    if not relative_path:
        return jsonify({"error": "Missing path"}), HTTPStatus.BAD_REQUEST

    try:
        file_browser_service.delete_path(relative_path)
        user_manager.log_audit_event(
            user_id=session.get("user_id"),
            action="delete_item",
            details=f"Deleted path: {relative_path}",
            ip_address=request.remote_addr,
        )
        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"error": "Path not found"}), HTTPStatus.NOT_FOUND
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
