"""Flask web application for Pixly dashboard."""

import json
from flask import Flask, jsonify, render_template_string, request

from pixly.core.config import ConfigError, load_config
from pixly.core.database import ScreenshotDatabase

app = Flask(__name__)

# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pixly Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { margin-bottom: 20px; color: #2c3e50; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { font-size: 14px; color: #666; margin-bottom: 8px; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #2c3e50; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .search-box { margin-bottom: 20px; }
        .search-box input { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 8px; }
        .results { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .result-item { padding: 15px 20px; border-bottom: 1px solid #eee; }
        .result-item:last-child { border-bottom: none; }
        .result-item h4 { margin-bottom: 5px; color: #2c3e50; }
        .result-item .meta { font-size: 12px; color: #666; }
        .result-item .preview { font-size: 13px; color: #888; margin-top: 5px; }
        .category-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .category-Errors { background: #fee; color: #c00; }
        .category-Code { background: #e8f5e9; color: #2e7d32; }
        .category-Memes { background: #fff3e0; color: #e65100; }
        .category-UI { background: #e3f2fd; color: #1565c0; }
        .category-Docs { background: #f3e5f5; color: #7b1fa2; }
        .category-Other { background: #eceff1; color: #546e7a; }
        h2 { margin-bottom: 15px; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Pixly Dashboard</h1>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card"><h3>Total Screenshots</h3><div class="value" id="total">-</div></div>
            <div class="stat-card"><h3>Total Size</h3><div class="value" id="size">-</div></div>
            <div class="stat-card"><h3>Duplicates</h3><div class="value" id="duplicates">-</div></div>
            <div class="stat-card"><h3>Space Saved</h3><div class="value" id="saved">-</div></div>
        </div>
        
        <div class="chart-container">
            <h2>Screenshots by Category</h2>
            <canvas id="categoryChart" height="100"></canvas>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search screenshots..." onkeyup="handleSearch(event)">
        </div>
        
        <h2>Recent Screenshots</h2>
        <div class="results" id="results"></div>
    </div>
    
    <script>
        let chart = null;
        
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            
            document.getElementById('total').textContent = data.total;
            document.getElementById('size').textContent = formatSize(data.total_size);
            document.getElementById('duplicates').textContent = data.duplicates;
            document.getElementById('saved').textContent = formatSize(data.duplicates * 500000); // Estimate
            
            // Update chart
            const categories = Object.keys(data.by_category || {});
            const counts = Object.values(data.by_category || {});
            
            if (chart) chart.destroy();
            chart = new Chart(document.getElementById('categoryChart'), {
                type: 'bar',
                data: {
                    labels: categories,
                    datasets: [{
                        label: 'Screenshots',
                        data: counts,
                        backgroundColor: ['#ef5350', '#66bb6a', '#ffa726', '#42a5f5', '#ab47bc', '#78909c']
                    }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } }
            });
        }
        
        async function loadRecent() {
            const res = await fetch('/api/recent');
            const data = await res.json();
            renderResults(data);
        }
        
        async function handleSearch(event) {
            const query = event.target.value.trim();
            if (query.length < 2) {
                loadRecent();
                return;
            }
            const res = await fetch('/api/search?q=' + encodeURIComponent(query));
            const data = await res.json();
            renderResults(data);
        }
        
        function renderResults(items) {
            const container = document.getElementById('results');
            if (!items.length) {
                container.innerHTML = '<div class="result-item">No screenshots found</div>';
                return;
            }
            container.innerHTML = items.map(item => `
                <div class="result-item">
                    <h4>${item.new_name} <span class="category-badge category-${item.category}">${item.category}</span></h4>
                    <div class="meta">${item.filepath} • ${new Date(item.processed_at).toLocaleString()}</div>
                    ${item.ocr_text ? `<div class="preview">${item.ocr_text.substring(0, 150)}...</div>` : ''}
                </div>
            `).join('');
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
            return (bytes/(1024*1024)).toFixed(1) + ' MB';
        }
        
        loadStats();
        loadRecent();
    </script>
</body>
</html>
"""


def get_db():
    """Get database instance."""
    config = load_config()
    return ScreenshotDatabase(config.db_path)


@app.route('/')
def dashboard():
    """Dashboard HTML page."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/stats')
def api_stats():
    """Statistics JSON endpoint."""
    db = get_db()
    try:
        stats = db.get_stats()
        return jsonify(stats)
    finally:
        db.close()


@app.route('/api/search')
def api_search():
    """Search results JSON endpoint."""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    db = get_db()
    try:
        results = db.search(query, limit=50)
        return jsonify([{
            'id': r.id,
            'filepath': r.filepath,
            'original_name': r.original_name,
            'new_name': r.new_name,
            'category': r.category,
            'description': r.description,
            'ocr_text': r.ocr_text,
            'processed_at': r.processed_at,
            'is_duplicate': r.is_duplicate
        } for r in results])
    finally:
        db.close()


@app.route('/api/recent')
def api_recent():
    """Recent screenshots JSON endpoint."""
    db = get_db()
    try:
        results = db.get_recent(limit=20)
        return jsonify([{
            'id': r.id,
            'filepath': r.filepath,
            'original_name': r.original_name,
            'new_name': r.new_name,
            'category': r.category,
            'description': r.description,
            'ocr_text': r.ocr_text,
            'processed_at': r.processed_at,
            'is_duplicate': r.is_duplicate
        } for r in results])
    finally:
        db.close()


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the Flask development server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
