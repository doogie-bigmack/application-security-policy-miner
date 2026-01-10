using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace ExpenseApp.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ExpenseController : ControllerBase
    {
        [HttpGet]
        [Authorize(Roles = "User")]
        public IActionResult GetAll()
        {
            return Ok(expenseService.GetAll());
        }

        [HttpPost]
        [Authorize(Roles = "Manager")]
        public IActionResult Create([FromBody] Expense expense)
        {
            return Ok(expenseService.Create(expense));
        }

        [HttpPut("{id}/approve")]
        [Authorize(Policy = "CanApproveExpenses")]
        public IActionResult Approve(int id)
        {
            var expense = expenseService.GetById(id);
            if (expense.Amount > 5000 && !User.IsInRole("Director"))
            {
                return Forbid("Only directors can approve expenses over $5,000");
            }
            return Ok(expenseService.Approve(id));
        }

        [HttpDelete("{id}")]
        [Authorize(Roles = "Admin")]
        public IActionResult Delete(int id)
        {
            expenseService.Delete(id);
            return NoContent();
        }

        [HttpGet("sensitive")]
        public IActionResult GetSensitiveData()
        {
            if (!User.HasClaim("Department", "Finance"))
            {
                return Forbid();
            }
            return Ok(sensitiveDataService.GetData());
        }
    }
}
