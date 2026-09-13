/**
 * APVA Interactive TVY & ROI Calculator Widget v3.0
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
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

      .apva-widget {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: rgba(12, 16, 25, 0.85);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        color: #f8fafc;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 28px;
        max-width: 680px;
        margin: 0 auto;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 35px -5px rgba(0, 217, 255, 0.12);
        position: relative;
        overflow: hidden;
      }
      .apva-widget::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00f5a0, #00d9ff, transparent);
      }
      .apva-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 18px;
        margin-bottom: 22px;
      }
      .apva-title {
        font-size: 1.25rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 40%, #93c5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 10px;
        letter-spacing: -0.02em;
      }
      .apva-badge {
        font-size: 0.72rem;
        background: rgba(0, 217, 255, 0.15);
        border: 1px solid rgba(0, 217, 255, 0.4);
        color: #38bdf8;
        padding: 3px 10px;
        border-radius: 9999px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      .apva-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 22px;
      }
      .apva-field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .apva-label {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .apva-input, .apva-select {
        background: rgba(8, 12, 20, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #f8fafc;
        padding: 10px 14px;
        border-radius: 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.95rem;
        outline: none;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      }
      .apva-input:focus, .apva-select:focus {
        border-color: #00d9ff;
        box-shadow: 0 0 14px rgba(0, 217, 255, 0.25);
      }
      .apva-result-card {
        background: linear-gradient(135deg, rgba(16, 24, 38, 0.9) 0%, rgba(8, 12, 20, 0.95) 100%);
        border: 1px solid rgba(0, 245, 160, 0.35);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 22px;
        position: relative;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.1);
      }
      .apva-grade-pill {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 9999px;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .apva-yield-title {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
        font-weight: 700;
      }
      .apva-yield-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        font-weight: 800;
        color: #00f5a0;
        text-shadow: 0 0 20px rgba(0, 245, 160, 0.35);
        letter-spacing: -0.02em;
      }
      .apva-yield-sub {
        font-size: 0.9rem;
        color: #cbd5e1;
        margin-top: 6px;
      }
      .apva-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 22px;
      }
      .apva-stat-box {
        background: rgba(8, 12, 20, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 14px 12px;
        border-radius: 12px;
        text-align: center;
      }
      .apva-stat-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
      }
      .apva-stat-lbl {
        font-size: 0.72rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
      }
      .apva-btn {
        display: block;
        width: 100%;
        background: linear-gradient(135deg, #00f5a0 0%, #00d9ff 100%);
        color: #06080d;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 0.98rem;
        letter-spacing: 0.02em;
        padding: 14px 0;
        border-radius: 12px;
        text-decoration: none;
        text-align: center;
        box-shadow: 0 8px 24px -4px rgba(0, 245, 160, 0.35);
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      }
      .apva-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px -4px rgba(0, 245, 160, 0.5);
        filter: brightness(1.08);
      }
      @media (max-width: 540px) {
        .apva-grid { grid-template-columns: 1fr; }
        .apva-stats { grid-template-columns: 1fr; }
      }
    </style>

    <div class="apva-widget">
      <div class="apva-header">
        <div class="apva-title">
          <span>APVA True Value Yield Calculator</span>
          <span class="apva-badge">v3.0 Enterprise</span>
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
          <label class="apva-label">Skill Level Tier</label>
          <select id="apva-skill-level" class="apva-select">
            <option value="2.0">Intern (2.0x Baseline)</option>
            <option value="1.5">Junior (1.5x Baseline)</option>
            <option value="1.0" selected>Mid-level (1.0x Baseline)</option>
            <option value="0.7">Senior (0.7x Baseline)</option>
            <option value="0.5">Staff / Expert (0.5x Baseline)</option>
          </select>
        </div>
        <div class="apva-field">
          <label class="apva-label">RAG Reliability SLA (%)</label>
          <input type="number" id="apva-rag-reliability" class="apva-input" value="92" min="10" max="100" />
        </div>
        <div class="apva-field">
          <label class="apva-label">Guardrail Friction Tax (min/task)</label>
          <input type="number" id="apva-guardrail-tax" class="apva-input" value="0.8" step="0.1" min="0" max="30" />
        </div>
      </div>

      <div class="apva-result-card">
        <div id="apva-grade-badge" class="apva-grade-pill" style="background:rgba(0,245,160,0.18);color:#00f5a0;border:1px solid rgba(0,245,160,0.4);">STRONG YIELD</div>
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
    const skillMultiplier = parseFloat(document.getElementById('apva-skill-level').value) || 1.0;
    const reliability = (parseFloat(document.getElementById('apva-rag-reliability').value) || 90) / 100.0;
    const guardrailTax = parseFloat(document.getElementById('apva-guardrail-tax').value) || 0.8;

    const aiGenTime = 3.0;
    const verifyTime = 5.0;

    const adjustedHuman = humanBase * skillMultiplier;
    const grossSaved = Math.max(0, adjustedHuman - (aiGenTime + verifyTime));
    const tvyMin = (grossSaved * reliability) - guardrailTax;
    const yieldPerTaskUsd = (tvyMin / 60.0) * hourlyRate;

    // Assuming 4 tasks/day * 250 work days = 1,000 tasks/year per person
    const tasksPerYearPerDev = 1000;
    const annualTotalUsd = yieldPerTaskUsd * tasksPerYearPerDev * teamSize;

    // Determine TVY Grade
    const badge = document.getElementById('apva-grade-badge');
    if (tvyMin >= 30.0) {
      badge.textContent = 'EXCEPTIONAL YIELD';
      badge.style.background = 'rgba(0, 245, 160, 0.2)';
      badge.style.color = '#00f5a0';
      badge.style.border = '1px solid rgba(0, 245, 160, 0.5)';
    } else if (tvyMin >= 15.0) {
      badge.textContent = 'STRONG YIELD';
      badge.style.background = 'rgba(0, 217, 255, 0.2)';
      badge.style.color = '#00d9ff';
      badge.style.border = '1px solid rgba(0, 217, 255, 0.5)';
    } else if (tvyMin >= 5.0) {
      badge.textContent = 'MODERATE YIELD';
      badge.style.background = 'rgba(245, 158, 11, 0.2)';
      badge.style.color = '#fbbf24';
      badge.style.border = '1px solid rgba(245, 158, 11, 0.5)';
    } else if (tvyMin >= 0.0) {
      badge.textContent = 'MARGINAL YIELD';
      badge.style.background = 'rgba(234, 179, 8, 0.2)';
      badge.style.color = '#fde047';
      badge.style.border = '1px solid rgba(234, 179, 8, 0.5)';
    } else {
      badge.textContent = 'NEGATIVE YIELD';
      badge.style.background = 'rgba(255, 51, 102, 0.2)';
      badge.style.color = '#ff4d79';
      badge.style.border = '1px solid rgba(255, 51, 102, 0.5)';
    }

    document.getElementById('apva-annual-yield').textContent = 
      (annualTotalUsd >= 0 ? '+$' : '-$') + Math.abs(Math.round(annualTotalUsd)).toLocaleString() + ' / yr';
    document.getElementById('apva-tvy-mins').textContent = 
      (tvyMin >= 0 ? '+' : '') + tvyMin.toFixed(2) + ' minutes net saved per developer task';
    document.getElementById('apva-stat-gross').textContent = grossSaved.toFixed(1) + ' min';
    document.getElementById('apva-stat-tax').textContent = guardrailTax.toFixed(1) + ' min';
    document.getElementById('apva-stat-unit').textContent = '$' + yieldPerTaskUsd.toFixed(2);
  }

  ['apva-team-size', 'apva-hourly-rate', 'apva-human-baseline', 'apva-skill-level', 'apva-rag-reliability', 'apva-guardrail-tax'].forEach(id => {
    document.getElementById(id).addEventListener('input', calculate);
    document.getElementById(id).addEventListener('change', calculate);
  });

  calculate();
})();
