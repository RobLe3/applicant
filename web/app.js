const state = {
  matches: [],
  insights: {
    suggestions: [],
    assessment: {},
    collection: {},
    derived_filters: {},
  },
  applications: [],
  applicationsByJob: {},
  submission: {},
  feedbackEnabled: false,
  activePreset: "",
  similarityMode: "show",
  scoreView: "adjusted",
  focusMode: false,
  focusIndex: 0,
  focusScrollY: 0,
  focusIds: [],
  expandedDescriptions: {},
  profileData: {
    profile: {},
    matching: {},
    job_sources: {},
    job_filters: {},
    derived_filters: {},
    adapters: {},
  },
  committee: {
    votes: {},
    profile_review: {},
    job_review: {},
  },
  holding: {
    items: [],
    index: 0,
    currentId: null,
  },
  pending: 0,
  statusMessage: "Ready",
};

const el = {
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabPanels: document.querySelectorAll(".tab-panel"),
  cards: document.getElementById("cards"),
  search: document.getElementById("search"),
  filterReco: document.getElementById("filter-reco"),
  filterRegion: document.getElementById("filter-region"),
  filterLanguage: document.getElementById("filter-language"),
  filterAlignment: document.getElementById("filter-alignment"),
  filterVote: document.getElementById("filter-vote"),
  presetToggle: document.getElementById("preset-toggle"),
  feedbackToggle: document.getElementById("feedback-toggle"),
  similarityToggle: document.getElementById("similarity-toggle"),
  focusToggle: document.getElementById("focus-toggle"),
  sort: document.getElementById("sort"),
  group: document.getElementById("group"),
  scoreViewToggle: document.getElementById("score-view-toggle"),
  scoreHistogram: document.getElementById("score-histogram"),
  scoreTotal: document.getElementById("score-total"),
  statTotal: document.getElementById("stat-total"),
  statApply: document.getElementById("stat-apply"),
  statConsider: document.getElementById("stat-consider"),
  suggestions: document.getElementById("suggestions-list"),
  assessment: document.getElementById("assessment-summary"),
  collection: document.getElementById("collection-summary"),
  profileAnchors: document.getElementById("profile-anchors"),
  holdingCard: document.getElementById("holding-card"),
  holdingCount: document.getElementById("holding-count"),
  holdingPrev: document.getElementById("holding-prev"),
  holdingNext: document.getElementById("holding-next"),
  profileSummary: document.getElementById("profile-summary"),
  profileCompare: document.getElementById("profile-compare"),
  profileHard: document.getElementById("profile-hard"),
  profileSoft: document.getElementById("profile-soft"),
  profileWeights: document.getElementById("profile-weights"),
  committeeReview: document.getElementById("committee-review"),
  crawlConfig: document.getElementById("crawl-config"),
  crawlAts: document.getElementById("crawl-ats"),
  crawlFilters: document.getElementById("crawl-filters"),
  crawlSummary: document.getElementById("crawl-summary"),
  runCrawl: document.getElementById("run-crawl"),
  runScore: document.getElementById("run-score"),
  status: document.getElementById("status"),
  statusText: document.getElementById("status-text"),
};

function scoreText(score) {
  return Number(score || 0).toFixed(2);
}

function extractCompensation(text) {
  if (!text) {
    return "";
  }
  const currency = "(?:USD|EUR|GBP|CHF|CAD|AUD|NZD|SGD|HKD|JPY|CNY|INR|SEK|NOK|DKK|PLN|CZK|BRL|MXN|\\$|\\u20ac|\\u00a3)";
  const amount = "\\\\d{2,3}(?:[.,]\\\\d{3})*(?:\\\\s?[kK])?";
  const rangeRegex = new RegExp(
    `${currency}\\\\s*${amount}\\\\s*(?:-|to|\\\\u2013|\\\\u2014)\\\\s*(?:${currency}\\\\s*)?${amount}`,
    "i"
  );
  const singleRegex = new RegExp(`${currency}\\\\s*${amount}`, "i");
  const rangeMatch = text.match(rangeRegex);
  if (rangeMatch) {
    return rangeMatch[0].trim();
  }
  const singleMatch = text.match(singleRegex);
  return singleMatch ? singleMatch[0].trim() : "";
}

function deriveJobFacts(job) {
  const description = job.description || "";
  const title = job.title || "";
  const text = `${title}\n${description}`.toLowerCase();
  const locationText = (job.location || "").toLowerCase();

  let workplace = "";
  if (text.includes("hybrid") || locationText.includes("hybrid")) {
    workplace = "Hybrid";
  } else if (text.includes("remote") || locationText.includes("remote") || text.includes("telecommute")) {
    workplace = "Remote";
  } else if (
    text.includes("on-site") ||
    text.includes("onsite") ||
    text.includes("in-office") ||
    text.includes("in office") ||
    text.includes("office-based")
  ) {
    workplace = "On-site";
  }

  let employmentType = "";
  const employmentMap = [
    ["Full-time", ["full-time", "full time", "fulltime"]],
    ["Part-time", ["part-time", "part time", "parttime"]],
    ["Contract", ["contract", "contractor", "fixed-term", "fixed term"]],
    ["Temporary", ["temporary", "temp"]],
    ["Internship", ["intern", "internship"]],
    ["Freelance", ["freelance"]],
  ];
  employmentMap.some(([label, tokens]) => {
    if (tokens.some((token) => text.includes(token))) {
      employmentType = label;
      return true;
    }
    return false;
  });

  return {
    location: job.location || "",
    workplace,
    employment_type: employmentType,
    compensation: extractCompensation(description),
  };
}

function getJobFacts(match) {
  const job = match.job || {};
  const facts = match.job_facts && Object.keys(match.job_facts).length ? match.job_facts : deriveJobFacts(job);
  return {
    location: facts.location || job.location || "",
    workplace: facts.workplace || "",
    employment_type: facts.employment_type || "",
    compensation: facts.compensation || "",
  };
}

function clearNode(node) {
  if (!node) {
    return;
  }
  node.innerHTML = "";
}

function renderEmptyState(node, message) {
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = message;
  node.appendChild(empty);
}

function renderTagList(node, items, emptyMessage) {
  if (!node) {
    return;
  }
  clearNode(node);
  if (!items || !items.length) {
    renderEmptyState(node, emptyMessage || "No data yet.");
    return;
  }
  const tags = document.createElement("div");
  tags.className = "suggestion-tags";
  items.forEach((item) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = item;
    tags.appendChild(tag);
  });
  node.appendChild(tags);
}

function setStatus(message, busy) {
  if (!el.status || !el.statusText) {
    return;
  }
  el.statusText.textContent = message;
  el.status.classList.toggle("is-busy", Boolean(busy));
}

function beginAction(message) {
  state.pending += 1;
  state.statusMessage = message || "Working...";
  setStatus(state.statusMessage, true);
}

function endAction(message) {
  state.pending = Math.max(0, state.pending - 1);
  if (state.pending === 0) {
    const doneMessage = message || "Ready";
    state.statusMessage = doneMessage;
    setStatus(doneMessage, false);
    return;
  }
  setStatus(state.statusMessage || "Working...", true);
}

function setButtonBusy(button, busy) {
  if (!button) {
    return;
  }
  button.disabled = Boolean(busy);
}

function getApplication(jobId) {
  return state.applicationsByJob[String(jobId)] || null;
}

function formatSubmissionStatus(app) {
  if (!app) {
    return "No application package generated.";
  }
  if (app.submitted) {
    return `Submitted ${app.submitted_at || ""}`.trim();
  }
  if (app.draft_created) {
    return "Draft created (not sent)";
  }
  return "Ready for draft or form assist.";
}

async function submitApplication(payload) {
  beginAction("Preparing submission...");
  try {
    const res = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Submission failed");
    }
    await loadApplications({ silent: true });
    return data.result || {};
  } finally {
    endAction("Submission updated");
  }
}

async function saveFeedback(jobId, outcome, note) {
  beginAction("Saving feedback...");
  try {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, outcome, note }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Feedback failed");
    }
    await loadApplications({ silent: true });
    return data.entry;
  } finally {
    endAction("Feedback saved");
  }
}

async function saveTemplateOverride(jobId, roleFamily) {
  beginAction("Saving template selection...");
  try {
    const res = await fetch("/api/template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, role_family: roleFamily }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Template update failed");
    }
    if (state.profileData) {
      state.profileData.template_overrides = data.template_overrides || {};
    }
    renderCards();
    return data.template_overrides || {};
  } finally {
    endAction("Template updated");
  }
}

