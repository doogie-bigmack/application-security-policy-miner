"""Tests for JavaScript/TypeScript scanner service."""

import pytest

from app.services.javascript_scanner import JavaScriptScannerService


@pytest.fixture
def javascript_scanner():
    """Create JavaScript scanner instance."""
    return JavaScriptScannerService()


def test_detect_nestjs_decorators(javascript_scanner):
    """Test detection of NestJS authorization decorators."""
    code = """
    @Controller('users')
    export class UsersController {
        @Get()
        @UseGuards(AuthGuard)
        @Roles('admin', 'moderator')
        async findAll() {
            return this.usersService.findAll();
        }
    }
    """

    patterns = javascript_scanner.analyze_file(code, "users.controller.ts")

    assert len(patterns["decorators"]) == 2
    assert any(d["decorator"] == "UseGuards" for d in patterns["decorators"])
    assert any(d["decorator"] == "Roles" for d in patterns["decorators"])


def test_detect_express_middleware(javascript_scanner):
    """Test detection of Express.js middleware patterns."""
    code = """
    const express = require('express');
    const app = express();

    app.get('/admin', requireAuth, checkRole('admin'), (req, res) => {
        res.json({ message: 'Admin area' });
    });

    app.post('/users', isAuthenticated, (req, res) => {
        // Create user
    });
    """

    patterns = javascript_scanner.analyze_file(code, "routes.js")

    assert len(patterns["middleware"]) >= 2
    assert any(m["middleware"] == "requireAuth" for m in patterns["middleware"])
    assert any(m["middleware"] == "checkRole" for m in patterns["middleware"])


def test_detect_authorization_method_calls(javascript_scanner):
    """Test detection of authorization method calls."""
    code = """
    function canDeleteUser(user, targetUser) {
        if (user.hasRole('admin') || user.id === targetUser.id) {
            return true;
        }
        return user.hasPermission('delete_users');
    }

    async function updateProfile(req, res) {
        if (!req.isAuthenticated()) {
            return res.status(401).json({ error: 'Unauthorized' });
        }
        // Update profile
    }
    """

    patterns = javascript_scanner.analyze_file(code, "auth.js")

    assert len(patterns["method_calls"]) >= 2
    assert any(m["method"] == "hasRole" for m in patterns["method_calls"])
    assert any(m["method"] == "hasPermission" for m in patterns["method_calls"])


def test_detect_authorization_conditionals(javascript_scanner):
    """Test detection of authorization conditionals."""
    code = """
    function approveExpense(user, expense) {
        if (user.role === 'manager' && expense.amount < 5000) {
            return expense.approve();
        }

        if (user.isAdmin || user.hasPermission('approve_all')) {
            return expense.approve();
        }

        throw new Error('Unauthorized');
    }
    """

    patterns = javascript_scanner.analyze_file(code, "expenses.js")

    assert len(patterns["conditionals"]) >= 2
    assert any(c["condition"] in ["user.role", "isAdmin"] for c in patterns["conditionals"])


def test_line_number_accuracy(javascript_scanner):
    """Test that line numbers are accurately reported."""
    code = """line 1
line 2
function test() {
    if (user.isAuthenticated) {
        return true;
    }
}
line 8
"""

    patterns = javascript_scanner.analyze_file(code, "test.js")

    # The conditional should be around line 4
    assert len(patterns["conditionals"]) == 1
    assert 3 <= patterns["conditionals"][0]["line"] <= 5


def test_typescript_decorators(javascript_scanner):
    """Test detection of TypeScript decorators."""
    code = """
    import { Controller, Get, UseGuards } from '@nestjs/common';

    @Controller('api/posts')
    export class PostsController {
        @Get()
        @Public()
        async findAll() {
            return [];
        }

        @Get(':id')
        @UseGuards(AuthGuard)
        async findOne(@Param('id') id: string) {
            return {};
        }
    }
    """

    patterns = javascript_scanner.analyze_file(code, "posts.controller.ts")

    assert len(patterns["decorators"]) >= 2
    assert any(d["decorator"] == "Public" for d in patterns["decorators"])
    assert any(d["decorator"] == "UseGuards" for d in patterns["decorators"])


def test_react_authorization_patterns(javascript_scanner):
    """Test detection of authorization patterns in React components."""
    code = """
    import React from 'react';

    function AdminPanel({ user }) {
        if (!user.isAuthenticated) {
            return <Redirect to="/login" />;
        }

        if (!user.hasRole('admin')) {
            return <Forbidden />;
        }

        return (
            <div>Admin Panel</div>
        );
    }
    """

    patterns = javascript_scanner.analyze_file(code, "AdminPanel.tsx")

    assert len(patterns["conditionals"]) >= 1
    assert any(c["condition"] in ["isAuthenticated", "hasRole"] for c in patterns["conditionals"])


def test_enhance_prompt(javascript_scanner):
    """Test prompt enhancement with JavaScript context."""
    code = """
    app.get('/users', requireAuth, checkRole('admin'), (req, res) => {
        if (req.user.hasPermission('view_users')) {
            res.json({ users: [] });
        }
    });
    """

    enhancement = javascript_scanner.enhance_prompt(code, "routes.js")

    assert enhancement != ""
    assert "Express.js/NestJS Middleware" in enhancement or "Authorization Method Calls" in enhancement


def test_no_authorization_code(javascript_scanner):
    """Test that files without authorization return empty patterns."""
    code = """
    function add(a, b) {
        return a + b;
    }

    const result = add(1, 2);
    console.log(result);
    """

    patterns = javascript_scanner.analyze_file(code, "math.js")

    assert len(patterns["decorators"]) == 0
    assert len(patterns["middleware"]) == 0
    assert len(patterns["method_calls"]) == 0
    assert len(patterns["conditionals"]) == 0


def test_multiple_patterns_same_file(javascript_scanner):
    """Test detection of multiple authorization patterns in same file."""
    code = """
    @Controller('api/admin')
    @UseGuards(AdminGuard)
    export class AdminController {
        @Get('users')
        @Roles('admin')
        async getUsers(req: Request) {
            if (!req.user.hasPermission('view_users')) {
                throw new ForbiddenException();
            }

            return this.userService.findAll();
        }

        @Post('users')
        @RequireAuth()
        async createUser(req: Request) {
            if (!req.isAuthenticated()) {
                throw new UnauthorizedException();
            }

            return this.userService.create(req.body);
        }
    }
    """

    patterns = javascript_scanner.analyze_file(code, "admin.controller.ts")

    # Should detect decorators, method calls, and conditionals
    assert len(patterns["decorators"]) >= 3
    assert len(patterns["method_calls"]) >= 1
    assert len(patterns["conditionals"]) >= 1
