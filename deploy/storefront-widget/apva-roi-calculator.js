/**
 * APVA Interactive TVY & ROI Calculator Widget
 * Hardonia Storefront Integration (https://aiautomatedsystems.ca)
 * 
 * Embed anywhere with:
 * <div id="apva-roi-calculator"></div>
 * <script src="apva-roi-calculator.js"></script>
 */

(function () {
  const container = document.getElementById('apva-roi-calculator');
  if (!container) return;

  container.innerHTML = `
    <style>
      .apva-widget {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 24px;
        max-width: 680px;
        margin: 0 auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
      }
      .apva-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 16px;
        margin-bottom: 20px;
      }
      .apva-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .apva-badge {
        font-size: 0.75rem;
        background: #0284c7;
        color: white;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
      }
      .apva-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
      }
      .apva-field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .apva-label {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
      }
      .apva-input {
        background: #1e293b;
        border: 1px solid #475569;
        color: white;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 1rem;
        outline: none;
        transition: border-color 0.2s;
      }
      .apva-input:focus {
        border-color: #38bdf8;
      }
      .apva-result-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
      }
      .apva-yield-title {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
      }
      .apva-yield-value {
        font-size: 2.25rem;
        font-weight: 800;
        color: #4ade80;
      }
      .apva-yield-sub {
        font-size: 0.95rem;
        color: #cbd5e1;
        margin-top: 4px;
      }
      .apva-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 20px;
      }
      .apva-stat-box {
        background: #1e293b;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
      }
      .apva-stat-num {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9;
      }
      .apva-stat-lbl {
        font-size: 0.75rem;
        color: #64748b;
      }
      .apva-btn {
        display: block;
        width: 100%;
        background: #38bdf8;
        color: #0f172a;
        font-weight: 700;
        font-size: 1rem;
        padding: 12px 0;
        border-radius: 8px;
        text-decoration: none;
        text-align: center;
        transition: transform 0.1s, background-color 0.2s;
      }
      .apva-btn:hover {
        background: #7dd3fc;
        transform: translateY(-1px);
      }
      @media (max-width: 500px) {
        .apva-grid { grid-template-columns: 1fr; }
        .apva-stats { grid-template-columns: 1fr; }
      }
    </style>

    <div class="apva-widget">
      <div class="apva-header">
        <div class="apva-title">
          <span>APVA True Value Yield Calculator</span>
          <span class="apva-badge">Hardonia Standard</span>
        </div>
      </div>

      <div class="apva-grid">
        <div class="apva-field">
          <label class="apva-label">Team Size (Engineers / Agents)</label>
          <input type="number" id="apva-team-size" class="apva-input" value="25" min="1" max="10000" />
        </div>
        <div class="apva-field">
          <label class="apva-label">Fully Loaded Hourly Rate ($/hr)</label>
          <input type="number" id="apva-hourly-rate" class="apva-input" value="85" min="10" max="1000" />
        </div>
        <div class="apva-field">
          <label class="apva-label">Human Baseline Time (min/task)</label>
          <input type="number" id="apva-human-baseline" class="apva-input" value="30" min="1" max="480" />
        </div>
        <div class="apva-field">
          <label class="apva-label">RAG Reliability SLA (%)</label>
          <input type="number" id="apva-rag-reliability" class="apva-input" value="92" min="10" max="100" />
        </div>
      </div>

      <div class="apva-result-card">
        <div class="apva-yield-title">Estimated Annual Net Value Yield</div>
        <div class="apva-yield-value" id="apva-annual-yield">$378,675 / yr</div>
        <div class="apva-yield-sub" id="apva-tvy-mins">+17.78 minutes net saved per developer task</div>
      </div>

      <div class="apva-stats">
        <div class="apva-stat-box">
          <div class="apva-stat-num" id="apva-stat-gross">22.0 min</div>
          <div class="apva-stat-lbl">Gross Time Saved</div>
        </div>
        <div class="apva-stat-box">
          <div class="apva-stat-num" id="apva-stat-tax">0.8 min</div>
          <div class="apva-stat-lbl">Guardrail Friction Tax</div>
        </div>
        <div class="apva-stat-box">
          <div class="apva-stat-num" id="apva-stat-unit">$25.19</div>
          <div class="apva-stat-lbl">Yield Value / Task</div>
        </div>
      </div>

      <a href="https://aiautomatedsystems.ca/p/repo-rescue-saas-audit" target="_blank" class="apva-btn">
        Start Measuring Your True TVY with APVA &rarr;
      </a>
    </div>
  `;

  function calculate() {
    const teamSize = parseFloat(document.getElementById('apva-team-size').value) || 1;
    const hourlyRate = parseFloat(document.getElementById('apva-hourly-rate').value) || 50;
    const humanBase = parseFloat(document.getElementById('apva-human-baseline').value) || 30;
    const reliability = (parseFloat(document.getElementById('apva-rag-reliability').value) || 90) / 100.0;

    const aiGenTime = 3.0;
    const verifyTime = 5.0;
    const guardrailTax = 0.8;

    const grossSaved = Math.max(0, humanBase - (aiGenTime + verifyTime));
    const tvyMin = (grossSaved * reliability) - guardrailTax;
    const yieldPerTaskUsd = (tvyMin / 60.0) * hourlyRate;

    // Assuming 4 tasks/day * 250 work days = 1,000 tasks/year per person
    const tasksPerYearPerDev = 1000;
    const annualTotalUsd = yieldPerTaskUsd * tasksPerYearPerDev * teamSize;

    document.getElementById('apva-annual-yield').textContent = 
      (annualTotalUsd >= 0 ? '+$' : '-$') + Math.abs(Math.round(annualTotalUsd)).toLocaleString() + ' / yr';
    document.getElementById('apva-tvy-mins').textContent = 
      (tvyMin >= 0 ? '+' : '') + tvyMin.toFixed(2) + ' minutes net saved per developer task';
    document.getElementById('apva-stat-gross').textContent = grossSaved.toFixed(1) + ' min';
    document.getElementById('apva-stat-tax').textContent = guardrailTax.toFixed(1) + ' min';
    document.getElementById('apva-stat-unit').textContent = '$' + yieldPerTaskUsd.toFixed(2);
  }

  ['apva-team-size', 'apva-hourly-rate', 'apva-human-baseline', 'apva-rag-reliability'].forEach(id => {
    document.getElementById(id).addEventListener('input', calculate);
  });

  calculate();
})();