function formatRoleLabel(value) {
  return (value || "")
    .toString()
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeRoleFamilies(list) {
  const normalized = [];
  (list || []).forEach((item) => {
    if (!item) {
      return;
    }
    if (typeof item === "string") {
      normalized.push({ id: item, label: formatRoleLabel(item) });
      return;
    }
    if (typeof item === "object") {
      const id = item.id || item.value || "";
      if (!id) {
        return;
      }
      const label = item.label || formatRoleLabel(id);
      normalized.push({ id, label });
    }
  });
  return normalized;
}

function setActiveTab(tabName) {
  el.tabButtons.forEach((btn) => {
    const isActive = btn.dataset.tab === tabName;
    btn.classList.toggle("is-active", isActive);
  });
  el.tabPanels.forEach((panel) => {
    const isActive = panel.id === `tab-${tabName}`;
    panel.classList.toggle("is-active", isActive);
  });
}

function getVote(match) {
  return (match.decision && match.decision.vote) || "none";
}

function getAlignmentScore(match) {
  const alignment = match.alignment || {};
  const value = alignment.alignment_score;
  return typeof value === "number" ? value : 0;
}

function getScoreValue(match, view) {
  const key = view || state.scoreView || "adjusted";
  if (key === "raw") {
    return typeof match.score_raw === "number" ? match.score_raw : match.score || 0;
  }
  if (key === "preset") {
    return typeof match.score_preset === "number" ? match.score_preset : match.score || 0;
  }
  if (key === "adjusted") {
    return typeof match.score_adjusted === "number" ? match.score_adjusted : match.score || 0;
  }
  return match.score || 0;
}

function populateSelectOptions(select, options, defaultValue) {
  if (!select) {
    return;
  }
  const current = select.value || defaultValue;
  select.innerHTML = "";
  options.forEach((opt) => {
    const option = document.createElement("option");
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.value === current) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function buildRegionOptions() {
  const keywords = ((state.profileData && state.profileData.matching) || {}).region_keywords || [];
  const seen = new Set();
  const options = [{ value: "all", label: "All" }];
  const addOption = (value, label) => {
    if (!value) {
      return;
    }
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    options.push({ value, label: label || value });
  };
  keywords.forEach((item) => {
    addOption(item, item);
  });
  addOption("Remote", "Remote");
  addOption("Hybrid", "Hybrid");
  return options;
}

function buildLanguageOptions() {
  const supported = ((state.profileData && state.profileData.language) || {}).supported || [];
  const deduped = [];
  const seen = new Set();
  supported.forEach((lang) => {
    if (!lang) {
      return;
    }
    const key = lang.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    deduped.push(key);
  });
  const options = [{ value: "all", label: "All" }];
  deduped.forEach((lang) => {
    const label = lang.toUpperCase();
    options.push({ value: lang, label });
  });
  return options;
}

function refreshFilterOptions() {
  populateSelectOptions(el.filterRegion, buildRegionOptions(), "all");
  populateSelectOptions(el.filterLanguage, buildLanguageOptions(), "all");
}

function refreshPresetOptions() {
  if (!el.presetToggle) {
    return;
  }
  const scoring = (state.profileData && state.profileData.scoring) || {};
  const presets = scoring.presets || {};
  const options = [{ value: "", label: "Default" }];
  Object.entries(presets).forEach(([key, preset]) => {
    if (!key) {
      return;
    }
    const label = preset.label ? preset.label : key;
    options.push({ value: key, label });
  });
  const defaultPreset = scoring.active_preset || "";
  state.activePreset = state.activePreset || defaultPreset;
  populateSelectOptions(el.presetToggle, options, state.activePreset || "");
  state.activePreset = el.presetToggle.value;
}

function applyFilters() {
  const q = (el.search.value || "").toLowerCase();
  const reco = el.filterReco.value;
  const vote = el.filterVote.value;
  const region = el.filterRegion ? el.filterRegion.value : "all";
  const language = el.filterLanguage ? el.filterLanguage.value : "all";
  const alignmentFocus = el.filterAlignment ? el.filterAlignment.value : "all";

  return state.matches.filter((match) => {
    const job = match.job || {};
    const text = `${job.title || ""} ${job.company || ""} ${job.location || ""} ${job.description || ""}`.toLowerCase();

    if (q && !text.includes(q)) {
      return false;
    }
    if (reco === "high") {
      if (match.recommendation !== "apply" && match.recommendation !== "consider") {
        return false;
      }
    } else if (reco !== "all" && match.recommendation !== reco) {
      return false;
    }
    const jobLanguage = (job.language || "").toLowerCase();
    if (language !== "all" && jobLanguage !== language) {
      return false;
    }

    if (region !== "all") {
      const regionKey = region.toLowerCase();
      const location = (job.location || "").toLowerCase();
      const desc = (job.description || "").toLowerCase();
      const facts = getJobFacts(match);
      const workplace = (facts.workplace || "").toLowerCase();
      const isWorkplace = ["remote", "hybrid", "on-site", "onsite"].includes(regionKey);
      if (isWorkplace) {
        if (regionKey === "remote" && workplace !== "remote") {
          return false;
        }
        if (regionKey === "hybrid" && workplace !== "hybrid") {
          return false;
        }
      } else {
        const haystack = `${location} ${desc}`;
        if (!haystack.includes(regionKey)) {
          return false;
        }
      }
    }

    if (alignmentFocus !== "all") {
      const minAlignment = Number(alignmentFocus);
      if (!Number.isNaN(minAlignment) && getAlignmentScore(match) < minAlignment) {
        return false;
      }
    }

    const currentVote = getVote(match);
    if (vote === "none" && currentVote !== "none") {
      return false;
    }
    if (vote !== "all" && vote !== "none" && currentVote !== vote) {
      return false;
    }
    return true;
  });
}

function applySort(list) {
  const mode = el.sort.value;
  return [...list].sort((a, b) => {
    const jobA = a.job || {};
    const jobB = b.job || {};

    if (mode === "score") {
      return (b.score || 0) - (a.score || 0);
    }
    if (mode === "company") {
      return (jobA.company || "").localeCompare(jobB.company || "");
    }
    if (mode === "location") {
      return (jobA.location || "").localeCompare(jobB.location || "");
    }
    if (mode === "title") {
      return (jobA.title || "").localeCompare(jobB.title || "");
    }
    return 0;
  });
}

function applySimilarityMode(list) {
  const mode = state.similarityMode || "show";
  if (mode !== "collapse") {
    return list;
  }
  const seen = new Set();
  return list.filter((match) => {
    const clusterId = match.cluster_id;
    if (!clusterId) {
      return true;
    }
    if (seen.has(clusterId)) {
      return false;
    }
    seen.add(clusterId);
    return true;
  });
}

function getVisibleMatches() {
  const filtered = applyFilters();
  const sorted = applySort(filtered);
  return applySimilarityMode(sorted);
}

function updateStats() {
  const total = state.matches.length;
  const applyCount = state.matches.filter((m) => m.recommendation === "apply").length;
  const considerCount = state.matches.filter((m) => m.recommendation === "consider").length;
  el.statTotal.textContent = total;
  el.statApply.textContent = applyCount;
  el.statConsider.textContent = considerCount;
}

function escapeSelector(value) {
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(String(value));
  }
  return String(value).replace(/["\\]/g, "\\$&");
}

function clearFocusHighlight() {
  document.querySelectorAll(".card.is-focused").forEach((card) => {
    card.classList.remove("is-focused");
  });
}

function highlightFocus(scroll = true) {
  clearFocusHighlight();
  if (!state.focusMode || !state.focusIds.length) {
    return;
  }
  const jobId = state.focusIds[state.focusIndex];
  if (!jobId) {
    return;
  }
  const selector = `[data-job-id="${escapeSelector(jobId)}"]`;
  const card = el.cards ? el.cards.querySelector(selector) : null;
  if (!card) {
    return;
  }
  card.classList.add("is-focused");
  if (scroll) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function updateFocusList(visible) {
  const currentId = state.focusMode && state.focusIds.length ? state.focusIds[state.focusIndex] : null;
  state.focusIds = (visible || []).map((match) => String(match.id));
  if (!state.focusMode) {
    return;
  }
  if (currentId) {
    const nextIndex = state.focusIds.indexOf(String(currentId));
    state.focusIndex = nextIndex >= 0 ? nextIndex : 0;
  } else {
    state.focusIndex = 0;
  }
  highlightFocus();
}

function setFocusMode(enabled) {
  state.focusMode = Boolean(enabled);
  if (state.focusMode) {
    state.focusScrollY = window.scrollY;
    updateFocusList(getVisibleMatches());
    return;
  }
  clearFocusHighlight();
  if (typeof state.focusScrollY === "number") {
    window.scrollTo({ top: state.focusScrollY, behavior: "auto" });
  }
}

function focusNext() {
  if (!state.focusIds.length) {
    return;
  }
  state.focusIndex = (state.focusIndex + 1) % state.focusIds.length;
  highlightFocus();
}

function focusPrev() {
  if (!state.focusIds.length) {
    return;
  }
  state.focusIndex = (state.focusIndex - 1 + state.focusIds.length) % state.focusIds.length;
  highlightFocus();
}

async function focusVote(vote) {
  if (!state.focusIds.length) {
    return;
  }
  const jobId = state.focusIds[state.focusIndex];
  const selector = `[data-job-id="${escapeSelector(jobId)}"]`;
  const card = el.cards ? el.cards.querySelector(selector) : null;
  const note = card ? (card.querySelector("textarea") || {}).value || "" : "";
  await setVote(jobId, vote, note);
}

async function setVote(jobId, vote, note) {
  const payload = { job_id: jobId, vote, note };
  beginAction(`Saving ${vote} vote...`);
  try {
    await fetch("/api/vote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadMatches({ silent: true });
  } finally {
    endAction("Vote saved");
  }
}

function buildTemplateSelector(match) {
  const drafting = (state.profileData && state.profileData.drafting) || {};
  const families = normalizeRoleFamilies(drafting.role_families || []);
  if (!families.length) {
    return null;
  }

  const block = document.createElement("div");
  block.className = "template-select";

  const label = document.createElement("label");
  label.textContent = "Template family";

  const select = document.createElement("select");
  select.className = "template-dropdown";

  const defaultFamily = drafting.default_role_family || "";
  const defaultLabel = defaultFamily ? `Default (${formatRoleLabel(defaultFamily)})` : "Default";
  const defaultOption = document.createElement("option");
  defaultOption.value = "";
  defaultOption.textContent = defaultLabel;
  select.appendChild(defaultOption);

  families.forEach((family) => {
    const option = document.createElement("option");
    option.value = family.id;
    option.textContent = family.label;
    select.appendChild(option);
  });

  const overrides = (state.profileData && state.profileData.template_overrides) || {};
  const overrideValue = overrides[String(match.id)] || "";
  const app = getApplication(match.id);
  const appFamily = (app && app.template && app.template.family) || "";
  const selected = overrideValue || appFamily || defaultFamily || "";
  select.value = selected;

  select.addEventListener("change", async () => {
    try {
      await saveTemplateOverride(match.id, select.value);
    } catch (err) {
      window.alert(err.message || "Template update failed");
    }
  });

  block.appendChild(label);
  block.appendChild(select);
  return block;
}

function buildApplicationPreview(match) {
  const app = getApplication(match.id);
  if (!app) {
    return null;
  }

  const details = document.createElement("details");
  details.className = "preview-details";

  const summary = document.createElement("summary");
  summary.textContent = "Application preview";
  details.appendChild(summary);

  const template = (app.template && app.template.family) || "";
  const templateLabel = template ? formatRoleLabel(template) : "Default";
  const meta = document.createElement("div");
  meta.className = "preview-meta";
  meta.innerHTML = `<strong>Template:</strong> ${templateLabel}`;
  details.appendChild(meta);

  const docText = app.docx_text || app.body_draft || "";
  if (!docText) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No draft text available.";
    details.appendChild(empty);
    return details;
  }

  const prevText = app.previous_body_draft || "";
  if (prevText) {
    const diff = document.createElement("div");
    diff.className = "preview-diff";

    const current = document.createElement("div");
    current.className = "preview-col";
    const currentTitle = document.createElement("div");
    currentTitle.className = "preview-title";
    currentTitle.textContent = "Current draft";
    const currentText = document.createElement("pre");
    currentText.className = "preview-text";
    currentText.textContent = docText;
    current.appendChild(currentTitle);
    current.appendChild(currentText);

    const previous = document.createElement("div");
    previous.className = "preview-col";
    const prevTitle = document.createElement("div");
    prevTitle.className = "preview-title";
    prevTitle.textContent = "Previous draft";
    const prevTextBlock = document.createElement("pre");
    prevTextBlock.className = "preview-text";
    prevTextBlock.textContent = prevText;
    previous.appendChild(prevTitle);
    previous.appendChild(prevTextBlock);

    diff.appendChild(current);
    diff.appendChild(previous);
    details.appendChild(diff);
    return details;
  }

  const text = document.createElement("pre");
  text.className = "preview-text";
  text.textContent = docText;
  details.appendChild(text);
  return details;
}

function buildSubmissionBlock(match) {
  const block = document.createElement("div");
  block.className = "submission";

  const title = document.createElement("div");
  title.className = "submission-title";
  title.textContent = "Submission";
  block.appendChild(title);

  const statusLine = document.createElement("div");
  statusLine.className = "profile-line";

  if (!state.submission.enabled) {
    statusLine.innerHTML = "<strong>Status:</strong> Submission disabled in config.";
    block.appendChild(statusLine);
    return block;
  }

  const app = getApplication(match.id);
  statusLine.innerHTML = `<strong>Status:</strong> ${formatSubmissionStatus(app)}`;
  block.appendChild(statusLine);

  if (!app) {
    const hint = document.createElement("div");
    hint.className = "empty-state";
    hint.textContent = "Generate an application package to enable drafts.";
    block.appendChild(hint);
    return block;
  }

  const exports = app.exports || {};
  if (exports.docx || exports.pdf) {
    const exportLine = document.createElement("div");
    exportLine.className = "profile-line";
    const docxLabel = exports.docx ? exports.docx : "n/a";
    const pdfLabel = exports.pdf ? exports.pdf : "n/a";
    exportLine.innerHTML = `<strong>Exports:</strong> ${docxLabel}, ${pdfLabel}`;
    block.appendChild(exportLine);
  }

  const fields = document.createElement("div");
  fields.className = "submission-fields";

  const toInput = document.createElement("input");
  toInput.type = "email";
  toInput.placeholder = "To";
  toInput.value = app.to || "";
  fields.appendChild(toInput);

  const subjectInput = document.createElement("input");
  subjectInput.type = "text";
  subjectInput.placeholder = "Subject";
  subjectInput.value = app.subject || "";
  fields.appendChild(subjectInput);

  const bodyInput = document.createElement("textarea");
  bodyInput.rows = 6;
  bodyInput.placeholder = "Draft body";
  bodyInput.value = app.body_draft || "";
  fields.appendChild(bodyInput);

  block.appendChild(fields);

  const attachments = app.attachments || [];
  if (attachments.length) {
    const attachmentLine = document.createElement("div");
    attachmentLine.className = "profile-line";
    attachmentLine.innerHTML = `<strong>Attachments:</strong> ${attachments.join(", ")}`;
    block.appendChild(attachmentLine);
  }

  const checklist = document.createElement("div");
  checklist.className = "checklist";
  const checklistItems = [
    { id: "reviewed_posting", label: "Reviewed the posting and fit." },
    { id: "reviewed_draft", label: "Reviewed the draft text for accuracy." },
    { id: "confirm_attachments", label: "Confirmed attachments before sending." },
  ];
  const checklistState = {};

  const updateReadyState = () => {
    const ready = checklistItems.every((item) => checklistState[item.id]);
    draftBtn.disabled = !ready;
    formBtn.disabled = !ready;
    if (smtpBtn) {
      smtpBtn.disabled = !ready;
    }
  };

  checklistItems.forEach((item) => {
    checklistState[item.id] = false;
    const row = document.createElement("label");
    row.className = "checklist-item";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.addEventListener("change", () => {
      checklistState[item.id] = input.checked;
      updateReadyState();
    });
    const text = document.createElement("span");
    text.textContent = item.label;
    row.appendChild(input);
    row.appendChild(text);
    checklist.appendChild(row);
  });

  block.appendChild(checklist);

  const actions = document.createElement("div");
  actions.className = "submission-actions";

  const draftBtn = document.createElement("button");
  draftBtn.className = "action-btn";
  draftBtn.textContent = "Create .eml Draft";
  draftBtn.disabled = true;
  draftBtn.onclick = async () => {
    try {
      await submitApplication({
        job_id: match.id,
        file: app.file,
        mode: "draft",
        to: toInput.value,
        subject: subjectInput.value,
        body: bodyInput.value,
        attachments: attachments,
        checklist: checklistState,
      });
    } catch (err) {
      window.alert(err.message || "Draft failed");
    }
  };
  actions.appendChild(draftBtn);

  const formBtn = document.createElement("button");
  formBtn.className = "action-btn ghost";
  formBtn.textContent = "Form Assist";
  formBtn.disabled = true;
  const formOutput = document.createElement("pre");
  formOutput.className = "form-output";
  formOutput.style.display = "none";
  formBtn.onclick = async () => {
    try {
      const result = await submitApplication({
        job_id: match.id,
        file: app.file,
        mode: "form",
        to: toInput.value,
        subject: subjectInput.value,
        body: bodyInput.value,
        attachments: attachments,
        checklist: checklistState,
      });
      if (result && result.form) {
        formOutput.textContent = JSON.stringify(result.form, null, 2);
        formOutput.style.display = "block";
      }
    } catch (err) {
      window.alert(err.message || "Form assist failed");
    }
  };
  actions.appendChild(formBtn);

  let smtpBtn = null;
  if (state.submission.smtp && state.submission.smtp.enabled) {
    smtpBtn = document.createElement("button");
    smtpBtn.className = "action-btn danger";
    smtpBtn.textContent = "Send via SMTP";
    smtpBtn.disabled = true;
    smtpBtn.onclick = async () => {
      const confirmed = window.confirm("Send via SMTP now?");
      if (!confirmed) {
        return;
      }
      try {
        await submitApplication({
          job_id: match.id,
          file: app.file,
          mode: "smtp",
          dispatch: true,
          to: toInput.value,
          subject: subjectInput.value,
          body: bodyInput.value,
          attachments: attachments,
          checklist: checklistState,
        });
      } catch (err) {
        window.alert(err.message || "SMTP send failed");
      }
    };
    actions.appendChild(smtpBtn);
  }

  block.appendChild(actions);
  block.appendChild(formOutput);

  return block;
}

function buildFeedbackBlock(match) {
  const app = getApplication(match.id);
  if (!app) {
    return null;
  }
  if (!app.submitted && !app.feedback) {
    return null;
  }

  const block = document.createElement("div");
  block.className = "feedback";

  const title = document.createElement("div");
  title.className = "submission-title";
  title.textContent = "Outcome Feedback";
  block.appendChild(title);

  const last = app.feedback || {};
  if (last.outcome) {
    const lastLine = document.createElement("div");
    lastLine.className = "profile-line";
    lastLine.innerHTML = `<strong>Last outcome:</strong> ${last.outcome}`;
    block.appendChild(lastLine);
  }

  const select = document.createElement("select");
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select outcome";
  select.appendChild(placeholder);
  ["accepted", "interview", "rejected", "no_response"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value.replace("_", " ");
    select.appendChild(option);
  });
  if (last.outcome) {
    select.value = last.outcome;
  }

  const note = document.createElement("input");
  note.type = "text";
  note.placeholder = "Optional feedback note";
  note.value = last.note || "";

  const saveBtn = document.createElement("button");
  saveBtn.className = "action-btn";
  saveBtn.textContent = "Save Outcome";
  saveBtn.onclick = async () => {
    if (!select.value) {
      window.alert("Select an outcome first.");
      return;
    }
    try {
      await saveFeedback(match.id, select.value, note.value);
    } catch (err) {
      window.alert(err.message || "Feedback failed");
    }
  };

  const fields = document.createElement("div");
  fields.className = "submission-fields";
  fields.appendChild(select);
  fields.appendChild(note);
  block.appendChild(fields);
  block.appendChild(saveBtn);

  return block;
}

function buildCard(match) {
  const job = match.job || {};
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.jobId = match.id;

  const header = document.createElement("div");
  header.className = "card-header";

  const title = document.createElement("div");
  title.className = "card-title";
  title.textContent = job.title || "Untitled Role";

  const sub = document.createElement("div");
  sub.className = "card-sub";
  sub.textContent = `${job.company || "Unknown"} · ${job.location || "Remote"}`;

  const badges = document.createElement("div");
  badges.className = "badges";

  const scoreBadge = document.createElement("span");
  scoreBadge.className = "badge";
  scoreBadge.textContent = `Score ${scoreText(match.score)}`;

  const recoBadge = document.createElement("span");
  recoBadge.className = "badge";
  recoBadge.textContent = `Reco ${match.recommendation || "n/a"}`;

  badges.appendChild(scoreBadge);
  badges.appendChild(recoBadge);

  if (match.recommendation_reason) {
    const reasonBadge = document.createElement("span");
    reasonBadge.className = "badge";
    reasonBadge.textContent = match.recommendation_reason;
    badges.appendChild(reasonBadge);
  }

  const currentVote = getVote(match);
  if (currentVote !== "none") {
    const voteBadge = document.createElement("span");
    voteBadge.className = `badge badge-vote badge-${currentVote}`;
    voteBadge.textContent = `Vote ${currentVote}`;
    badges.appendChild(voteBadge);
  }

  const qualification = match.qualification || {};
  if (qualification.coverage !== undefined) {
    const coverageBadge = document.createElement("span");
    coverageBadge.className = "badge";
    coverageBadge.textContent = `Coverage ${scoreText(qualification.coverage)}`;
    badges.appendChild(coverageBadge);
  }

  const alignment = match.alignment || {};
  if (alignment.alignment_score !== undefined) {
    const alignBadge = document.createElement("span");
    alignBadge.className = "badge";
    alignBadge.textContent = `Align ${scoreText(alignment.alignment_score)}`;
    badges.appendChild(alignBadge);
  }

  if (match.cluster_size && match.cluster_size > 1) {
    const clusterBadge = document.createElement("span");
    clusterBadge.className = "badge";
    clusterBadge.textContent = `Similar ${match.cluster_size}`;
    badges.appendChild(clusterBadge);
  }

  if (Array.isArray(qualification.gaps) && qualification.gaps.length) {
    const gapBadge = document.createElement("span");
    gapBadge.className = "badge";
    gapBadge.textContent = `Gaps ${qualification.gaps.length}`;
    badges.appendChild(gapBadge);
  }

  header.appendChild(title);
  header.appendChild(sub);
  header.appendChild(badges);

  const score = document.createElement("div");
  score.innerHTML = `<div class="score">${scoreText(match.score)}</div><div class="score-label">Fit score</div>`;

  const facts = getJobFacts(match);
  let factsBlock = null;
  if (facts.location || facts.workplace || facts.employment_type || facts.compensation) {
    factsBlock = document.createElement("div");
    factsBlock.className = "job-facts";
    const addFact = (label, value) => {
      if (!value) {
        return;
      }
      const fact = document.createElement("div");
      fact.className = "job-fact";
      const strong = document.createElement("strong");
      strong.textContent = `${label}:`;
      const span = document.createElement("span");
      span.textContent = value;
      fact.appendChild(strong);
      fact.appendChild(span);
      factsBlock.appendChild(fact);
    };
    addFact("Location", facts.location);
    addFact("Workplace", facts.workplace);
    addFact("Employment", facts.employment_type);
    addFact("Compensation", facts.compensation);
  }

  const description = document.createElement("div");
  description.className = "note";
  const gapHint = Array.isArray(qualification.gaps) && qualification.gaps.length ? `Top gap: ${qualification.gaps[0]}` : "";
  const descriptionText = job.description || "No description available.";
  const lines = descriptionText.split(/\n+/).filter((line) => line.trim());
  const previewLines = 6;
  const isExpanded = Boolean(state.expandedDescriptions[match.id]);
  const hasMore = lines.length > previewLines;
  let previewText = descriptionText;
  if (hasMore && !isExpanded) {
    previewText = lines.slice(0, previewLines).join("\n");
  }
  if (!isExpanded && gapHint) {
    previewText = `${previewText}\n${gapHint}`;
  }
  description.textContent = isExpanded ? descriptionText : previewText;

  let toggleBtn = null;
  if (hasMore) {
    toggleBtn = document.createElement("button");
    toggleBtn.className = "action-btn ghost";
    toggleBtn.textContent = isExpanded ? "Show less" : "Show more";
    toggleBtn.onclick = () => {
      state.expandedDescriptions[match.id] = !isExpanded;
      renderCards();
    };
  }

  let requirementsBlock = null;
  const requirements = qualification.requirements || [];
  if (requirements.length) {
    const matchedCount = requirements.filter((row) => row.status === "matched").length;
    requirementsBlock = document.createElement("div");
    requirementsBlock.className = "requirements";

    const header = document.createElement("div");
    header.className = "requirement-header";
    header.innerHTML = `<strong>Prerequisites:</strong> ${matchedCount}/${requirements.length} matched`;
    requirementsBlock.appendChild(header);

    requirements.slice(0, 3).forEach((row) => {
      const item = document.createElement("div");
      item.className = "requirement-item";

      const status = document.createElement("span");
      const isMatched = row.status === "matched";
      status.className = `badge ${isMatched ? "badge-approve" : "badge-reject"} requirement-status`;
      status.textContent = isMatched ? "Matched" : "Gap";
      item.appendChild(status);

      const text = document.createElement("div");
      text.className = "requirement-text";
      const rawText = (row.requirement || "").trim();
      text.textContent = rawText.length > 160 ? `${rawText.slice(0, 160)}...` : rawText;
      item.appendChild(text);

      const matches = row.matches || [];
      if (matches.length) {
        const labels = [];
        matches.forEach((match) => {
          const label = match.label || "";
          if (label && !labels.includes(label)) {
            labels.push(label);
          }
        });
        if (labels.length) {
          const tags = document.createElement("div");
          tags.className = "suggestion-tags";
          labels.slice(0, 3).forEach((label) => {
            const tag = document.createElement("span");
            tag.className = "tag";
            tag.textContent = `Match: ${label}`;
            tags.appendChild(tag);
          });
          item.appendChild(tags);
        }
      }

      requirementsBlock.appendChild(item);
    });

    if (requirements.length > 3) {
      const more = document.createElement("div");
      more.className = "empty-state";
      more.textContent = `Showing 3 of ${requirements.length}.`;
      requirementsBlock.appendChild(more);
    }
  }

  let linkRow = null;
  if (job.url) {
    linkRow = document.createElement("div");
    linkRow.className = "card-links";
    const link = document.createElement("a");
    link.href = job.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Open posting";
    link.className = "card-link";
    linkRow.appendChild(link);
  }

  const skillOverlap = (alignment.skills && alignment.skills.overlap) || [];
  const capOverlap = (alignment.capabilities && alignment.capabilities.overlap) || [];
  const traitOverlap = (alignment.traits && alignment.traits.overlap) || [];

  let fitDetails = null;
  if (skillOverlap.length || capOverlap.length || traitOverlap.length) {
    fitDetails = document.createElement("div");
    fitDetails.className = "note";
    const detailParts = [];
    if (alignment.skills) {
      detailParts.push(
        `Skill fit P${scoreText(alignment.skills.profile_coverage)} / J${scoreText(alignment.skills.job_coverage)}`
      );
    }
    if (alignment.capabilities) {
      detailParts.push(
        `Capability fit P${scoreText(alignment.capabilities.profile_coverage)} / J${scoreText(
          alignment.capabilities.job_coverage
        )}`
      );
    }
    if (alignment.traits) {
      detailParts.push(
        `Trait fit P${scoreText(alignment.traits.profile_coverage)} / J${scoreText(alignment.traits.job_coverage)}`
      );
    }
    fitDetails.textContent = detailParts.join(" | ");

    const tagWrap = document.createElement("div");
    tagWrap.className = "suggestion-tags";
    const appendTags = (label, items) => {
      if (!items.length) {
        return;
      }
      items.slice(0, 6).forEach((item) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = `${label}: ${item}`;
        tagWrap.appendChild(tag);
      });
    };
    appendTags("Skill", skillOverlap);
    appendTags("Capability", capOverlap);
    appendTags("Trait", traitOverlap);
    if (tagWrap.childNodes.length) {
      fitDetails.appendChild(tagWrap);
    }
  }

  const note = document.createElement("textarea");
  note.placeholder = "Add a quick note or decision context";
  note.value = (match.decision && match.decision.note) || "";

  const voteRow = document.createElement("div");
  voteRow.className = "vote-row";

  const approveBtn = document.createElement("button");
  approveBtn.className = `vote-btn primary${currentVote === "approve" ? " is-active" : ""}`;
  approveBtn.textContent = "Approve";
  approveBtn.onclick = () => setVote(match.id, "approve", note.value);

  const holdBtn = document.createElement("button");
  holdBtn.className = `vote-btn secondary${currentVote === "hold" ? " is-active" : ""}`;
  holdBtn.textContent = "Hold";
  holdBtn.onclick = () => setVote(match.id, "hold", note.value);

  const rejectBtn = document.createElement("button");
  rejectBtn.className = `vote-btn danger${currentVote === "reject" ? " is-active" : ""}`;
  rejectBtn.textContent = "Reject";
  rejectBtn.onclick = () => setVote(match.id, "reject", note.value);

  voteRow.appendChild(approveBtn);
  voteRow.appendChild(holdBtn);
  voteRow.appendChild(rejectBtn);

  card.appendChild(header);
  card.appendChild(score);
  if (factsBlock) {
    card.appendChild(factsBlock);
  }
  const templateBlock = buildTemplateSelector(match);
  if (templateBlock) {
    card.appendChild(templateBlock);
  }
  card.appendChild(description);
  if (toggleBtn) {
    card.appendChild(toggleBtn);
  }
  if (requirementsBlock) {
    card.appendChild(requirementsBlock);
  }
  if (fitDetails) {
    card.appendChild(fitDetails);
  }
  if (linkRow) {
    card.appendChild(linkRow);
  }
  const previewBlock = buildApplicationPreview(match);
  if (previewBlock) {
    card.appendChild(previewBlock);
  }
  card.appendChild(note);
  card.appendChild(voteRow);

  const submissionBlock = buildSubmissionBlock(match);
  if (submissionBlock) {
    card.appendChild(submissionBlock);
  }
  const feedbackBlock = buildFeedbackBlock(match);
  if (feedbackBlock) {
    card.appendChild(feedbackBlock);
  }

  return card;
}

function renderCards() {
  const visible = getVisibleMatches();
  el.cards.innerHTML = "";
  const groupMode = el.group ? el.group.value : "none";
  el.cards.classList.toggle("grouped", groupMode === "vote" || groupMode === "alignment");

  if (groupMode === "alignment") {
    const buckets = {
      a90: [],
      a80: [],
      a70: [],
      "rest": [],
    };
    const order = [
      ["a90", "Alignment 0.90+"],
      ["a80", "Alignment 0.80+"],
      ["a70", "Alignment 0.70+"],
      ["rest", "Alignment < 0.70"],
    ];
    visible.forEach((match) => {
      const score = getAlignmentScore(match);
      if (score >= 0.9) {
        buckets.a90.push(match);
      } else if (score >= 0.8) {
        buckets.a80.push(match);
      } else if (score >= 0.7) {
        buckets.a70.push(match);
      } else {
        buckets["rest"].push(match);
      }
    });
    order.forEach(([key, label]) => {
      const items = buckets[key] || [];
      if (!items.length) {
        return;
      }
      const bucket = document.createElement("section");
      bucket.className = `bucket bucket-${key}`;

      const header = document.createElement("div");
      header.className = "bucket-title";
      header.textContent = label;

      const count = document.createElement("span");
      count.className = "bucket-count";
      count.textContent = items.length;
      header.appendChild(count);

      const grid = document.createElement("div");
      grid.className = "bucket-cards";
      items.forEach((match) => {
        grid.appendChild(buildCard(match));
      });

      bucket.appendChild(header);
      bucket.appendChild(grid);
      el.cards.appendChild(bucket);
    });
  } else if (groupMode === "vote") {
    const buckets = {
      approve: [],
      hold: [],
      reject: [],
      none: [],
    };
    const order = [
      ["approve", "Approved"],
      ["hold", "Hold"],
      ["reject", "Rejected"],
      ["none", "Not Voted"],
    ];
    visible.forEach((match) => {
      const vote = getVote(match);
      buckets[vote || "none"].push(match);
    });
    order.forEach(([key, label]) => {
      const items = buckets[key] || [];
      if (!items.length) {
        return;
      }
      const bucket = document.createElement("section");
      bucket.className = `bucket bucket-${key}`;

      const header = document.createElement("div");
      header.className = "bucket-title";
      header.textContent = label;

      const count = document.createElement("span");
      count.className = "bucket-count";
      count.textContent = items.length;
      header.appendChild(count);

      const grid = document.createElement("div");
      grid.className = "bucket-cards";
      items.forEach((match) => {
        grid.appendChild(buildCard(match));
      });

      bucket.appendChild(header);
      bucket.appendChild(grid);
      el.cards.appendChild(bucket);
    });
  } else {
    visible.forEach((match) => {
      el.cards.appendChild(buildCard(match));
    });
  }

  updateFocusList(visible);
}

function refreshHoldingQueue(options = {}) {
  const items = applySort(applyFilters().filter((match) => getVote(match) === "none"));
  const currentId = state.holding.currentId;
  state.holding.items = items;
  if (!items.length) {
    state.holding.index = 0;
    state.holding.currentId = null;
    renderHoldingQueue();
    return;
  }
  if (options.reset || !currentId) {
    state.holding.index = 0;
  } else {
    const nextIndex = items.findIndex((match) => match.id === currentId);
    state.holding.index = nextIndex >= 0 ? nextIndex : 0;
  }
  state.holding.currentId = items[state.holding.index].id;
  renderHoldingQueue();
}

function renderHoldingQueue() {
  if (!el.holdingCard || !el.holdingCount) {
    return;
  }
  clearNode(el.holdingCard);
  const items = state.holding.items || [];
  if (!items.length) {
    el.holdingCount.textContent = "Queue 0 of 0";
    renderEmptyState(el.holdingCard, "No new vacancies awaiting a vote.");
    setButtonBusy(el.holdingPrev, true);
    setButtonBusy(el.holdingNext, true);
    return;
  }
  const index = Math.min(Math.max(state.holding.index, 0), items.length - 1);
  state.holding.index = index;
  state.holding.currentId = items[index].id;
  el.holdingCount.textContent = `Queue ${index + 1} of ${items.length}`;
  setButtonBusy(el.holdingPrev, index <= 0);
  setButtonBusy(el.holdingNext, index >= items.length - 1);
  el.holdingCard.appendChild(buildCard(items[index]));
}

function shiftHolding(delta) {
  const items = state.holding.items || [];
  if (!items.length) {
    return;
  }
  const nextIndex = Math.min(Math.max(state.holding.index + delta, 0), items.length - 1);
  if (nextIndex === state.holding.index) {
    return;
  }
  state.holding.index = nextIndex;
  state.holding.currentId = items[nextIndex].id;
  renderHoldingQueue();
}

function renderSuggestions() {
  if (!el.suggestions) {
    return;
  }
  clearNode(el.suggestions);
  const suggestions = (state.insights && state.insights.suggestions) || [];
  if (!suggestions.length) {
    renderEmptyState(el.suggestions, "No suggestions yet. Run match scoring.");
    return;
  }

  suggestions.forEach((item) => {
    const row = document.createElement("div");
    row.className = "suggestion-item";

    const title = document.createElement("div");
    title.className = "suggestion-title";
    title.textContent = `${item.title || "Untitled"} · ${item.company || "Unknown"}`;

    const meta = document.createElement("div");
    meta.className = "suggestion-meta";
    const metaParts = [];
    if (item.location) {
      metaParts.push(item.location);
    }
    metaParts.push(`Score ${scoreText(item.score)}`);
    if (item.alignment !== undefined) {
      metaParts.push(`Align ${scoreText(item.alignment)}`);
    }
    metaParts.push(`Coverage ${scoreText(item.coverage)}`);
    if (item.recommendation) {
      metaParts.push(`Reco ${item.recommendation}`);
    }
    meta.textContent = metaParts.join(" | ");

    row.appendChild(title);
    row.appendChild(meta);

    if (item.url) {
      const link = document.createElement("a");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Open posting";
      link.className = "suggestion-meta";
      row.appendChild(link);
    }

    if (Array.isArray(item.top_gaps) && item.top_gaps.length) {
      const tags = document.createElement("div");
      tags.className = "suggestion-tags";
      item.top_gaps.slice(0, 3).forEach((gap) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = gap;
        tags.appendChild(tag);
      });
      row.appendChild(tags);
    }

    el.suggestions.appendChild(row);
  });
}

function renderAssessment() {
  if (!el.assessment) {
    return;
  }
  clearNode(el.assessment);
  const assessment = (state.insights && state.insights.assessment) || {};
  if (!assessment || !Object.keys(assessment).length) {
    renderEmptyState(el.assessment, "No assessment yet. Run match scoring.");
    return;
  }

  const grid = document.createElement("div");
  grid.className = "metric-grid";
  const requirements = assessment.requirements || {};
  const metrics = [
    { label: "Avg score", value: scoreText(assessment.avg_score) },
    { label: "Avg coverage", value: scoreText(assessment.avg_coverage) },
    { label: "Req coverage", value: scoreText(requirements.coverage) },
    { label: "Total jobs", value: assessment.total_jobs || 0 },
  ];

  metrics.forEach((metric) => {
    const card = document.createElement("div");
    card.className = "metric";
    const value = document.createElement("div");
    value.className = "metric-value";
    value.textContent = metric.value;
    const label = document.createElement("div");
    label.className = "metric-label";
    label.textContent = metric.label;
    card.appendChild(value);
    card.appendChild(label);
    grid.appendChild(card);
  });

  el.assessment.appendChild(grid);

  const recos = assessment.recommendations || {};
  const recoTags = document.createElement("div");
  recoTags.className = "suggestion-tags";
  ["apply", "consider", "skip"].forEach((key) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = `${key} ${recos[key] || 0}`;
    recoTags.appendChild(tag);
  });
  el.assessment.appendChild(recoTags);

  if (Array.isArray(assessment.top_gaps) && assessment.top_gaps.length) {
    const gapTags = document.createElement("div");
    gapTags.className = "suggestion-tags";
    assessment.top_gaps.slice(0, 5).forEach((gap) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = `${gap.gap} (${gap.count})`;
      gapTags.appendChild(tag);
    });
    el.assessment.appendChild(gapTags);
  }

  const weighting = assessment.skill_weighting || {};
  const tiers = [
    { key: "major", label: "Major skills" },
    { key: "median", label: "Median skills" },
    { key: "minor", label: "Minor skills" },
  ];
  tiers.forEach((tier) => {
    const items = weighting[tier.key] || [];
    if (!items.length) {
      return;
    }
    const label = document.createElement("div");
    label.className = "profile-line";
    label.innerHTML = `<strong>${tier.label}:</strong>`;
    el.assessment.appendChild(label);
    const tags = document.createElement("div");
    tags.className = "suggestion-tags";
    items.forEach((item) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      const weight = item.weight !== undefined ? scoreText(item.weight) : null;
      const type = item.type ? item.type : null;
      const parts = [item.skill || "Skill"];
      if (type) {
        parts.push(type);
      }
      if (weight !== null) {
        parts.push(weight);
      }
      tag.textContent = parts.join(" · ");
      tags.appendChild(tag);
    });
    el.assessment.appendChild(tags);
  });

  const abstractions = assessment.role_abstractions || {};
  const capabilityRows = abstractions.capabilities || [];
  const traitRows = abstractions.traits || [];
  if (capabilityRows.length || traitRows.length) {
    const label = document.createElement("div");
    label.className = "profile-line";
    label.innerHTML = "<strong>Role abstractions:</strong>";
    el.assessment.appendChild(label);
    const list = document.createElement("div");
    list.className = "bucket-cards";
    const combined = capabilityRows
      .map((item) => ({ ...item, _kind: "Capability" }))
      .concat(traitRows.map((item) => ({ ...item, _kind: "Trait" })));
    combined.forEach((item) => {
      const row = document.createElement("div");
      row.className = "suggestion-item";
      const title = document.createElement("div");
      title.className = "suggestion-title";
      const level = item.level ? item.level : "minor";
      title.textContent = `${item.label || item._kind} · ${level}`;
      const meta = document.createElement("div");
      meta.className = "suggestion-meta";
      const metaParts = [];
      if (item.weight !== undefined) {
        metaParts.push(`Weight ${scoreText(item.weight)}`);
      }
      if (Array.isArray(item.skills) && item.skills.length) {
        metaParts.push(item.skills.join(", "));
      }
      meta.textContent = metaParts.join(" | ");
      row.appendChild(title);
      row.appendChild(meta);
      list.appendChild(row);
    });
    el.assessment.appendChild(list);
  }
}

