/**
 * Salamandra Web Interface Application Logic
 * Comprehensive Multi-Agent Investigation, Interactive Directory & History Navigation
 */

document.addEventListener("DOMContentLoaded", () => {
  // =========================================================================
  // DOM ELEMENT REFERENCES
  // =========================================================================

  // Navigation
  const navBtns = document.querySelectorAll(".app-navbar .nav-btn");
  const viewPanes = document.querySelectorAll(".view-pane");
  const navHistoryBadge = document.getElementById("nav-history-badge");
  const navDirBadge = document.getElementById("nav-dir-badge");
  const backToHistoryBtn = document.getElementById("back-to-history-btn");

  // Query Form & Pipeline
  const newsForm = document.getElementById("news-investigate-form");
  const newsInput = document.getElementById("news-url-input");
  const submitBtn = document.getElementById("analyze-btn");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");
  const pipelineTracker = document.getElementById("pipeline-tracker");

  // Report View
  const reportContainer = document.getElementById("report-markdown-container");
  const reportToolbar = document.getElementById("report-toolbar");
  const reportMetaInfo = document.getElementById("report-meta-info");
  const copyReportBtn = document.getElementById("copy-report-btn");

  // History Elements
  const historySearchInput = document.getElementById("history-search-input");
  const historyDateStart = document.getElementById("history-date-start");
  const historyDateEnd = document.getElementById("history-date-end");
  const clearHistoryFiltersBtn = document.getElementById("clear-history-filters-btn");
  const refreshHistoryBtn = document.getElementById("refresh-history-btn");
  const datePresetPills = document.querySelectorAll(".date-preset-pill");
  const historyTableBody = document.getElementById("history-table-body");

  // Directory Elements
  const filterJurisdiction = document.getElementById("filter-jurisdiction");
  const filterAgency = document.getElementById("filter-agency");
  const filterStatus = document.getElementById("filter-status");
  const dirSearchInput = document.getElementById("dir-search-input");
  const clearDirFiltersBtn = document.getElementById("clear-dir-filters-btn");
  const sectorPills = document.querySelectorAll(".sector-pill");
  const dirCountBadge = document.getElementById("dir-count-badge");
  const dirCardsContainer = document.getElementById("directory-cards-container");
  const dirTableContainer = document.getElementById("directory-table-container");
  const dirTableBody = document.getElementById("directory-table-body");
  const viewCardsBtn = document.getElementById("view-cards-btn");
  const viewTableBtn = document.getElementById("view-table-btn");

  // Ledger Elements
  const ledgerContainer = document.getElementById("ledger-cards-container");
  const ledgerStatusBadge = document.getElementById("ledger-status-badge");

  // Modal Elements
  const dossierModal = document.getElementById("dossier-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalCloseBottomBtn = document.getElementById("modal-close-bottom-btn");
  const modalCopyMdBtn = document.getElementById("modal-copy-md-btn");
  const modalOperatorBadge = document.getElementById("modal-operator-badge");
  const modalOperatorName = document.getElementById("modal-operator-name");
  const modalOperatorMeta = document.getElementById("modal-operator-meta");
  const modalBodyContent = document.getElementById("modal-body-content");

  // =========================================================================
  // APPLICATION STATE
  // =========================================================================
  let currentReportRaw = "";
  let activeDossierMarkdown = "";
  let activeView = "view-new-query";
  let historySearchDebounce = null;
  let dirSearchDebounce = null;
  let activeDatePreset = "all";
  let activeSectorFilter = "todos";

  // Map view IDs to hash fragments
  const viewHashMapping = {
    "view-new-query": "nueva-consulta",
    "view-history": "historial",
    "view-directory": "directorio",
    "view-report": "informe",
    "view-ledger": "ledger"
  };

  const hashViewMapping = {
    "nueva-consulta": "view-new-query",
    "historial": "view-history",
    "directorio": "view-directory",
    "informe": "view-report",
    "ledger": "view-ledger"
  };

  // =========================================================================
  // NAVIGATION CONTROLLER
  // =========================================================================
  function switchView(targetViewId, updateHash = true) {
    if (!targetViewId) return;

    activeView = targetViewId;

    // Update navbar active states
    navBtns.forEach(btn => {
      const isMatch = btn.getAttribute("data-view") === targetViewId;
      btn.classList.toggle("active", isMatch);
    });

    // Update view panes
    viewPanes.forEach(pane => {
      const isMatch = pane.id === targetViewId;
      pane.classList.toggle("active", isMatch);
    });

    // Update URL Hash
    if (updateHash && viewHashMapping[targetViewId]) {
      window.location.hash = viewHashMapping[targetViewId];
    }

    // Trigger data refreshes on tab activation
    if (targetViewId === "view-history") {
      loadHistory();
    } else if (targetViewId === "view-directory") {
      loadDirectory();
    } else if (targetViewId === "view-ledger") {
      loadLedger();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Handle Navbar clicks
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const viewId = btn.getAttribute("data-view");
      switchView(viewId);
    });
  });

  // Handle "Volver al Historial" from Report View
  if (backToHistoryBtn) {
    backToHistoryBtn.addEventListener("click", () => {
      switchView("view-history");
    });
  }

  // Handle URL hash routing
  function handleHashChange() {
    const hash = window.location.hash.replace("#", "").trim();
    if (hash && hashViewMapping[hash]) {
      switchView(hashViewMapping[hash], false);
    } else {
      switchView("view-new-query", false);
    }
  }

  window.addEventListener("hashchange", handleHashChange);

  // =========================================================================
  // LIVE INVESTIGATION QUERY FORM & PIPELINE ANIMATION
  // =========================================================================
  const pipelineSteps = [
    { id: "step-extract", delay: 1000 },
    { id: "step-gov-scout", delay: 2800 },
    { id: "step-corroborate", delay: 5000 },
    { id: "step-source", delay: 7500 },
    { id: "step-osint", delay: 10000 },
    { id: "step-bias", delay: 12500 },
    { id: "step-orchestrator", delay: 15000 }
  ];

  let stepTimeouts = [];

  function resetPipeline() {
    stepTimeouts.forEach(t => clearTimeout(t));
    stepTimeouts = [];
    pipelineSteps.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) {
        el.className = "step-card";
        const status = el.querySelector(".step-status");
        if (status) status.textContent = "Espera";
      }
    });
  }

  function animatePipelineSteps() {
    pipelineSteps.forEach((s, idx) => {
      const t = setTimeout(() => {
        const el = document.getElementById(s.id);
        if (el) {
          el.className = "step-card running";
          const status = el.querySelector(".step-status");
          if (status) status.textContent = "Ejecutando...";
        }
        if (idx > 0) {
          const prev = document.getElementById(pipelineSteps[idx - 1].id);
          if (prev) {
            prev.className = "step-card completed";
            const prevStatus = prev.querySelector(".step-status");
            if (prevStatus) prevStatus.textContent = "✓ Listo";
          }
        }
      }, s.delay);
      stepTimeouts.push(t);
    });
  }

  function completePipeline() {
    stepTimeouts.forEach(t => clearTimeout(t));
    pipelineSteps.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) {
        el.className = "step-card completed";
        const status = el.querySelector(".step-status");
        if (status) status.textContent = "✓ Completado";
      }
    });
  }

  function setLoading(isLoading) {
    if (!submitBtn) return;
    submitBtn.disabled = isLoading;
    if (isLoading) {
      if (btnText) btnText.textContent = "Investigando en Red A2A...";
      if (btnSpinner) btnSpinner.style.display = "inline-block";
    } else {
      if (btnText) btnText.textContent = "Desmantelar Sesgo";
      if (btnSpinner) btnSpinner.style.display = "none";
    }
  }

  if (newsForm) {
    newsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const query = newsInput.value.trim();
      if (!query) return;

      setLoading(true);
      resetPipeline();
      if (pipelineTracker) {
        pipelineTracker.classList.add("active");
        pipelineTracker.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      animatePipelineSteps();

      try {
        const response = await fetch("/api/investigate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errDetail = errorData.error || `${response.status} ${response.statusText}`;
          throw new Error(errDetail);
        }

        const data = await response.json();
        completePipeline();

        // Populate and display Report
        currentReportRaw = data.report || "No se generó reporte.";
        if (reportContainer) {
          reportContainer.innerHTML = renderMarkdown(currentReportRaw);
        }

        if (reportToolbar && reportMetaInfo) {
          reportMetaInfo.innerHTML = `<span>Consulta auditada: <strong>${escapeHtml(query)}</strong></span>`;
          reportToolbar.style.display = "flex";
        }

        // Switch to Report View
        switchView("view-report");

        // Background updates
        loadHistory();
        loadDirectory();
        loadLedger();

      } catch (err) {
        alert(`Error al investigar la noticia: ${err.message}`);
        resetPipeline();
      } finally {
        setLoading(false);
      }
    });
  }

  // Copy report button
  if (copyReportBtn) {
    copyReportBtn.addEventListener("click", () => {
      if (!currentReportRaw) return;
      navigator.clipboard.writeText(currentReportRaw).then(() => {
        const origText = copyReportBtn.textContent;
        copyReportBtn.textContent = "✓ ¡Copiado!";
        setTimeout(() => { copyReportBtn.textContent = origText; }, 2000);
      });
    });
  }

  // =========================================================================
  // HISTORIAL DE REPORTES: Filters, Table View & Actions
  // =========================================================================
  function getHistoryDateRange() {
    let startDate = "";
    let endDate = "";

    const now = new Date();
    const formatYMD = (d) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    };

    if (activeDatePreset === "today") {
      startDate = formatYMD(now);
      endDate = formatYMD(now);
    } else if (activeDatePreset === "7d") {
      const past = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      startDate = formatYMD(past);
      endDate = formatYMD(now);
    } else if (activeDatePreset === "30d") {
      const past = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      startDate = formatYMD(past);
      endDate = formatYMD(now);
    } else if (activeDatePreset === "custom") {
      if (historyDateStart) startDate = historyDateStart.value;
      if (historyDateEnd) endDate = historyDateEnd.value;
    }

    return { startDate, endDate };
  }

  async function loadHistory() {
    if (!historyTableBody) return;

    try {
      historyTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 2.5rem;" class="text-dim">
            <span class="spinner" style="margin-right: 0.5rem;"></span> Cargando historial de reportes...
          </td>
        </tr>
      `;

      const { startDate, endDate } = getHistoryDateRange();
      const queryParam = historySearchInput ? historySearchInput.value.trim() : "";

      const params = new URLSearchParams();
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      if (queryParam) params.set("q", queryParam);

      const url = `/api/investigations?${params.toString()}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Error consultando investigaciones");
      const list = await res.json();

      // Update badge
      if (navHistoryBadge) {
        navHistoryBadge.textContent = Array.isArray(list) ? list.length : "0";
      }

      if (!Array.isArray(list) || list.length === 0) {
        historyTableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; padding: 3rem;" class="text-dim">
              <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">📋</div>
              <strong style="color: #fff; font-size: 1rem;">No se encontraron reportes con los filtros seleccionados</strong>
              <p style="font-size: 0.85rem; margin-top: 0.4rem;">
                Prueba cambiando el rango de fechas o inicia una <a href="#nueva-consulta" onclick="switchView('view-new-query'); return false;" style="color: var(--accent-emerald);">nueva consulta</a>.
              </p>
            </td>
          </tr>
        `;
        return;
      }

      // Render table rows
      historyTableBody.innerHTML = list.map(item => {
        const dateFormatted = item.created_at ? new Date(item.created_at).toLocaleString() : "Reciente";
        const operators = item.operators || [];
        const domain = item.web_domain || "Consulta Directa";

        // Operator Chips
        let opChipsHtml = "";
        if (operators.length > 0) {
          opChipsHtml = `
            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center;">
              ${operators.map(op => {
                const sec = (op.sector || "").toLowerCase();
                const badgeCls = sec.includes("polic") ? "badge-police" :
                                 sec.includes("judic") ? "badge-judicial" :
                                 sec.includes("fiscal") ? "badge-fiscal" : "badge-clean";
                const locationLabel = op.jurisdiction || op.agency || "";
                return `
                  <button type="button" class="op-chip" onclick="openOperatorModal('${op.id}')" title="Ver expediente de ${escapeHtml(op.full_name)}">
                    <span class="badge ${badgeCls} badge-mini">${escapeHtml(op.sector || 'Operador')}</span>
                    <strong>${escapeHtml(op.full_name)}</strong>
                    ${locationLabel ? `<span style="opacity: 0.8; font-size: 0.72rem;">(${escapeHtml(locationLabel)})</span>` : ""}
                    <span>🔍</span>
                  </button>
                `;
              }).join("")}
            </div>
          `;
        } else {
          opChipsHtml = `<span class="text-dim" style="font-size: 0.8rem;">Sin funcionarios individualizados</span>`;
        }

        // Title and Source
        const isUrl = (item.url || "").startsWith("http://") || (item.url || "").startsWith("https://");
        const titleHtml = `
          <div>
            <strong style="color: #fff; font-size: 0.95rem;">${escapeHtml(item.title || item.url || 'Investigación Noticiosa')}</strong>
            ${isUrl ? `
              <div style="font-size: 0.78rem; margin-top: 0.2rem;">
                <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-cyan); text-decoration: none;">
                  🔗 ${escapeHtml(item.url.length > 55 ? item.url.substring(0, 52) + '...' : item.url)}
                </a>
              </div>
            ` : `
              <div style="font-size: 0.78rem; color: var(--text-dim); margin-top: 0.2rem;">
                Hecho verificado: ${escapeHtml(item.url ? item.url.substring(0, 55) + '...' : '')}
              </div>
            `}
          </div>
        `;

        return `
          <tr>
            <td>${titleHtml}</td>
            <td>
              <span class="web-domain-badge">
                🌐 ${escapeHtml(domain)}
              </span>
            </td>
            <td style="color: var(--text-muted); font-size: 0.83rem; white-space: nowrap;">
              📅 ${escapeHtml(dateFormatted)}
            </td>
            <td>${opChipsHtml}</td>
            <td style="text-align: right; white-space: nowrap;">
              <button type="button" class="btn-primary btn-sm" onclick="viewHistoricalReport('${item.id}')" title="Abrir informe completo">
                📖 Ver Informe
              </button>
              <button type="button" class="btn-secondary btn-sm" onclick="copyInvestigationId('${item.id}', this)" title="Copiar ID de auditoría">
                📋
              </button>
            </td>
          </tr>
        `;
      }).join("");

    } catch (err) {
      if (historyTableBody) {
        historyTableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; color: var(--accent-rose); padding: 2rem;">
              Error cargando historial: ${escapeHtml(err.message)}
            </td>
          </tr>
        `;
      }
    }
  }

  // Date Preset Pills
  datePresetPills.forEach(pill => {
    pill.addEventListener("click", () => {
      datePresetPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      activeDatePreset = pill.getAttribute("data-preset") || "all";

      // Clear custom date inputs if not custom
      if (activeDatePreset === "all") {
        if (historyDateStart) historyDateStart.value = "";
        if (historyDateEnd) historyDateEnd.value = "";
      } else {
        const { startDate, endDate } = getHistoryDateRange();
        if (historyDateStart) historyDateStart.value = startDate;
        if (historyDateEnd) historyDateEnd.value = endDate;
      }

      loadHistory();
    });
  });

  // Custom date picker changes
  function onCustomDateChange() {
    activeDatePreset = "custom";
    datePresetPills.forEach(p => p.classList.remove("active"));
    loadHistory();
  }

  if (historyDateStart) historyDateStart.addEventListener("change", onCustomDateChange);
  if (historyDateEnd) historyDateEnd.addEventListener("change", onCustomDateChange);

  // Search input with debounce
  if (historySearchInput) {
    historySearchInput.addEventListener("input", () => {
      clearTimeout(historySearchDebounce);
      historySearchDebounce = setTimeout(() => {
        loadHistory();
      }, 280);
    });
  }

  // Clear history filters
  if (clearHistoryFiltersBtn) {
    clearHistoryFiltersBtn.addEventListener("click", () => {
      if (historySearchInput) historySearchInput.value = "";
      if (historyDateStart) historyDateStart.value = "";
      if (historyDateEnd) historyDateEnd.value = "";
      activeDatePreset = "all";
      datePresetPills.forEach(p => {
        p.classList.toggle("active", p.getAttribute("data-preset") === "all");
      });
      loadHistory();
    });
  }

  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", loadHistory);
  }

  window.copyInvestigationId = function(id, btn) {
    navigator.clipboard.writeText(id).then(() => {
      const orig = btn.textContent;
      btn.textContent = "✓";
      setTimeout(() => { btn.textContent = orig; }, 1800);
    });
  };

  window.viewHistoricalReport = async function(invId) {
    try {
      const res = await fetch(`/api/investigations/${invId}`);
      if (!res.ok) throw new Error("No se pudo cargar el informe");
      const inv = await res.json();

      currentReportRaw = inv.final_report || "";
      if (reportContainer) {
        reportContainer.innerHTML = renderMarkdown(currentReportRaw);
      }

      if (reportToolbar && reportMetaInfo) {
        const dateStr = inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "";
        reportMetaInfo.innerHTML = `<span>Informe guardado: <strong>${escapeHtml(inv.title || inv.url)}</strong> (${dateStr})</span>`;
        reportToolbar.style.display = "flex";
      }

      switchView("view-report");

    } catch (e) {
      alert(`Error al visualizar el informe: ${e.message}`);
    }
  };

  // =========================================================================
  // DIRECTORIO DE ENTIDADES Y OPERADORES
  // =========================================================================
  async function loadDirectoryFilters() {
    try {
      const res = await fetch("/api/directory/filters");
      if (!res.ok) return;
      const data = await res.json();

      // Populate Jurisdictions (Entidades Federativas)
      if (filterJurisdiction && Array.isArray(data.jurisdictions)) {
        const curVal = filterJurisdiction.value;
        filterJurisdiction.innerHTML = `<option value="todos">Todas las entidades</option>` +
          data.jurisdictions.map(j => `<option value="${escapeHtml(j)}">${escapeHtml(j)}</option>`).join("");
        if (curVal) filterJurisdiction.value = curVal;
      }

      // Populate Agencies (Instituciones)
      if (filterAgency && Array.isArray(data.agencies)) {
        const curVal = filterAgency.value;
        filterAgency.innerHTML = `<option value="todos">Todas las instituciones</option>` +
          data.agencies.map(a => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`).join("");
        if (curVal) filterAgency.value = curVal;
      }

    } catch (e) {
      console.warn("Error cargando opciones de filtro del directorio:", e);
    }
  }

  async function loadDirectory() {
    try {
      if (dirCountBadge) dirCountBadge.textContent = "Filtrando directorio...";

      const params = new URLSearchParams();
      if (filterJurisdiction && filterJurisdiction.value !== "todos") {
        params.set("jurisdiction", filterJurisdiction.value);
      }
      if (filterAgency && filterAgency.value !== "todos") {
        params.set("agency", filterAgency.value);
      }
      if (filterStatus && filterStatus.value !== "todos") {
        params.set("status", filterStatus.value);
      }
      if (activeSectorFilter && activeSectorFilter !== "todos") {
        params.set("sector", activeSectorFilter);
      }
      if (dirSearchInput && dirSearchInput.value.trim()) {
        params.set("q", dirSearchInput.value.trim());
      }

      const res = await fetch(`/api/directory?${params.toString()}`);
      if (!res.ok) throw new Error("Error consultando directorio");
      const operators = await res.json();

      // Update counters
      const count = Array.isArray(operators) ? operators.length : 0;
      if (dirCountBadge) {
        dirCountBadge.textContent = `${count} entidad${count === 1 ? '' : 'es'} / operador${count === 1 ? '' : 'es'}`;
      }
      if (navDirBadge) {
        navDirBadge.textContent = count;
      }

      renderDirectoryCards(operators);
      renderDirectoryTable(operators);

    } catch (e) {
      if (dirCardsContainer) {
        dirCardsContainer.innerHTML = `<p class="text-dim" style="grid-column: 1/-1;">Error cargando directorio: ${escapeHtml(e.message)}</p>`;
      }
      if (dirTableBody) {
        dirTableBody.innerHTML = `<tr><td colspan="8" class="text-dim" style="text-align: center;">Error cargando datos.</td></tr>`;
      }
    }
  }

  function renderDirectoryCards(operators) {
    if (!dirCardsContainer) return;

    if (!Array.isArray(operators) || operators.length === 0) {
      dirCardsContainer.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem;" class="text-dim">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏛️</div>
          <strong style="color: #fff;">No se encontraron operadores ni entidades con estos criterios.</strong>
          <p style="font-size: 0.85rem; margin-top: 0.35rem;">Prueba restableciendo los filtros de entidad federativa o institución.</p>
        </div>
      `;
      return;
    }

    dirCardsContainer.innerHTML = operators.map(op => {
      const sectorLow = (op.sector || "").toLowerCase();
      const badgeClass = sectorLow.includes("polic") ? "badge-police" :
                         sectorLow.includes("judic") ? "badge-judicial" :
                         sectorLow.includes("fiscal") ? "badge-fiscal" : "badge-clean";

      const incidentCount = op.incidents_count || 0;
      const incidentBadge = incidentCount > 0
        ? `<span class="badge badge-incident-count">⚠️ ${incidentCount} Abuso(s)</span>`
        : `<span class="badge badge-clean">✓ Sin antecedentes</span>`;

      return `
        <div class="operator-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.35rem;">
            <div class="operator-name">${escapeHtml(op.full_name)}</div>
            ${incidentBadge}
          </div>

          <div class="operator-meta">
            <span class="badge ${badgeClass}">${escapeHtml(op.sector)}</span>
            <span class="badge badge-clean">🗺️ ${escapeHtml(op.jurisdiction || 'N/A')}</span> • 
            ${escapeHtml(op.agency)}
          </div>

          <div style="font-size: 0.88rem; margin-bottom: 0.3rem;">
            <strong>Cargo:</strong> ${escapeHtml(op.rank_or_role || 'No especificado')}
          </div>

          <div class="transparency-details">
            <div class="transparency-row">
              <span class="transparency-label">📅 Periodo / Fechas:</span>
              <span style="color: var(--accent-cyan);">${escapeHtml(op.tenure_period || 'En funciones / Periodo activo')}</span>
            </div>
            ${op.profile_details ? `
            <div class="transparency-row">
              <span class="transparency-label">🎓 Formación:</span>
              <span>${escapeHtml(op.profile_details)}</span>
            </div>` : ''}
            ${(op.office_location || op.contact_info) ? `
            <div class="transparency-row">
              <span class="transparency-label">🏢 Sede / Contacto:</span>
              <span>${escapeHtml(op.office_location || op.contact_info || '')}</span>
            </div>` : ''}
          </div>

          ${op.superiors_chain ? `
            <div class="chain-box">
              <strong>Cadena de Mando:</strong> ${escapeHtml(op.superiors_chain)}
            </div>` : ''}

          <div class="card-actions">
            <span style="font-size: 0.75rem; color: var(--text-dim);">ID: ${escapeHtml((op.id || '').substring(0, 8))}...</span>
            <button type="button" class="btn-secondary btn-sm" onclick="openOperatorModal('${op.id}')">
              🔍 Ver Expediente
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderDirectoryTable(operators) {
    if (!dirTableBody) return;

    if (!Array.isArray(operators) || operators.length === 0) {
      dirTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem;" class="text-dim">No se encontraron registros.</td></tr>`;
      return;
    }

    dirTableBody.innerHTML = operators.map(op => {
      const sectorLow = (op.sector || "").toLowerCase();
      const badgeClass = sectorLow.includes("polic") ? "badge-police" :
                         sectorLow.includes("judic") ? "badge-judicial" :
                         sectorLow.includes("fiscal") ? "badge-fiscal" : "badge-clean";
      const incidentCount = op.incidents_count || 0;
      const incidentBadge = incidentCount > 0
        ? `<span class="badge badge-incident-count">${incidentCount}</span>`
        : `<span class="badge badge-clean">0</span>`;

      return `
        <tr>
          <td><strong>${escapeHtml(op.full_name)}</strong></td>
          <td><span class="badge badge-clean">🗺️ ${escapeHtml(op.jurisdiction || 'N/A')}</span></td>
          <td><span class="badge ${badgeClass}">${escapeHtml(op.sector)}</span></td>
          <td>${escapeHtml(op.agency)}</td>
          <td>${escapeHtml(op.rank_or_role || '-')}</td>
          <td style="font-size: 0.8rem; color: var(--accent-cyan);">${escapeHtml(op.tenure_period || 'En funciones')}</td>
          <td>${incidentBadge}</td>
          <td>
            <button type="button" class="btn-secondary btn-sm" onclick="openOperatorModal('${op.id}')">
              🔍 Ver
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }

  // Directory filter event listeners
  if (filterJurisdiction) filterJurisdiction.addEventListener("change", loadDirectory);
  if (filterAgency) filterAgency.addEventListener("change", loadDirectory);
  if (filterStatus) filterStatus.addEventListener("change", loadDirectory);

  if (dirSearchInput) {
    dirSearchInput.addEventListener("input", () => {
      clearTimeout(dirSearchDebounce);
      dirSearchDebounce = setTimeout(() => {
        loadDirectory();
      }, 280);
    });
  }

  // Sector pills
  sectorPills.forEach(pill => {
    pill.addEventListener("click", () => {
      sectorPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      activeSectorFilter = pill.getAttribute("data-sector") || "todos";
      loadDirectory();
    });
  });

  // Clear directory filters
  if (clearDirFiltersBtn) {
    clearDirFiltersBtn.addEventListener("click", () => {
      if (filterJurisdiction) filterJurisdiction.value = "todos";
      if (filterAgency) filterAgency.value = "todos";
      if (filterStatus) filterStatus.value = "todos";
      if (dirSearchInput) dirSearchInput.value = "";
      activeSectorFilter = "todos";
      sectorPills.forEach(p => {
        p.classList.toggle("active", p.getAttribute("data-sector") === "todos");
      });
      loadDirectory();
    });
  }

  // View toggle: Cards vs Table
  if (viewCardsBtn && viewTableBtn) {
    viewCardsBtn.addEventListener("click", () => {
      viewCardsBtn.classList.add("active");
      viewTableBtn.classList.remove("active");
      if (dirCardsContainer) dirCardsContainer.style.display = "grid";
      if (dirTableContainer) dirTableContainer.style.display = "none";
    });

    viewTableBtn.addEventListener("click", () => {
      viewTableBtn.classList.add("active");
      viewCardsBtn.classList.remove("active");
      if (dirCardsContainer) dirCardsContainer.style.display = "none";
      if (dirTableContainer) dirTableContainer.style.display = "block";
    });
  }

  // =========================================================================
  // DOSSIER FORENSE MODAL
  // =========================================================================
  window.openOperatorModal = async function(operatorId) {
    if (!dossierModal) return;
    dossierModal.style.display = "flex";
    if (modalBodyContent) {
      modalBodyContent.innerHTML = `<div style="text-align: center; padding: 2.5rem;" class="text-dim">Cargando expediente forense completo...</div>`;
    }

    try {
      const res = await fetch(`/api/directory/${operatorId}`);
      if (!res.ok) throw new Error("No se pudo obtener el expediente");
      const data = await res.json();
      const op = data.operator || {};
      const incidents = data.incidents || [];
      activeDossierMarkdown = data.dossier_markdown || "";

      // Header info
      const sectorLow = (op.sector || "").toLowerCase();
      const badgeClass = sectorLow.includes("polic") ? "badge-police" :
                         sectorLow.includes("judic") ? "badge-judicial" :
                         sectorLow.includes("fiscal") ? "badge-fiscal" : "badge-clean";

      if (modalOperatorBadge) {
        modalOperatorBadge.className = `badge ${badgeClass}`;
        modalOperatorBadge.textContent = op.sector || "General";
      }
      if (modalOperatorName) {
        modalOperatorName.textContent = op.full_name || "Operador Desconocido";
      }
      if (modalOperatorMeta) {
        modalOperatorMeta.textContent = `${op.agency || ''} • ${op.jurisdiction ? '🗺️ ' + op.jurisdiction + ' • ' : ''}${op.rank_or_role || 'Sin cargo asignado'}`;
      }

      // Render Modal Body
      let html = `
        <div class="dossier-section">
          <div class="dossier-section-title">🏛️ Perfil Institucional y Funcional</div>
          <div class="dossier-grid">
            <div class="dossier-item">
              <div class="dossier-item-label">Entidad Federativa / Jurisdicción</div>
              <div class="dossier-item-val" style="color: var(--accent-cyan); font-weight: 600;">${escapeHtml(op.jurisdiction || 'N/A')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Corporación / Dependencia</div>
              <div class="dossier-item-val">${escapeHtml(op.agency || 'N/A')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Cargo Actual / Rango</div>
              <div class="dossier-item-val">${escapeHtml(op.rank_or_role || 'No especificado')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Identificador / Placa</div>
              <div class="dossier-item-val">${escapeHtml(op.badge_or_id || 'No disponible')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Filiación Política</div>
              <div class="dossier-item-val">${escapeHtml(op.political_affiliations || 'Sin filiación partidista formal')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Periodo en el Cargo / Fechas</div>
              <div class="dossier-item-val" style="color: var(--accent-cyan); font-weight: 600;">${escapeHtml(op.tenure_period || 'En funciones / Periodo activo')}</div>
            </div>
            <div class="dossier-item">
              <div class="dossier-item-label">Sede u Oficina Oficial</div>
              <div class="dossier-item-val">${escapeHtml(op.office_location || 'Sede Central Institucional')}</div>
            </div>
            <div class="dossier-item" style="grid-column: 1 / -1;">
              <div class="dossier-item-label">Perfil Profesional, Formación y Cédula</div>
              <div class="dossier-item-val">${escapeHtml(op.profile_details || 'Información curricular pública en auditoría')}</div>
            </div>
            <div class="dossier-item" style="grid-column: 1 / -1;">
              <div class="dossier-item-label">Contacto Oficial Institucional</div>
              <div class="dossier-item-val">${escapeHtml(op.contact_info || 'Canal de atención ciudadana y solicitudes de transparencia')}</div>
            </div>
            <div class="dossier-item" style="grid-column: 1 / -1;">
              <div class="dossier-item-label">Cadena de Mando Jerárquica (Superiores)</div>
              <div class="dossier-item-val" style="color: var(--accent-amber);">${escapeHtml(op.superiors_chain || 'Bajo investigación')}</div>
            </div>
            ${op.subordinates_scope ? `
            <div class="dossier-item" style="grid-column: 1 / -1;">
              <div class="dossier-item-label">Fuerza Operativa / Subordinados</div>
              <div class="dossier-item-val">${escapeHtml(op.subordinates_scope)}</div>
            </div>` : ''}
          </div>
        </div>

        <div class="dossier-section">
          <div class="dossier-section-title" style="color: ${incidents.length > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)'};">
            ${incidents.length > 0 ? '🚨' : '🛡️'} Historial de Abusos de Poder y Violaciones Documentadas (${incidents.length})
          </div>
      `;

      if (incidents.length === 0) {
        html += `
          <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 1rem; border-radius: var(--radius-sm); font-size: 0.88rem; color: #a7f3d0;">
            ✓ No se registran quejas formales de abuso de autoridad ni violaciones a derechos humanos validadas en el libro mayor para este actor.
          </div>
        `;
      } else {
        html += incidents.map((inc, i) => `
          <div class="incident-card">
            <div class="incident-title">${i + 1}. ${escapeHtml(inc.incident_type)} (${escapeHtml(inc.incident_date || 'Fecha no especificada')})</div>
            <div class="incident-desc">${escapeHtml(inc.description)}</div>
            <div class="incident-meta">
              <strong>Ubicación:</strong> ${escapeHtml(inc.location || 'No especificada')} • 
              <strong>Estatus:</strong> <span style="color: var(--accent-amber);">${escapeHtml(inc.investigation_status || 'Sin sanción')}</span>
              ${inc.victims_summary ? `<br/><strong>Afectados / Víctimas:</strong> ${escapeHtml(inc.victims_summary)}` : ''}
              ${inc.sources && inc.sources.length ? `<br/><strong>Fuentes:</strong> ${escapeHtml(inc.sources.join(', '))}` : ''}
            </div>
          </div>
        `).join("");
      }

      html += `</div>`;
      if (modalBodyContent) modalBodyContent.innerHTML = html;

    } catch (err) {
      if (modalBodyContent) modalBodyContent.innerHTML = `<p class="text-dim">Error cargando expediente: ${escapeHtml(err.message)}</p>`;
    }
  };

  function closeModal() {
    if (dossierModal) dossierModal.style.display = "none";
  }

  if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeModal);
  if (modalCloseBottomBtn) modalCloseBottomBtn.addEventListener("click", closeModal);
  if (dossierModal) {
    dossierModal.addEventListener("click", (e) => {
      if (e.target === dossierModal) closeModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && dossierModal && dossierModal.style.display !== "none") {
      closeModal();
    }
  });

  if (modalCopyMdBtn) {
    modalCopyMdBtn.addEventListener("click", () => {
      if (!activeDossierMarkdown) return;
      navigator.clipboard.writeText(activeDossierMarkdown).then(() => {
        const orig = modalCopyMdBtn.textContent;
        modalCopyMdBtn.textContent = "✓ ¡Dossier Copiado!";
        setTimeout(() => { modalCopyMdBtn.textContent = orig; }, 2000);
      });
    });
  }

  // =========================================================================
  // LIBRO MAYOR INMUTABLE
  // =========================================================================
  async function loadLedger() {
    if (!ledgerContainer) return;
    try {
      const res = await fetch("/api/ledger");
      const data = await res.json();

      if (ledgerStatusBadge) {
        ledgerStatusBadge.textContent = data.valid ? "✓ Criptográficamente Válido" : "⚠️ Discrepancia";
        ledgerStatusBadge.className = data.valid ? "badge badge-police" : "badge badge-abuse";
      }

      if (!data.entries || data.entries.length === 0) {
        ledgerContainer.innerHTML = "<p class='text-dim'>El libro mayor está vacío.</p>";
        return;
      }

      ledgerContainer.innerHTML = data.entries.slice().reverse().map(entry => `
        <div class="ledger-item">
          <div class="ledger-item-header">
            <span>Bloque #${entry.index} [${escapeHtml(entry.action)}]</span>
            <span>${escapeHtml(entry.timestamp_utc)}</span>
          </div>
          <div><strong>Payload:</strong> ${escapeHtml(JSON.stringify(entry.payload))}</div>
          <div class="hash-text"><strong>Hash:</strong> ${entry.hash}</div>
          <div class="hash-text"><strong>Prev Hash:</strong> ${entry.prev_hash}</div>
        </div>
      `).join("");
    } catch (e) {
      ledgerContainer.innerHTML = `<p class="text-dim">Error cargando libro mayor: ${escapeHtml(e.message)}</p>`;
    }
  }

  // =========================================================================
  // HELPERS
  // =========================================================================
  function renderMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

    // Code blocks & inline code
    html = html.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');

    // Blockquotes
    html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Paragraph breaks
    html = html.replace(/\n\n/gim, '<br/><br/>');

    return html;
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initialize latest report for the Report Tab if available
  async function initInitialReport() {
    try {
      const res = await fetch("/api/investigations");
      if (!res.ok) return;
      const list = await res.json();
      if (Array.isArray(list) && list.length > 0) {
        const latest = list[0];
        const detailRes = await fetch(`/api/investigations/${latest.id}`);
        if (detailRes.ok) {
          const inv = await detailRes.json();
          currentReportRaw = inv.final_report || "";
          if (reportContainer) {
            reportContainer.innerHTML = renderMarkdown(currentReportRaw);
          }
          if (reportToolbar && reportMetaInfo) {
            const dateStr = inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "";
            reportMetaInfo.innerHTML = `<span>Último informe generado: <strong>${escapeHtml(inv.title || inv.url)}</strong> (${dateStr})</span>`;
            reportToolbar.style.display = "flex";
          }
        }
      } else {
        if (reportContainer) {
          reportContainer.innerHTML = `
            <div style="text-align: center; padding: 3rem 1.5rem; background: rgba(10, 14, 20, 0.4); border: 1px dashed var(--border-color); border-radius: var(--radius-md);">
              <div style="font-size: 2.2rem; margin-bottom: 0.75rem;">🛡️</div>
              <h2 style="font-size: 1.3rem; color: #fff; margin-bottom: 0.5rem;">Bienvenido a Salamandra</h2>
              <p style="color: var(--text-muted); max-width: 580px; margin: 0 auto; line-height: 1.6; font-size: 0.92rem;">
                Ingresa una URL noticiosa o describe un hecho arriba para ejecutar el pipeline multi-agente de deconstrucción de sesgo, contraste fáctico y rastreo de operadores institucionales.
              </p>
            </div>
          `;
        }
      }
    } catch (e) {
      console.warn("No se pudo cargar informe inicial:", e);
    }
  }

  // =========================================================================
  // BOOTSTRAP INITIALIZATION
  // =========================================================================
  handleHashChange();
  loadDirectoryFilters();
  initInitialReport();
  loadHistory();
  loadDirectory();
  loadLedger();
});
