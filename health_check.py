"""
Health Check HTTP Server
Provides a simple HTTP endpoint for monitoring system health
"""

import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HEALTH_FILE = "logs/health_status.txt"
PORT = 8080

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.serve_health()
        elif self.path == '/':
            self.serve_index()
        else:
            self.send_error(404)

    def serve_health(self):
        """Serve health status as JSON"""
        try:
            # Read health status file
            if Path(HEALTH_FILE).exists():
                health_data = {}
                with open(HEALTH_FILE, 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            health_data[key.strip()] = value.strip()

                response = {
                    'status': health_data.get('Status', 'UNKNOWN'),
                    'uptime': health_data.get('Uptime', 'N/A'),
                    'emails_processed': health_data.get('Emails Processed', '0'),
                    'emails_failed': health_data.get('Emails Failed', '0'),
                    'success_rate': health_data.get('Success Rate', 'N/A'),
                    'consecutive_failures': health_data.get('Consecutive Failures', '0'),
                    'last_successful_process': health_data.get('Last Successful Process', 'Never'),
                    'last_error': health_data.get('Last Error', 'None'),
                    'timestamp': datetime.now().isoformat()
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())
            else:
                # Health file doesn't exist - system might not be running
                response = {
                    'status': 'UNKNOWN',
                    'message': 'Health status file not found. System may not be running.',
                    'timestamp': datetime.now().isoformat()
                }
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            response = {
                'status': 'ERROR',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())

    def serve_index(self):
        """Serve simple HTML dashboard"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>RAG Email System - Health Dashboard</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    border-bottom: 3px solid #4CAF50;
                    padding-bottom: 10px;
                }
                .status {
                    font-size: 24px;
                    font-weight: bold;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                .healthy {
                    background-color: #4CAF50;
                    color: white;
                }
                .unhealthy {
                    background-color: #f44336;
                    color: white;
                }
                .unknown {
                    background-color: #ff9800;
                    color: white;
                }
                .metric {
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #eee;
                }
                .metric-label {
                    font-weight: bold;
                    color: #666;
                }
                .metric-value {
                    color: #333;
                }
                .footer {
                    margin-top: 20px;
                    text-align: center;
                    color: #888;
                    font-size: 12px;
                }
            </style>
            <script>
                async function updateHealth() {
                    try {
                        const response = await fetch('/health');
                        const data = await response.json();

                        document.getElementById('status').textContent = data.status;
                        document.getElementById('status').className =
                            'status ' + data.status.toLowerCase();

                        document.getElementById('uptime').textContent = data.uptime;
                        document.getElementById('processed').textContent = data.emails_processed;
                        document.getElementById('failed').textContent = data.emails_failed;
                        document.getElementById('success_rate').textContent = data.success_rate;
                        document.getElementById('failures').textContent = data.consecutive_failures;
                        document.getElementById('last_process').textContent = data.last_successful_process;
                        document.getElementById('last_error').textContent = data.last_error;
                        document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString();
                    } catch (error) {
                        console.error('Failed to fetch health status:', error);
                    }
                }

                setInterval(updateHealth, 5000);
                window.onload = updateHealth;
            </script>
        </head>
        <body>
            <div class="container">
                <h1>RAG Email System - Health Dashboard</h1>

                <div id="status" class="status unknown">LOADING...</div>

                <div class="metrics">
                    <div class="metric">
                        <span class="metric-label">Uptime:</span>
                        <span class="metric-value" id="uptime">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Emails Processed:</span>
                        <span class="metric-value" id="processed">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Emails Failed:</span>
                        <span class="metric-value" id="failed">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Success Rate:</span>
                        <span class="metric-value" id="success_rate">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Consecutive Failures:</span>
                        <span class="metric-value" id="failures">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Last Successful Process:</span>
                        <span class="metric-value" id="last_process">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Last Error:</span>
                        <span class="metric-value" id="last_error">-</span>
                    </div>
                </div>

                <div class="footer">
                    Last updated: <span id="timestamp">-</span><br>
                    Auto-refreshes every 5 seconds
                </div>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

def run_server(port=PORT):
    """Run the health check HTTP server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Health check server running on http://localhost:{port}")
    print(f"Dashboard: http://localhost:{port}/")
    print(f"JSON endpoint: http://localhost:{port}/health")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