function renderCollection() {
  if (!el.collection) {
    return;
  }
  clearNode(el.collection);
  const collection = (state.insights && state.insights.collection) || {};
  if (!collection || !Object.keys(collection).length) {
    renderEmptyState(el.collection, "No collection summary yet. Run job crawl.");
    return;
  }

  const grid = document.createElement("div");
  grid.className = "metric-grid";
  const metrics = [
    { label: "Raw jobs", value: collection.raw_total || 0 },
    { label: "Normalized", value: collection.normalized_total || 0 },
    { label: "Filtered out", value: collection.filtered_out || 0 },
    { label: "ATS jobs", value: collection.ats_total || 0 },
    { label: "Manual jobs", value: collection.manual_total || 0 },
    { label: "Truncated", value: collection.truncated || 0 },
  ];

  metrics.forEach((metric) => {
    const card = document.createElement("div");
    card.className = "metric";
    const value = document.createElement("div");
    value.className = "metric-value";
    value.textContent = metric.value;
    const label = document.createElement("div");
    label.className = "metric-label";
    label.textContent = metric.label;
    card.appendChild(value);
    card.appendChild(label);
    grid.appendChild(card);
  });

  el.collection.appendChild(grid);

  if (collection.derived_filters) {
    const derived = collection.derived_filters || {};
    const line = document.createElement("div");
    line.className = "profile-line";
    if (derived.enabled) {
      const keywordCount = derived.include_keywords || 0;
      const locationCount = derived.location_allow || 0;
      line.innerHTML = `<strong>Derived filters:</strong> ${keywordCount} keywords · ${locationCount} locations`;
    } else {
      line.innerHTML = "<strong>Derived filters:</strong> Disabled";
    }
    el.collection.appendChild(line);
  }
}

