"""Tests for source type classification."""

from app.models.policy import SourceType
from app.services.scanner_service import ScannerService


class TestSourceTypeClassification:
    """Test source type classification logic."""

    def test_classify_frontend_react(self):
        """Test React frontend file is classified as frontend."""
        scanner = ScannerService(db=None)

        file_path = "frontend/src/components/LoginButton.tsx"
        content = """
import React, { useState } from 'react';

function LoginButton() {
  const [user, setUser] = useState(null);

  const handleLogin = () => {
    if (user.role === 'admin') {
      return <AdminPanel />;
    }
  };

  return <button onClick={handleLogin}>Login</button>;
}
"""

        result = scanner._classify_source_type(file_path, content)
        assert result == SourceType.FRONTEND

    def test_classify_backend_python(self):
        """Test Python backend file is classified as backend."""
        scanner = ScannerService(db=None)

        file_path = "backend/app/api/endpoints/users.py"
        content = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def get_users():
    if request.user.role == 'admin':
        return all_users()
"""

        result = scanner._classify_source_type(file_path, content)
        assert result == SourceType.BACKEND

    def test_classify_backend_java_controller(self):
        """Test Java Spring controller is classified as backend."""
        scanner = ScannerService(db=None)

        file_path = "src/main/java/controllers/UserController.java"
        content = """
@RestController
@RequestMapping("/api/users")
public class UserController {

    @PreAuthorize("hasRole('ADMIN')")
    @GetMapping
    public List<User> getUsers() {
        return userService.findAll();
    }
}
"""

        result = scanner._classify_source_type(file_path, content)
        assert result == SourceType.BACKEND

    def test_classify_frontend_vue(self):
        """Test Vue component is classified as frontend."""
        scanner = ScannerService(db=None)

        file_path = "client/components/UserList.vue"
        content = """
<template>
  <div v-if="user.isAdmin">
    <h1>Admin Panel</h1>
  </div>
</template>

<script>
export default {
  name: 'UserList',
  computed: {
    canEdit() {
      return this.user.role === 'admin';
    }
  }
}
</script>
"""

        result = scanner._classify_source_type(file_path, content)
        assert result == SourceType.FRONTEND

    def test_classify_unknown(self):
        """Test file with ambiguous classification."""
        scanner = ScannerService(db=None)

        file_path = "utils/helper.py"
        content = """
def check_permission(user):
    return user.role == 'admin'
"""

        result = scanner._classify_source_type(file_path, content)
        # Could be either backend or unknown depending on scoring
        assert result in [SourceType.BACKEND, SourceType.UNKNOWN]
