import { showToast } from "./base.js";

interface TrafficLightConfig {
  title: string;
  expression: string | null;
  green_threshold: number;
  red_threshold: number;
}

interface MetricsConfig {
  metric_column: string | null;
  metric_format: string;
}

interface GraphConfig {
  graph_type: string;
  title: string | null;
  x_column: string | null;
  x_format: string;
  y_column: string | null;
  y_format: string;
  x_secondary_column: string | null;
  x_secondary_format: string;
  data_range_mode: string | null;
  data_range_limit: number | null;
}

interface CompanySettings {
  traffic_light_config: TrafficLightConfig;
  metrics_config: MetricsConfig;
  graph_config: GraphConfig;
}

interface CompanyOut {
  company_id: number;
  company_name: string;
  plan: string;
  settings: CompanySettings;
  databases_count: number;
  managers_count: number;
  total_storage_mb: number;
  company_created_at: string;
}

let companyData: CompanyOut | null = null;

loadCompany();

async function loadCompany(): Promise<void> {
  const response = await fetch("/api/admin/company", { credentials: "include" });
  if (!response.ok) {
    showToast("Failed to load company settings.", "error");
    return;
  }

  companyData = await response.json();
  populateAll(companyData);
}

function populateAll(data: CompanyOut): void {
  // Card 1: Company Info
  const nameInput = document.getElementById("company_name") as HTMLInputElement;
  if (nameInput) nameInput.value = data.company_name;

  const planBadge = document.getElementById("plan_badge");
  if (planBadge) {
    planBadge.textContent = data.plan;
    planBadge.className = `plan-badge ${data.plan}`;
  }

  const createdAt = document.getElementById("company_created_at");
  if (createdAt) {
    createdAt.textContent = new Date(data.company_created_at).toLocaleDateString();
  }

  // Card 2: Traffic Light
  const tl = data.settings?.traffic_light_config;
  if (tl) {
    setInputValue("tl_title", tl.title ?? "");
    setInputValue("tl_expression", tl.expression ?? "");
    setInputValue("tl_green", tl.green_threshold);
    setInputValue("tl_red", tl.red_threshold);
  }

  // Card 3: Metrics
  const m = data.settings?.metrics_config;
  if (m) {
    setInputValue("metric_column", m.metric_column ?? "");
    setSelectValue("metric_format", m.metric_format);
  }

  // Card 4: Graph
  const g = data.settings?.graph_config;
  if (g) {
    setSelectValue("graph_type", g.graph_type);
    setInputValue("graph_title", g.title ?? "");
    setInputValue("graph_x_column", g.x_column ?? "");
    setSelectValue("graph_x_format", g.x_format);
    setInputValue("graph_y_column", g.y_column ?? "");
    setSelectValue("graph_y_format", g.y_format);
    setInputValue("graph_x2_column", g.x_secondary_column ?? "");
    setSelectValue("graph_x2_format", g.x_secondary_format);
    setSelectValue("graph_range_mode", g.data_range_mode ?? "all");
    setInputValue("graph_range_limit", g.data_range_limit ?? 12);
    toggleRangeLimit();
  }

  // Card 5: Limits
  const limits = document.getElementById("limit_dbs");
  if (limits) {
    const tentConfig = data.settings?.tent_config;
    const managerConfig = data.settings?.manager_config;
    const limitsData = PLAN_LIMITS[data.plan] ?? PLAN_LIMITS["free"];

    setText("limit_dbs", `${tentConfig?.current_count ?? data.databases_count}/${tentConfig?.total_allowed ?? limitsData.dbs}`);
    setText("limit_managers", `${managerConfig?.current_count ?? data.managers_count}/${managerConfig?.total_allowed ?? limitsData.managers}`);
    setText("limit_tables", `${limitsData.tables}`);
    setText("limit_storage", `${limitsData.storage_mb} MB`);

    const pillsContainer = document.getElementById("model_pills");
    if (pillsContainer) {
      pillsContainer.innerHTML = "";
      const models: string[] = limitsData.allowed_models ?? [];
      for (const model of models) {
        const pill = document.createElement("span");
        pill.className = "model-pill";
        pill.textContent = model;
        pillsContainer.appendChild(pill);
      }
    }
  }
}