function renderProfile() {
  const data = state.profileData || {};
  const profile = data.profile || {};
  const identity = profile.identity || {};
  const hardSkills = profile.hard_skills || [];
  const softSkills = profile.soft_skills || [];
  const sources = profile.source_files || [];

  if (el.profileSummary) {
    clearNode(el.profileSummary);
    if (!profile || !Object.keys(profile).length) {
      renderEmptyState(el.profileSummary, "Profile not loaded yet.");
    } else {
      const lines = [
        { label: "Name", value: identity.name || "Unknown" },
        { label: "Location", value: identity.location || "Unspecified" },
        { label: "Email", value: identity.email || "Unspecified" },
        { label: "Sources", value: sources.length || 0 },
        { label: "Experience entries", value: (profile.experience || []).length },
      ];
      lines.forEach((item) => {
        const line = document.createElement("div");
        line.className = "profile-line";
        line.innerHTML = `<strong>${item.label}:</strong> ${item.value}`;
        el.profileSummary.appendChild(line);
      });
    }
  }

  renderTagList(el.profileHard, hardSkills, "No hard skills extracted yet.");
  renderTagList(el.profileSoft, softSkills, "No soft skills extracted yet.");

  if (el.profileCompare) {
    clearNode(el.profileCompare);
    const comparison = data.comparison || {};
    const local = comparison.local || {};
    const web = comparison.web || {};
    const overlap = comparison.overlap || [];
    if (!local.total && !web.total && !overlap.length) {
      renderEmptyState(el.profileCompare, "No comparison data yet.");
    } else {
      const grid = document.createElement("div");
      grid.className = "metric-grid";
      const metrics = [
        { label: "Local skills", value: local.total || 0 },
        { label: "Web skills", value: web.total || 0 },
        { label: "Overlap", value: overlap.length || 0 },
      ];
      metrics.forEach((metric) => {
        const card = document.createElement("div");
        card.className = "metric";
        const value = document.createElement("div");
        value.className = "metric-value";
        value.textContent = metric.value;
        const label = document.createElement("div");
        label.className = "metric-label";
        label.textContent = metric.label;
        card.appendChild(value);
        card.appendChild(label);
        grid.appendChild(card);
      });
      el.profileCompare.appendChild(grid);

      const localOnly = comparison.local_only || [];
      const webOnly = comparison.web_only || [];
      if (localOnly.length) {
        const label = document.createElement("div");
        label.className = "profile-line";
        label.innerHTML = "<strong>Local-only highlights:</strong>";
        el.profileCompare.appendChild(label);
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        localOnly.slice(0, 8).forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        el.profileCompare.appendChild(tags);
      }

      if (webOnly.length) {
        const label = document.createElement("div");
        label.className = "profile-line";
        label.innerHTML = "<strong>Web-only highlights:</strong>";
        el.profileCompare.appendChild(label);
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        webOnly.slice(0, 8).forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        el.profileCompare.appendChild(tags);
      }
    }
  }

  if (el.profileWeights) {
    clearNode(el.profileWeights);
    const matching = data.matching || {};
    const weights = matching.weights || {};
    const entries = Object.entries(weights);
    if (!entries.length) {
      renderEmptyState(el.profileWeights, "No weight configuration found.");
    } else {
      const grid = document.createElement("div");
      grid.className = "metric-grid";
      entries.forEach(([key, value]) => {
        const card = document.createElement("div");
        card.className = "metric";
        const val = document.createElement("div");
        val.className = "metric-value";
        val.textContent = scoreText(value);
        const label = document.createElement("div");
        label.className = "metric-label";
        label.textContent = key;
        card.appendChild(val);
        card.appendChild(label);
        grid.appendChild(card);
      });
      el.profileWeights.appendChild(grid);

      const thresholds = [
        `apply ≥ ${matching.apply_threshold ?? "n/a"}`,
        `consider ≥ ${matching.consider_threshold ?? "n/a"}`,
        `min score ${matching.min_score ?? "n/a"}`,
        `top N ${matching.top_n ?? "n/a"}`,
      ];
      const tags = document.createElement("div");
      tags.className = "suggestion-tags";
      thresholds.forEach((item) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = item;
        tags.appendChild(tag);
      });
      el.profileWeights.appendChild(tags);
    }
  }
}

