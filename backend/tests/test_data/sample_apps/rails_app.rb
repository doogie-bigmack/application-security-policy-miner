class ExpensesController < ApplicationController
  before_action :authenticate_user!
  before_action :require_manager, only: [:create]
  before_action :require_manager_or_director, only: [:approve]
  before_action :require_admin, only: [:destroy]

  # GET /api/expenses
  def index
    # All authenticated users can view expenses
    @expenses = Expense.all
    render json: @expenses
  end

  # POST /api/expenses
  def create
    # Only managers can create expenses (enforced by before_action)
    @expense = Expense.new(expense_params)

    if @expense.save
      render json: @expense, status: :created
    else
      render json: @expense.errors, status: :unprocessable_entity
    end
  end

  # PUT /api/expenses/:id/approve
  def approve
    # Managers can approve up to $5000, directors for higher
    @expense = Expense.find(params[:id])

    if @expense.amount > 5000 && !current_user.has_role?(:director)
      render json: { error: 'Director role required for amounts over $5,000' }, status: :forbidden
      return
    end

    @expense.update(approved: true)
    render json: @expense
  end

  # DELETE /api/expenses/:id
  def destroy
    # Only admins can delete (enforced by before_action)
    @expense = Expense.find(params[:id])
    @expense.destroy
    head :no_content
  end

  # GET /api/reports/financial
  def financial_report
    # Finance department only
    unless current_user.department == 'Finance'
      render json: { error: 'Finance department access required' }, status: :forbidden
      return
    end

    @report = ReportService.generate_financial_report
    render json: @report
  end

  private

  def require_manager
    unless current_user.has_role?(:manager)
      render json: { error: 'Manager role required' }, status: :forbidden
    end
  end

  def require_manager_or_director
    unless current_user.has_role?(:manager) || current_user.has_role?(:director)
      render json: { error: 'Manager or Director role required' }, status: :forbidden
    end
  end

  def require_admin
    unless current_user.has_role?(:admin)
      render json: { error: 'Admin role required' }, status: :forbidden
    end
  end

  def expense_params
    params.require(:expense).permit(:amount, :description, :category)
  end
end
