const rowsBody = document.querySelector("#rowsBody");
const addRowBtn = document.querySelector("#addRowBtn");
const generateBtn = document.querySelector("#generateBtn");
const fileInput = document.querySelector("#fileInput");
const message = document.querySelector("#message");
const progressPanel = document.querySelector("#progressPanel");
const totalProgress = document.querySelector("#totalProgress");
const currentProgress = document.querySelector("#currentProgress");
const totalProgressText = document.querySelector("#totalProgressText");
const currentProgressText = document.querySelector("#currentProgressText");
const progressDetail = document.querySelector("#progressDetail");

const emptyRow = {
  party_a: "",
  start_date: "",
  end_date: "",
  signing_date: "",
};

function addRow(data = emptyRow) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="text" data-field="party_a" placeholder="例如：杭州测试科技有限公司"></td>
    <td><input type="text" data-field="start_date" placeholder="例如：2026-7-1"></td>
    <td><input type="text" data-field="end_date" placeholder="例如：2027-7-1"></td>
    <td><input type="text" data-field="signing_date" placeholder="可留空，例如：2026-7-2"></td>
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

function rowData(tr) {
  const data = {};
  tr.querySelectorAll("input").forEach((input) => {
    data[input.dataset.field] = input.value.trim();
  });
  return data;
}

function validateRow(tr) {
  const data = rowData(tr);
  const errors = [];
  if (!data.party_a) errors.push("甲方必填");
  if (!data.start_date) errors.push("开始日期必填");
  if (!data.end_date) errors.push("结束日期必填");
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
      setMessage("合同已生成，正在下载。");
      downloadFrom(job.download_url);
      return;
    }
    if (job.status === "error") {
      throw new Error(job.error || "生成失败");
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
}

addRowBtn.addEventListener("click", () => addRow());

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  setMessage("正在导入文件...");
  const response = await fetch("/api/import", { method: "POST", body });
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
  setMessage("正在生成合同...");
  progressPanel.hidden = false;
  showProgress({ total_percent: 0, current_percent: 0, current_index: 1, total: allRows().length, message: "提交任务" });
  try {
    const response = await fetch("/api/generate", {
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

addRow();