function renderProfileAnchors() {
  if (!el.profileAnchors) {
    return;
  }
  clearNode(el.profileAnchors);
  const profile = (state.profileData && state.profileData.profile) || {};
  const weighting = profile.skill_weighting || {};
  let entries = (weighting.entries || []).filter(
    (entry) => (entry.committee && entry.committee.decision) === "accept"
  );
  if (!entries.length) {
    renderEmptyState(el.profileAnchors, "No accepted profile skills yet.");
    return;
  }
  entries = entries.sort((a, b) => {
    const weightDiff = (b.weight || 0) - (a.weight || 0);
    if (weightDiff !== 0) {
      return weightDiff;
    }
    return (a.skill || "").localeCompare(b.skill || "");
  });

  const countLine = document.createElement("div");
  countLine.className = "profile-line";
  countLine.innerHTML = `<strong>Accepted:</strong> ${entries.length}`;
  el.profileAnchors.appendChild(countLine);

  const tags = document.createElement("div");
  tags.className = "suggestion-tags";
  entries.slice(0, 18).forEach((entry) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = entry.skill || "Skill";
    tags.appendChild(tag);
  });
  el.profileAnchors.appendChild(tags);

  if (entries.length > 18) {
    const extra = document.createElement("div");
    extra.className = "empty-state";
    extra.textContent = `Showing 18 of ${entries.length}.`;
    el.profileAnchors.appendChild(extra);
  }
}