const PLAN_LIMITS: Record<string, { dbs: number; managers: number; tables: number; storage_mb: number; allowed_models: string[] }> = {
  free: { dbs: 1, managers: 2, tables: 20, storage_mb: 50, allowed_models: ["llama-3.1-8b-instant"] },
  pro: { dbs: 5, managers: 10, tables: 100, storage_mb: 500, allowed_models: ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"] },
  ultra: { dbs: 20, managers: 50, tables: 1000, storage_mb: 5000, allowed_models: ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "local-llm"] },
};

// ── Save handlers ──────────────────────────────────────────────────────────────

document.querySelectorAll<HTMLButtonElement>(".settings-save").forEach((btn) => {
  btn.addEventListener("click", () => {
    const card = btn.getAttribute("data-card");
    if (card === "company") saveCompanyInfo();
    else if (card === "traffic_light") saveTrafficLight();
    else if (card === "metrics") saveMetrics();
    else if (card === "graph") saveGraph();
  });
});

async function patchSettings(body: Record<string, unknown>): Promise<boolean> {
  const response = await fetch("/api/admin/company", {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (response.ok) {
    showToast("Settings saved.", "success");
    return true;
  } else {
    const data = await response.json();
    showToast(data.detail || "Failed to save.", "error");
    return false;
  }
}

async function saveCompanyInfo(): Promise<void> {
  const name = (document.getElementById("company_name") as HTMLInputElement)?.value.trim();
  if (!name) {
    showToast("Company name cannot be empty.", "error");
    return;
  }
  const ok = await patchSettings({ company_name: name });
  if (ok && companyData) companyData.company_name = name;
}

async function saveTrafficLight(): Promise<void> {
  const body = {
    settings: {
      traffic_light_config: {
        title: getVal("tl_title"),
        expression: getVal("tl_expression") || null,
        green_threshold: getNum("tl_green"),
        red_threshold: getNum("tl_red"),
      },
    },
  };
  await patchSettings(body);
}

async function saveMetrics(): Promise<void> {
  const body = {
    settings: {
      metrics_config: {
        metric_column: getVal("metric_column") || null,
        metric_format: getSelectVal("metric_format"),
      },
    },
  };
  await patchSettings(body);
}

async function saveGraph(): Promise<void> {
  const body = {
    settings: {
      graph_config: {
        graph_type: getSelectVal("graph_type"),
        title: getVal("graph_title") || null,
        x_column: getVal("graph_x_column") || null,
        x_format: getSelectVal("graph_x_format"),
        y_column: getVal("graph_y_column") || null,
        y_format: getSelectVal("graph_y_format"),
        x_secondary_column: getVal("graph_x2_column") || null,
        x_secondary_format: getSelectVal("graph_x2_format"),
        data_range_mode: getSelectVal("graph_range_mode"),
        data_range_limit: getNum("graph_range_limit"),
      },
    },
  };
  await patchSettings(body);
}

// ── Range limit toggle ─────────────────────────────────────────────────────────

const rangeMode = document.getElementById("graph_range_mode") as HTMLSelectElement;
rangeMode?.addEventListener("change", toggleRangeLimit);

function toggleRangeLimit(): void {
  const group = document.getElementById("range_limit_group");
  const mode = (document.getElementById("graph_range_mode") as HTMLSelectElement)?.value;
  if (group) {
    group.style.display = mode === "limit" ? "flex" : "none";
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function setInputValue(id: string, value: string | number): void {
  const el = document.getElementById(id) as HTMLInputElement;
  if (el) el.value = String(value);
}

function setSelectValue(id: string, value: string): void {
  const el = document.getElementById(id) as HTMLSelectElement;
  if (el) el.value = value;
}

function setText(id: string, value: string): void {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function getVal(id: string): string {
  return (document.getElementById(id) as HTMLInputElement)?.value?.trim() ?? "";
}

function getNum(id: string): number {
  return parseFloat((document.getElementById(id) as HTMLInputElement)?.value) || 0;
}

function getSelectVal(id: string): string {
  return (document.getElementById(id) as HTMLSelectElement)?.value ?? "";
}
