"""Integration tests for JavaScript/TypeScript scanner with real repository."""

import shutil
import tempfile
from pathlib import Path

import pytest
from git import Repo

from app.services.javascript_scanner import JavaScriptScannerService


@pytest.fixture
def javascript_scanner():
    """Create JavaScript scanner service."""
    return JavaScriptScannerService()


@pytest.fixture
def sample_javascript_repo():
    """Create a temporary JavaScript repository with authorization code."""
    # Create temporary directory
    tmpdir = tempfile.mkdtemp()
    repo_path = Path(tmpdir) / "test-javascript-repo"
    repo_path.mkdir()

    # Create Express.js file with middleware
    routes_file = repo_path / "routes.js"
    routes_file.write_text("""
const express = require('express');
const router = express.Router();

// Middleware
function requireAuth(req, res, next) {
    if (!req.isAuthenticated()) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    next();
}

function checkRole(role) {
    return (req, res, next) => {
        if (req.user.role !== role) {
            return res.status(403).json({ error: 'Forbidden' });
        }
        next();
    };
}

// Routes with authorization
router.get('/admin', requireAuth, checkRole('admin'), (req, res) => {
    res.json({ message: 'Admin area' });
});

router.post('/users', requireAuth, (req, res) => {
    if (req.user.hasPermission('create_users')) {
        res.json({ message: 'User created' });
    } else {
        res.status(403).json({ error: 'No permission' });
    }
});

module.exports = router;
""")

    # Create NestJS controller
    controller_file = repo_path / "users.controller.ts"
    controller_file.write_text("""
import { Controller, Get, Post, UseGuards } from '@nestjs/common';
import { AuthGuard } from './auth.guard';
import { Roles } from './roles.decorator';

@Controller('api/users')
export class UsersController {
    @Get()
    @UseGuards(AuthGuard)
    @Roles('admin', 'moderator')
    async findAll() {
        return [];
    }

    @Post()
    @UseGuards(AuthGuard)
    @Roles('admin')
    async create(@Body() createUserDto: CreateUserDto) {
        return {};
    }
}
""")

    # Create React component with auth checks
    react_file = repo_path / "AdminPanel.tsx"
    react_file.write_text("""
import React from 'react';

function AdminPanel({ user }) {
    if (!user.isAuthenticated) {
        return <Redirect to="/login" />;
    }

    if (!user.hasRole('admin')) {
        return <div>Access Denied</div>;
    }

    return (
        <div>
            <h1>Admin Panel</h1>
        </div>
    );
}

export default AdminPanel;
""")

    # Initialize git repo
    git_repo = Repo.init(repo_path)
    git_repo.index.add([str(routes_file), str(controller_file), str(react_file)])
    git_repo.index.commit("Initial commit with authorization code")

    yield repo_path

    # Cleanup
    shutil.rmtree(tmpdir)


def test_scan_express_file(javascript_scanner, sample_javascript_repo):
    """Test scanning Express.js file with middleware."""
    routes_file = sample_javascript_repo / "routes.js"
    content = routes_file.read_text()

    patterns = javascript_scanner.analyze_file(content, str(routes_file))

    # Should detect middleware
    assert len(patterns["middleware"]) >= 2
    assert any(m["middleware"] == "requireAuth" for m in patterns["middleware"])
    assert any(m["middleware"] == "checkRole" for m in patterns["middleware"])

    # Should detect method calls
    assert len(patterns["method_calls"]) >= 1
    assert any(m["method"] == "hasPermission" for m in patterns["method_calls"])


def test_scan_nestjs_file(javascript_scanner, sample_javascript_repo):
    """Test scanning NestJS controller with decorators."""
    controller_file = sample_javascript_repo / "users.controller.ts"
    content = controller_file.read_text()

    patterns = javascript_scanner.analyze_file(content, str(controller_file))

    # Should detect decorators
    assert len(patterns["decorators"]) >= 2
    assert any(d["decorator"] == "UseGuards" for d in patterns["decorators"])
    assert any(d["decorator"] == "Roles" for d in patterns["decorators"])


def test_scan_react_file(javascript_scanner, sample_javascript_repo):
    """Test scanning React component with authorization checks."""
    react_file = sample_javascript_repo / "AdminPanel.tsx"
    content = react_file.read_text()

    patterns = javascript_scanner.analyze_file(content, str(react_file))

    # Should detect conditionals
    assert len(patterns["conditionals"]) >= 1
    assert any(c["condition"] in ["isAuthenticated", "hasRole"] for c in patterns["conditionals"])


def test_prompt_enhancement(javascript_scanner, sample_javascript_repo):
    """Test that prompt enhancement works for all file types."""
    # Test Express.js
    routes_file = sample_javascript_repo / "routes.js"
    content = routes_file.read_text()
    enhancement = javascript_scanner.enhance_prompt(content, str(routes_file))
    assert "Express.js/NestJS Middleware" in enhancement

    # Test NestJS
    controller_file = sample_javascript_repo / "users.controller.ts"
    content = controller_file.read_text()
    enhancement = javascript_scanner.enhance_prompt(content, str(controller_file))
    assert "NestJS Authorization Decorators" in enhancement

    # Test React
    react_file = sample_javascript_repo / "AdminPanel.tsx"
    content = react_file.read_text()
    enhancement = javascript_scanner.enhance_prompt(content, str(react_file))
    assert enhancement != ""  # Should have some enhancement