function getCommitteeDecision(scope, kind, id, jobId) {
  const votes = (state.committee && state.committee.votes) || {};
  if (scope === "profile") {
    return ((votes.profile || {})[kind] || {})[id] || "";
  }
  if (scope === "job") {
    const jobVotes = ((votes.jobs || {})[jobId] || {})[kind] || {};
    return jobVotes[id] || "";
  }
  return "";
}

async function setCommitteeDecision({ scope, kind, id, jobId, decision }) {
  beginAction("Saving committee decision...");
  try {
    await fetch("/api/committee", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, kind, id, job_id: jobId, decision }),
    });
    await loadCommittee({ silent: true });
  } finally {
    endAction("Committee updated");
  }
}

function renderCommitteeButtons(scope, kind, id, jobId) {
  const row = document.createElement("div");
  row.className = "vote-row";
  const decision = getCommitteeDecision(scope, kind, id, jobId);

  const acceptBtn = document.createElement("button");
  acceptBtn.className = `vote-btn primary${decision === "accept" ? " is-active" : ""}`;
  acceptBtn.textContent = "Accept";
  acceptBtn.onclick = () => setCommitteeDecision({ scope, kind, id, jobId, decision: "accept" });

  const rejectBtn = document.createElement("button");
  rejectBtn.className = `vote-btn danger${decision === "reject" ? " is-active" : ""}`;
  rejectBtn.textContent = "Reject";
  rejectBtn.onclick = () => setCommitteeDecision({ scope, kind, id, jobId, decision: "reject" });

  row.appendChild(acceptBtn);
  row.appendChild(rejectBtn);
  return row;
}

