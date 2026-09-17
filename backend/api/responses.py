from __future__ import annotations

from flask import jsonify


def ok(data, status: int = 200):
    return jsonify({"success": True, "data": data, "error": None}), status


def fail(code: str, message: str, details=None, status: int = 400):
    return jsonify({"success": False, "data": None, "error": {"code": code, "message": message, "details": details or {}}}), status
