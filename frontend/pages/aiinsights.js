async function renderAiInsightsPage(main) {
  const recs = MOCK.recommendations;

  main.innerHTML = `
    ${pageHeader('AI Recommendations', 'AI powered recommendations and potential savings',
      `<select class="select"><option>Impact: High to Low</option></select>`
    )}

    <div class="card">
      ${recs.map(r => `
        <div class="rec-row">
          <div class="rec-icon icon-${r.color}">${r.icon}</div>
          <div style="flex:1;">
            <p class="rec-title">${r.title}</p>
            <p class="rec-sub">${r.desc}</p>
          </div>
          <div class="rec-facility">${r.facility}</div>
          <span class="badge ${r.impact === 'High' ? 'badge-green' : r.impact === 'Medium' ? 'badge-amber' : 'badge-blue'}">${r.impact}</span>
          <div class="rec-savings">${r.savings}</div>
          <span class="link">View</span>
        </div>
      `).join('')}
      <div class="pagination">
        <span class="pagination-info">Showing 1 to ${recs.length} of 12 recommendations</span>
        <div class="page-btn">&lsaquo;</div>
        <div class="page-btn active">1</div>
        <div class="page-btn">2</div>
        <div class="page-btn">3</div>
        <div class="page-btn">&rsaquo;</div>
      </div>
    </div>
  `;
}
