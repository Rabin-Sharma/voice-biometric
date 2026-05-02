async function loadAccount() {
  const response = await fetch("/api/account");
  if (!response.ok) {
    return null;
  }
  return response.json();
}

async function loadTransactions() {
  const response = await fetch("/api/transactions");
  if (!response.ok) {
    return [];
  }
  const data = await response.json();
  return data.transactions || [];
}

function renderAccount(account) {
  document.getElementById("user-name").textContent = account.full_name;
  document.getElementById("balance").textContent = account.balance.toLocaleString(
    undefined,
    { minimumFractionDigits: 2, maximumFractionDigits: 2 }
  );
  document.getElementById("account-number").textContent = account.account_number;
  document.getElementById("account-type").textContent = account.account_type;
  document.getElementById("member-since").textContent = account.member_since;
}

function renderTransactions(transactions) {
  const container = document.getElementById("transactions");
  if (transactions.length === 0) {
    container.innerHTML = "<p class='text-sm text-slate-400'>No transactions yet.</p>";
    return;
  }

  container.innerHTML = transactions
    .map((item) => {
      const amount = item.amount.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      const color = item.type === "credit" ? "text-emerald-400" : "text-rose-400";
      return `
        <div class="flex items-center justify-between border-b border-white/5 py-3">
          <div>
            <p class="text-sm text-slate-200">${item.description || "Transaction"}</p>
            <p class="text-xs text-slate-400">${item.created_at}</p>
          </div>
          <div class="text-right">
            <p class="text-sm font-semibold ${color}">${item.type === "credit" ? "+" : "-"}$${amount}</p>
            <p class="text-xs text-slate-400">Bal: $${item.balance_after.toFixed(2)}</p>
          </div>
        </div>
      `;
    })
    .join("");
}

async function initDashboard() {
  const account = await loadAccount();
  if (!account) {
    return;
  }
  renderAccount(account);
  const transactions = await loadTransactions();
  renderTransactions(transactions);
}

initDashboard();
