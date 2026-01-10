const express = require('express');
const router = express.Router();

// Middleware to check if user is authenticated
const requireAuth = (req, res, next) => {
    if (!req.user) {
        return res.status(401).json({ error: 'Authentication required' });
    }
    next();
};

// Middleware to check for specific role
const requireRole = (role) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ error: 'Authentication required' });
        }
        if (!req.user.roles.includes(role)) {
            return res.status(403).json({ error: `${role} role required` });
        }
        next();
    };
};

// Middleware to check for any of specified roles
const requireAnyRole = (...roles) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ error: 'Authentication required' });
        }
        if (!roles.some(role => req.user.roles.includes(role))) {
            return res.status(403).json({ error: `One of these roles required: ${roles.join(', ')}` });
        }
        next();
    };
};

// Get all expenses - requires authentication
router.get('/api/expenses', requireAuth, async (req, res) => {
    const expenses = await Expense.findAll();
    res.json(expenses);
});

// Create expense - requires MANAGER role
router.post('/api/expenses', requireRole('MANAGER'), async (req, res) => {
    const expense = await Expense.create(req.body);
    res.status(201).json(expense);
});

// Approve expense - MANAGER for < $5000, DIRECTOR for higher
router.put('/api/expenses/:id/approve', requireAnyRole('MANAGER', 'DIRECTOR'), async (req, res) => {
    const expense = await Expense.findByPk(req.params.id);

    if (!expense) {
        return res.status(404).json({ error: 'Expense not found' });
    }

    if (expense.amount > 5000 && !req.user.roles.includes('DIRECTOR')) {
        return res.status(403).json({ error: 'Director role required for amounts over $5,000' });
    }

    expense.approved = true;
    await expense.save();
    res.json(expense);
});

// Delete expense - requires ADMIN role
router.delete('/api/expenses/:id', requireRole('ADMIN'), async (req, res) => {
    await Expense.destroy({ where: { id: req.params.id } });
    res.status(204).send();
});

// Financial report - Finance department only
router.get('/api/reports/financial', requireAuth, async (req, res) => {
    if (req.user.department !== 'Finance') {
        return res.status(403).json({ error: 'Finance department access required' });
    }

    const report = await generateFinancialReport();
    res.json(report);
});

module.exports = router;
