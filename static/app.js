const rowsBody = document.querySelector("#rowsBody");
const headerRow = document.querySelector("#headerRow");
const addRowBtn = document.querySelector("#addRowBtn");
const generateBtn = document.querySelector("#generateBtn");
const fileInput = document.querySelector("#fileInput");
const message = document.querySelector("#message");
const notice = document.querySelector("#notice");
const progressPanel = document.querySelector("#progressPanel");
const totalProgress = document.querySelector("#totalProgress");
const currentProgress = document.querySelector("#currentProgress");
const totalProgressText = document.querySelector("#totalProgressText");
const currentProgressText = document.querySelector("#currentProgressText");
const currentProgressLabel = document.querySelector("#currentProgressLabel");
const progressDetail = document.querySelector("#progressDetail");
const tabButtons = Array.from(document.querySelectorAll(".tab"));

const modes = {
  contract: {
    label: "产品服务合同",
    itemLabel: "当前合同",
    importUrl: "/api/import",
    generateUrl: "/api/generate",
    emptyStatus: "甲方必填，开始日期必填，结束日期必填",
    notice: "日期格式：2026-7-1、2026/7/1 或 2026年7月1日。签署日期可留空。",
    fields: [
      { key: "party_a", label: "甲方名称", placeholder: "例如：杭州测试科技有限公司", required: true, message: "甲方必填" },
      { key: "start_date", label: "开始日期", placeholder: "例如：2026-7-1", required: true, message: "开始日期必填" },
      { key: "end_date", label: "结束日期", placeholder: "例如：2027-7-1", required: true, message: "结束日期必填" },
      { key: "signing_date", label: "签署日期", placeholder: "可留空，例如：2026-7-2", required: false },
    ],
  },
  storeProof: {
    label: "店铺经营证明",
    itemLabel: "当前证明",
    importUrl: "/api/store-proof/import",
    generateUrl: "/api/store-proof/generate",
    emptyStatus: "企业名、营业执照、账户名称、店铺地址、时间均必填",
    notice: "时间格式：2026-7-19、2026/7/19 或 2026年7月19日。支持导入 Excel/CSV。",
    fields: [
      { key: "enterprise_name", label: "企业名", placeholder: "例如：杭州测试科技有限公司", required: true, message: "企业名必填" },
      { key: "business_license", label: "营业执照", placeholder: "例如：91330000TEST000001", required: true, message: "营业执照必填" },
      { key: "account_name", label: "账户名称", placeholder: "例如：测试旗舰店", required: true, message: "账户名称必填" },
      { key: "shop_url", label: "店铺地址", placeholder: "例如：https://example.com/shop", required: true, message: "店铺地址必填" },
      { key: "proof_date", label: "时间", placeholder: "例如：2026-7-19", required: true, message: "时间必填" },
    ],
  },
};

let activeMode = "contract";
const modeRows = {
  contract: [],
  storeProof: [],
};

function config() {
  return modes[activeMode];
}

function emptyRow() {
  return Object.fromEntries(config().fields.map((field) => [field.key, ""]));
}

function saveActiveRows() {
  modeRows[activeMode] = allRows();
}

function renderHeader() {
  headerRow.innerHTML = config().fields.map((field) => `<th>${field.label}</th>`).join("") + "<th>状态</th><th></th>";
}

function addRow(data = emptyRow()) {
  const tr = document.createElement("tr");
  const inputs = config().fields
    .map(
      (field) =>
        `<td><input type="text" data-field="${field.key}" placeholder="${field.placeholder}"></td>`
    )
    .join("");
  tr.innerHTML = `
    ${inputs}
    <td class="status">待填写</td>
    <td><button type="button" class="remove" title="删除行">×</button></td>
  `;
  for (const [field, value] of Object.entries(data)) {
    const input = tr.querySelector(`[data-field="${field}"]`);
    if (input) input.value = value || "";
  }
  tr.querySelector(".remove").addEventListener("click", () => {
    tr.remove();
    if (!rowsBody.children.length) addRow();
  });
  tr.querySelectorAll("input").forEach((input) => input.addEventListener("input", () => validateRow(tr)));
  rowsBody.appendChild(tr);
  validateRow(tr);
}