function renderCommitteeReview() {
  if (!el.committeeReview) {
    return;
  }
  clearNode(el.committeeReview);
  const profileReview = state.committee.profile_review || {};
  const jobReview = state.committee.job_review || {};
  const hasProfile =
    (profileReview.skills || []).length ||
    (profileReview.abstractions || []).length ||
    (profileReview.emails || []).length;
  const jobItems = jobReview.jobs || [];
  if (!hasProfile && !jobItems.length) {
    renderEmptyState(el.committeeReview, "No held items. Committee is clear.");
    return;
  }

  if (hasProfile) {
    const header = document.createElement("div");
    header.className = "profile-line";
    header.innerHTML = "<strong>Profile holds:</strong>";
    el.committeeReview.appendChild(header);

    (profileReview.skills || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "suggestion-item";
      const title = document.createElement("div");
      title.className = "suggestion-title";
      title.textContent = item.skill || "Skill";
      const meta = document.createElement("div");
      meta.className = "suggestion-meta";
      meta.textContent = `${item.type || "skill"} · mentions ${item.mentions || 0}`;
      row.appendChild(title);
      row.appendChild(meta);
      row.appendChild(renderCommitteeButtons("profile", "skills", item.skill, ""));
      el.committeeReview.appendChild(row);
    });

    (profileReview.abstractions || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "suggestion-item";
      const label = item.category || item.trait || "Abstraction";
      const kind = item.category ? "capability" : "trait";
      const id = `${kind}:${label}`;
      const title = document.createElement("div");
      title.className = "suggestion-title";
      title.textContent = label;
      const meta = document.createElement("div");
      meta.className = "suggestion-meta";
      meta.textContent = `${kind} · signal ${item.total_signal || 0}`;
      row.appendChild(title);
      row.appendChild(meta);
      row.appendChild(renderCommitteeButtons("profile", "abstractions", id, ""));
      el.committeeReview.appendChild(row);
    });

    (profileReview.emails || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "suggestion-item";
      const title = document.createElement("div");
      title.className = "suggestion-title";
      title.textContent = item.email || "Email";
      const meta = document.createElement("div");
      meta.className = "suggestion-meta";
      meta.textContent = `score ${item.score || 0}`;
      row.appendChild(title);
      row.appendChild(meta);
      row.appendChild(renderCommitteeButtons("profile", "emails", item.email, ""));
      el.committeeReview.appendChild(row);
    });
  }

  if (jobItems.length) {
    const header = document.createElement("div");
    header.className = "profile-line";
    header.innerHTML = "<strong>Job holds:</strong>";
    el.committeeReview.appendChild(header);
    jobItems.forEach((job) => {
      const titleRow = document.createElement("div");
      titleRow.className = "profile-line";
      titleRow.innerHTML = `<strong>${job.title || "Job"}:</strong> ${job.company || ""}`;
      el.committeeReview.appendChild(titleRow);
      const review = job.committee_review || {};
      (review.skills || []).forEach((item) => {
        const row = document.createElement("div");
        row.className = "suggestion-item";
        const title = document.createElement("div");
        title.className = "suggestion-title";
        title.textContent = item.skill || "Skill";
        const meta = document.createElement("div");
        meta.className = "suggestion-meta";
        meta.textContent = `${item.type || "skill"} · mentions ${item.mentions || 0}`;
        row.appendChild(title);
        row.appendChild(meta);
        row.appendChild(renderCommitteeButtons("job", "skills", item.skill, job.job_id));
        el.committeeReview.appendChild(row);
      });
      (review.abstractions || []).forEach((item) => {
        const row = document.createElement("div");
        row.className = "suggestion-item";
        const label = item.category || item.trait || "Abstraction";
        const kind = item.category ? "capability" : "trait";
        const id = `${kind}:${label}`;
        const title = document.createElement("div");
        title.className = "suggestion-title";
        title.textContent = label;
        const meta = document.createElement("div");
        meta.className = "suggestion-meta";
        meta.textContent = `${kind} · signal ${item.total_signal || 0}`;
        row.appendChild(title);
        row.appendChild(meta);
        row.appendChild(renderCommitteeButtons("job", "abstractions", id, job.job_id));
        el.committeeReview.appendChild(row);
      });
    });
  }
}

function renderCrawl() {
  const sources = state.profileData.job_sources || {};
  const filters = state.profileData.job_filters || {};
  const companies = sources.ats_companies || [];
  const adapters = state.profileData.adapters || {};
  const collection = (state.insights && state.insights.collection) || {};
  const sourceCounts = new Map();
  (collection.sources || []).forEach((entry) => {
    if (!entry) {
      return;
    }
    const sourceId = entry.source_id || "unknown";
    const sourceType = entry.source_type || "unknown";
    sourceCounts.set(`${sourceType}:${sourceId}`, entry.count || 0);
  });

  if (el.crawlConfig) {
    clearNode(el.crawlConfig);
    if (!Object.keys(sources).length) {
      renderEmptyState(el.crawlConfig, "No job source configuration found.");
    } else {
      const jobPages = sources.job_pages || [];
      const lines = [
        { label: "Manual files", value: sources.use_manual_files ? "Enabled" : "Disabled" },
        { label: "ATS", value: sources.use_ats ? "Enabled" : "Disabled" },
        { label: "Job pages", value: jobPages.length },
        { label: "Max per company", value: sources.max_per_company ?? 0 },
        { label: "Max total", value: sources.max_total ?? 0 },
        { label: "Fetch timeout", value: `${sources.fetch_timeout_seconds ?? 10}s` },
      ];
      lines.forEach((item) => {
        const line = document.createElement("div");
        line.className = "profile-line";
        line.innerHTML = `<strong>${item.label}:</strong> ${item.value}`;
        el.crawlConfig.appendChild(line);
      });
    }
  }

  if (el.crawlAts) {
    clearNode(el.crawlAts);
    const rows = [];
    const getHost = (value) => {
      try {
        return new URL(value).hostname;
      } catch (err) {
        return "";
      }
    };

    companies.forEach((company) => {
      const name = company.company || company.name || company.board || company.slug || "ATS Company";
      const slug = company.board || company.slug || "";
      const provider = company.provider || "ats";
      const sourceId = `${provider}:${slug}`.replace(/:$/, "");
      const count = sourceCounts.get(`ats:${sourceId}`) || 0;
      const meta = ["ats", sourceId, `count ${count}`].filter(Boolean).join(" · ");
      rows.push({ label: name, meta: meta || "ats" });
    });

    if (sources.use_manual_files) {
      const count = sourceCounts.get("manual:manual") || 0;
      rows.push({ label: "Manual files", meta: `manual · manual · count ${count}` });
    }

    const jobPages = sources.job_pages || [];
    if (sources.use_job_pages && jobPages.length) {
      const count = sourceCounts.get("job_page:job_page") || 0;
      rows.push({ label: "Job pages", meta: `job_page · job_page · count ${count}` });
    }

    Object.entries(adapters).forEach(([name, cfg]) => {
      if (!cfg || typeof cfg !== "object") {
        return;
      }
      const enabled = cfg.enabled !== false;
      const status = enabled ? "enabled" : "disabled";
      const feeds = Array.isArray(cfg.feeds) ? cfg.feeds : [];
      if (feeds.length) {
        feeds.forEach((feed) => {
          const label = feed.company || feed.name || feed.source_id || name;
          const host = getHost(feed.feed_url || "");
          const metaParts = ["rss", status];
          if (feed.intent_label) {
            metaParts.push(feed.intent_label);
          }
          if (host) {
            metaParts.push(host);
          }
          const sourceId = feed.source_id || name;
          const count = sourceCounts.get(`rss:${sourceId}`) || 0;
          metaParts.push(sourceId, `count ${count}`);
          rows.push({ label, meta: metaParts.join(" · ") });
        });
      } else {
        const label = name;
        const metaParts = ["adapter", status];
        if (cfg.source_path) {
          const parts = cfg.source_path.split("/");
          metaParts.push(parts[parts.length - 1]);
        }
        const sourceId = name;
        const count = sourceCounts.get(`adapter:${sourceId}`) || 0;
        metaParts.push(sourceId, `count ${count}`);
        rows.push({ label, meta: metaParts.join(" · ") });
      }
    });

    if (!rows.length) {
      renderEmptyState(el.crawlAts, "No sources configured.");
    } else {
      rows.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "suggestion-item";
        const title = document.createElement("div");
        title.className = "suggestion-title";
        title.textContent = entry.label;
        const meta = document.createElement("div");
        meta.className = "suggestion-meta";
        meta.textContent = entry.meta;
        row.appendChild(title);
        row.appendChild(meta);
        el.crawlAts.appendChild(row);
      });
    }
  }

  if (el.crawlFilters) {
    clearNode(el.crawlFilters);
    const include = filters.include_keywords || [];
    const exclude = filters.exclude_keywords || [];
    const locationAllow = filters.location_allow || [];
    const locationBlock = filters.location_block || [];
    const derived =
      (state.insights && state.insights.derived_filters) ||
      (state.profileData && state.profileData.derived_filters) ||
      {};
    const derivedFilters = derived.derived || derived || {};
    const derivedInclude = derivedFilters.include_keywords || [];
    const derivedLocationAllow = derivedFilters.location_allow || [];
    if (!include.length && !exclude.length && !locationAllow.length && !locationBlock.length) {
      renderEmptyState(el.crawlFilters, "No filters configured.");
    } else {
      const includeBlock = document.createElement("div");
      includeBlock.className = "filter-block";
      const includeLabel = document.createElement("div");
      includeLabel.className = "profile-line";
      includeLabel.innerHTML = "<strong>Include:</strong>";
      includeBlock.appendChild(includeLabel);
      if (include.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        include.forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        includeBlock.appendChild(tags);
      } else {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No include keywords.";
        includeBlock.appendChild(empty);
      }
      el.crawlFilters.appendChild(includeBlock);

      const excludeBlock = document.createElement("div");
      excludeBlock.className = "filter-block";
      const excludeLabel = document.createElement("div");
      excludeLabel.className = "profile-line";
      excludeLabel.innerHTML = "<strong>Exclude:</strong>";
      excludeBlock.appendChild(excludeLabel);
      if (exclude.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        exclude.forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        excludeBlock.appendChild(tags);
      } else {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No exclude keywords.";
        excludeBlock.appendChild(empty);
      }
      el.crawlFilters.appendChild(excludeBlock);

      const locationBlockEl = document.createElement("div");
      locationBlockEl.className = "filter-block";
      const locationLabel = document.createElement("div");
      locationLabel.className = "profile-line";
      locationLabel.innerHTML = "<strong>Location allow:</strong>";
      locationBlockEl.appendChild(locationLabel);
      if (locationAllow.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        locationAllow.forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        locationBlockEl.appendChild(tags);
      } else {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No location allow list.";
        locationBlockEl.appendChild(empty);
      }
      el.crawlFilters.appendChild(locationBlockEl);

      const locationBlockList = document.createElement("div");
      locationBlockList.className = "filter-block";
      const blockLabel = document.createElement("div");
      blockLabel.className = "profile-line";
      blockLabel.innerHTML = "<strong>Location block:</strong>";
      locationBlockList.appendChild(blockLabel);
      if (locationBlock.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        locationBlock.forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        locationBlockList.appendChild(tags);
      } else {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No location block list.";
        locationBlockList.appendChild(empty);
      }
      el.crawlFilters.appendChild(locationBlockList);
    }

    const derivedBlock = document.createElement("div");
    derivedBlock.className = "filter-block";
    const derivedLabel = document.createElement("div");
    derivedLabel.className = "profile-line";
    derivedLabel.innerHTML = "<strong>Derived (profile-based):</strong>";
    derivedBlock.appendChild(derivedLabel);
    if (!derivedInclude.length && !derivedLocationAllow.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No derived filters yet.";
      derivedBlock.appendChild(empty);
    } else {
      const includeLine = document.createElement("div");
      includeLine.className = "profile-line";
      includeLine.innerHTML = `<strong>Include:</strong> ${derivedInclude.length}`;
      derivedBlock.appendChild(includeLine);
      if (derivedInclude.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        derivedInclude.slice(0, 12).forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        derivedBlock.appendChild(tags);
      }
      const locationLine = document.createElement("div");
      locationLine.className = "profile-line";
      locationLine.innerHTML = `<strong>Location allow:</strong> ${derivedLocationAllow.length}`;
      derivedBlock.appendChild(locationLine);
      if (derivedLocationAllow.length) {
        const tags = document.createElement("div");
        tags.className = "suggestion-tags";
        derivedLocationAllow.slice(0, 12).forEach((item) => {
          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = item;
          tags.appendChild(tag);
        });
        derivedBlock.appendChild(tags);
      }
    }
    el.crawlFilters.appendChild(derivedBlock);
  }

  if (el.crawlSummary) {
    clearNode(el.crawlSummary);
    const summary = state.insights.collection || {};
    if (!summary || !Object.keys(summary).length) {
      renderEmptyState(el.crawlSummary, "No crawl summary yet.");
    } else {
      const grid = document.createElement("div");
      grid.className = "metric-grid";
      const metrics = [
        { label: "Raw jobs", value: summary.raw_total || 0 },
        { label: "Normalized", value: summary.normalized_total || 0 },
        { label: "Filtered out", value: summary.filtered_out || 0 },
        { label: "ATS jobs", value: summary.ats_total || 0 },
        { label: "Manual jobs", value: summary.manual_total || 0 },
        { label: "Job pages", value: summary.job_page_total || 0 },
        { label: "Truncated", value: summary.truncated || 0 },
      ];
      metrics.forEach((metric) => {
        const card = document.createElement("div");
        card.className = "metric";
        const value = document.createElement("div");
        value.className = "metric-value";
        value.textContent = metric.value;
        const label = document.createElement("div");
        label.className = "metric-label";
        label.textContent = metric.label;
        card.appendChild(value);
        card.appendChild(label);
        grid.appendChild(card);
      });
      el.crawlSummary.appendChild(grid);
      if (summary.generated_at) {
        const line = document.createElement("div");
        line.className = "profile-line";
        line.innerHTML = `<strong>Generated:</strong> ${summary.generated_at}`;
        el.crawlSummary.appendChild(line);
      }
    }
  }
}

