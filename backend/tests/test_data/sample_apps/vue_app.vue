<script setup lang="ts">
import { computed } from 'vue';
import { useAuth } from '@/composables/useAuth';
import { useRouter } from 'vue-router';

const { user, isAuthenticated } = useAuth();
const router = useRouter();

// Expense List Component
const ExpenseList = {
  setup() {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated.value) {
      router.push('/login');
    }

    return { isAuthenticated };
  },
  template: `
    <div v-if="isAuthenticated">
      <h1>Expenses</h1>
      <!-- Expense list -->
    </div>
    <div v-else>
      <p>Please log in to view expenses</p>
    </div>
  `
};

// Create Expense Component
const CreateExpense = {
  setup() {
    const { user } = useAuth();

    const canCreate = computed(() => {
      return user.value?.roles.includes('MANAGER') || false;
    });

    return { canCreate, user };
  },
  template: `
    <div v-if="canCreate">
      <h1>Create Expense</h1>
      <form @submit.prevent="onSubmit">
        <!-- Form fields -->
      </form>
    </div>
    <div v-else>
      <p>Manager access required</p>
    </div>
  `
};

// Approve Expense Component
const ApproveExpense = {
  props: ['expense'],
  setup(props) {
    const { user } = useAuth();

    const canApprove = computed(() => {
      if (!user.value) return false;

      // Managers can approve up to $5000
      if (user.value.roles.includes('MANAGER') && props.expense.amount <= 5000) {
        return true;
      }

      // Directors can approve any amount
      if (user.value.roles.includes('DIRECTOR')) {
        return true;
      }

      return false;
    });

    const approve = () => {
      // Approval logic
    };

    return { canApprove, approve };
  },
  template: `
    <button v-if="canApprove" @click="approve">
      Approve
    </button>
  `
};

// Delete Expense Component
const DeleteExpense = {
  props: ['expenseId'],
  setup() {
    const { user } = useAuth();

    const isAdmin = computed(() => {
      return user.value?.roles.includes('ADMIN') || false;
    });

    const deleteExpense = () => {
      // Delete logic
    };

    return { isAdmin, deleteExpense };
  },
  template: `
    <button v-if="isAdmin" @click="deleteExpense">
      Delete
    </button>
  `
};

// Financial Report Component
const FinancialReport = {
  setup() {
    const { user } = useAuth();

    const hasAccess = computed(() => {
      return user.value?.department === 'Finance';
    });

    return { hasAccess };
  },
  template: `
    <div v-if="hasAccess">
      <h1>Financial Report</h1>
      <!-- Report content -->
    </div>
    <div v-else>
      <p>Finance department access required</p>
    </div>
  `
};
</script>

<script lang="ts">
// Router navigation guards
export const routes = [
  {
    path: '/expenses',
    component: ExpenseList,
    beforeEnter: (to, from, next) => {
      const { isAuthenticated } = useAuth();
      if (!isAuthenticated.value) {
        next('/login');
      } else {
        next();
      }
    }
  },
  {
    path: '/expenses/create',
    component: CreateExpense,
    beforeEnter: (to, from, next) => {
      const { user } = useAuth();
      if (!user.value?.roles.includes('MANAGER')) {
        next('/unauthorized');
      } else {
        next();
      }
    }
  },
  {
    path: '/reports/financial',
    component: FinancialReport,
    beforeEnter: (to, from, next) => {
      const { user } = useAuth();
      if (user.value?.department !== 'Finance') {
        next('/unauthorized');
      } else {
        next();
      }
    }
  }
];
</script>