function renderRows() {
  rowsBody.innerHTML = "";
  const rows = modeRows[activeMode].length ? modeRows[activeMode] : [emptyRow()];
  rows.forEach((row) => addRow(row));
}

function renderMode() {
  renderHeader();
  renderRows();
  notice.textContent = config().notice;
  currentProgressLabel.textContent = config().itemLabel;
  generateBtn.textContent = `生成${config().label}`;
  progressPanel.hidden = true;
  setMessage("");
  tabButtons.forEach((button) => button.classList.toggle("active", button.dataset.mode === activeMode));
}

function rowData(tr) {
  const data = {};
  tr.querySelectorAll("input").forEach((input) => {
    data[input.dataset.field] = input.value.trim();
  });
  return data;
}

function validateRow(tr) {
  const data = rowData(tr);
  const errors = config().fields
    .filter((field) => field.required && !data[field.key])
    .map((field) => field.message);
  const status = tr.querySelector(".status");
  status.textContent = errors.length ? errors.join("，") : "可生成";
  status.classList.toggle("error", errors.length > 0);
}

function allRows() {
  return Array.from(rowsBody.querySelectorAll("tr")).map(rowData);
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setGenerating(isGenerating) {
  generateBtn.disabled = isGenerating;
  addRowBtn.disabled = isGenerating;
  fileInput.disabled = isGenerating;
  tabButtons.forEach((button) => (button.disabled = isGenerating));
}

function showProgress(job) {
  progressPanel.hidden = false;
  const total = Number(job.total_percent || 0);
  const current = Number(job.current_percent || 0);
  totalProgress.value = total;
  currentProgress.value = current;
  totalProgressText.textContent = `${total}%`;
  currentProgressText.textContent = `${current}%`;
  const index = job.current_index || 0;
  const totalRows = job.total || 0;
  progressDetail.textContent = `第 ${index}/${totalRows} 份：${job.message || ""}`;
}

function downloadFrom(url) {
  const link = document.createElement("a");
  link.href = url;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function pollJob(jobId) {
  while (true) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || "无法读取生成进度");
    showProgress(job);

    if (job.status === "complete") {
      setMessage(`${config().label}已生成，正在下载。`);
      downloadFrom(job.download_url);
      return;
    }
    if (job.status === "error") {
      throw new Error(job.error || "生成失败");
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.mode === activeMode) return;
    saveActiveRows();
    activeMode = button.dataset.mode;
    renderMode();
  });
});

addRowBtn.addEventListener("click", () => addRow());

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  setMessage("正在导入文件...");
  const response = await fetch(config().importUrl, { method: "POST", body });
  const result = await response.json();
  if (!response.ok) {
    setMessage(result.error || "导入失败", true);
    return;
  }
  rowsBody.innerHTML = "";
  result.rows.forEach((row) => addRow(row));
  if (!result.rows.length) addRow();
  setMessage(`已导入 ${result.rows.length} 行。`);
  fileInput.value = "";
});

generateBtn.addEventListener("click", async () => {
  setGenerating(true);
  setMessage(`正在生成${config().label}...`);
  progressPanel.hidden = false;
  showProgress({ total_percent: 0, current_percent: 0, current_index: 1, total: allRows().length, message: "提交任务" });
  try {
    const response = await fetch(config().generateUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows: allRows() }),
    });
    const result = await response.json();

    if (!response.ok) {
      const text = (result.errors || []).map((item) => `第 ${item.row} 行：${item.error}`).join("；");
      setMessage(text || result.error || "生成失败", true);
      return;
    }

    await pollJob(result.job_id);
  } catch (error) {
    setMessage(error.message || "生成失败", true);
  } finally {
    setGenerating(false);
  }
});

renderMode();