function renderInsights() {
  renderScoreDistribution();
  renderSuggestions();
  renderAssessment();
  renderCollection();
  renderCrawl();
}

function renderScoreDistribution() {
  if (!el.scoreHistogram || !el.scoreTotal) {
    return;
  }
  clearNode(el.scoreHistogram);
  const matches = state.matches || [];
  el.scoreTotal.textContent = `Total jobs: ${matches.length}`;
  if (!matches.length) {
    renderEmptyState(el.scoreHistogram, "No scores yet.");
    return;
  }
  const buckets = [
    { label: "<0.60", min: 0.0, max: 0.6 },
    { label: "0.60-0.70", min: 0.6, max: 0.7 },
    { label: "0.70-0.80", min: 0.7, max: 0.8 },
    { label: "0.80-0.90", min: 0.8, max: 0.9 },
    { label: "0.90-1.00", min: 0.9, max: 1.01 },
  ];
  const counts = buckets.map(() => 0);
  matches.forEach((match) => {
    const value = getScoreValue(match, state.scoreView);
    const score = typeof value === "number" ? value : 0;
    const index = buckets.findIndex((bucket) => score >= bucket.min && score < bucket.max);
    if (index >= 0) {
      counts[index] += 1;
    }
  });
  const maxCount = Math.max(...counts, 1);
  buckets.forEach((bucket, idx) => {
    const count = counts[idx];
    const wrap = document.createElement("div");
    wrap.className = "histogram-bar";
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max(10, (count / maxCount) * 80)}px`;
    const label = document.createElement("span");
    label.textContent = bucket.label;
    const countLabel = document.createElement("strong");
    countLabel.textContent = count;
    wrap.appendChild(countLabel);
    wrap.appendChild(bar);
    wrap.appendChild(label);
    el.scoreHistogram.appendChild(wrap);
  });
}

async function loadMatches(options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    beginAction("Loading matches...");
  }
  try {
    const res = await fetch("/api/matches");
    const data = await res.json();
    state.matches = data.matches || [];
    updateStats();
    renderCards();
    refreshHoldingQueue({ preserve: true });
  } finally {
    if (!silent) {
      endAction("Matches updated");
    }
  }
}

async function loadInsights(options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    beginAction("Loading insights...");
  }
  try {
    const res = await fetch("/api/insights");
    const data = await res.json();
    state.insights = data || {};
    renderInsights();
    renderCrawl();
  } finally {
    if (!silent) {
      endAction("Insights updated");
    }
  }
}

async function loadProfile(options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    beginAction("Loading profile...");
  }
  try {
    const res = await fetch("/api/profile");
    const data = await res.json();
    state.profileData = data || {};
    renderProfile();
    renderCrawl();
    renderProfileAnchors();
    renderCards();
    refreshFilterOptions();
    refreshPresetOptions();
  } finally {
    if (!silent) {
      endAction("Profile updated");
    }
  }
}

async function loadCommittee(options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    beginAction("Loading committee review...");
  }
  try {
    const res = await fetch("/api/committee");
    const data = await res.json();
    state.committee = data || {};
    renderCommitteeReview();
  } finally {
    if (!silent) {
      endAction("Committee updated");
    }
  }
}

async function loadApplications(options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    beginAction("Loading applications...");
  }
  try {
    const res = await fetch("/api/applications");
    const data = await res.json();
    state.applications = data.applications || [];
    state.submission = data.submission || {};
    state.applicationsByJob = {};
    state.applications.forEach((app) => {
      if (app.job_id !== undefined && app.job_id !== null) {
        state.applicationsByJob[String(app.job_id)] = app;
      }
    });
    renderCards();
  } finally {
    if (!silent) {
      endAction("Applications updated");
    }
  }
}

async function runCrawl() {
  beginAction("Running job crawl...");
  setButtonBusy(el.runCrawl, true);
  setButtonBusy(el.runScore, true);
  try {
    const res = await fetch("/api/crawl", { method: "POST" });
    const data = await res.json();
    if (data && data.summary) {
      state.insights.collection = data.summary;
      renderCollection();
      renderCrawl();
    }
    await loadInsights({ silent: true });
  } finally {
    setButtonBusy(el.runCrawl, false);
    setButtonBusy(el.runScore, false);
    endAction("Crawl complete");
  }
}

async function runScore() {
  beginAction("Refreshing scores...");
  setButtonBusy(el.runCrawl, true);
  setButtonBusy(el.runScore, true);
  try {
    await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback_enabled: state.feedbackEnabled, preset: state.activePreset }),
    });
    await Promise.all([loadMatches({ silent: true }), loadInsights({ silent: true }), loadCommittee({ silent: true })]);
  } finally {
    setButtonBusy(el.runCrawl, false);
    setButtonBusy(el.runScore, false);
    endAction("Scores refreshed");
  }
}

async function init() {
  beginAction("Loading dashboard...");
  try {
    await Promise.all([
      loadMatches({ silent: true }),
      loadInsights({ silent: true }),
      loadProfile({ silent: true }),
      loadCommittee({ silent: true }),
      loadApplications({ silent: true }),
    ]);
  } finally {
    endAction("Dashboard ready");
  }
}

[el.search, el.filterReco, el.filterRegion, el.filterLanguage, el.filterAlignment, el.filterVote, el.sort, el.group, el.similarityToggle]
  .filter(Boolean)
  .forEach((input) => {
  input.addEventListener("input", () => {
    renderCards();
    refreshHoldingQueue({ preserve: true });
  });
});

if (el.feedbackToggle) {
  state.feedbackEnabled = el.feedbackToggle.value === "on";
  el.feedbackToggle.addEventListener("change", () => {
    state.feedbackEnabled = el.feedbackToggle.value === "on";
  });
}

if (el.presetToggle) {
  el.presetToggle.addEventListener("change", () => {
    state.activePreset = el.presetToggle.value;
    runScore();
  });
}

if (el.similarityToggle) {
  state.similarityMode = el.similarityToggle.value;
  el.similarityToggle.addEventListener("change", () => {
    state.similarityMode = el.similarityToggle.value;
    renderCards();
    refreshHoldingQueue({ preserve: true });
  });
}

if (el.scoreViewToggle) {
  state.scoreView = el.scoreViewToggle.value;
  el.scoreViewToggle.addEventListener("change", () => {
    state.scoreView = el.scoreViewToggle.value;
    renderScoreDistribution();
  });
}

if (el.focusToggle) {
  state.focusMode = el.focusToggle.value === "on";
  el.focusToggle.addEventListener("change", () => {
    setFocusMode(el.focusToggle.value === "on");
  });
}

document.addEventListener("keydown", (event) => {
  if (!state.focusMode) {
    return;
  }
  const tagName = (event.target && event.target.tagName) || "";
  if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) {
    return;
  }
  const reviewPanel = document.getElementById("tab-review");
  if (!reviewPanel || !reviewPanel.classList.contains("is-active")) {
    return;
  }
  const key = event.key;
  if (key === "ArrowDown" || key === "ArrowRight") {
    event.preventDefault();
    focusNext();
  } else if (key === "ArrowUp" || key === "ArrowLeft") {
    event.preventDefault();
    focusPrev();
  } else if (key === "Enter") {
    event.preventDefault();
    focusVote("approve");
  } else if (key === " " || key === "Spacebar") {
    event.preventDefault();
    focusVote("hold");
  } else if (key === "Escape") {
    event.preventDefault();
    if (el.focusToggle) {
      el.focusToggle.value = "off";
    }
    setFocusMode(false);
  }
});

el.tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    setActiveTab(btn.dataset.tab);
  });
});

if (el.runCrawl) {
  el.runCrawl.addEventListener("click", runCrawl);
}

if (el.runScore) {
  el.runScore.addEventListener("click", runScore);
}

if (el.holdingPrev) {
  el.holdingPrev.addEventListener("click", () => shiftHolding(-1));
}

if (el.holdingNext) {
  el.holdingNext.addEventListener("click", () => shiftHolding(1));
}

init();
