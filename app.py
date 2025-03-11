import json
import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from the config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"services": []}

def save_config(config):
    """Save configuration to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def fetch_data_from_service(service):
    """Fetch data from an external service."""
    try:
        response = requests.get(service['url'], timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            # Determine the data format based on content type
            if 'application/json' in content_type:
                data = response.json()
            elif 'text/html' in content_type:
                data = response.text
            else:
                data = response.text
                
            return {
                'name': service['name'],
                'url': service['url'],
                'status': 'Connected',
                'data': data
            }
        else:
            return {
                'name': service['name'],
                'url': service['url'],
                'status': f'Error: HTTP {response.status_code}',
                'data': None
            }
    except requests.exceptions.RequestException as e:
        return {
            'name': service['name'],
            'url': service['url'],
            'status': f'Error: {str(e)}',
            'data': None
        }

@app.route('/')
def home():
    """Homepage that displays data from connected external services."""
    config = load_config()
    service_data = []
    
    for service in config['services']:
        service_data.append(fetch_data_from_service(service))
    
    return render_template('index.html', services=service_data)

@app.route('/refresh-service-data')
def refresh_service_data():
    """API endpoint to refresh service data without reloading the page."""
    service_name = request.args.get('name')
    config = load_config()
    
    # Find the service by name
    for service in config['services']:
        if service['name'] == service_name:
            service_data = fetch_data_from_service(service)
            return jsonify(service_data)
    
    return jsonify({"error": "Service not found"}), 404

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for managing external service connections."""
    config = load_config()
    
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        
        if name and url:
            # Simple validation
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
                
            # Check if service with this name already exists
            for service in config['services']:
                if service['name'] == name:
                    service['url'] = url
                    break
            else:
                config['services'].append({'name': name, 'url': url})
                
            save_config(config)
            
        return redirect(url_for('settings'))
    
    return render_template('settings.html', services=config['services'])

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test connection to an external service."""
    url = request.json.get('url')
    
    if not url:
        return jsonify({'status': 'Error', 'message': 'URL is required'}), 400
        
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
        
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return jsonify({
                'status': 'Success',
                'message': 'Connection successful'
            })
        else:
            return jsonify({
                'status': 'Error',
                'message': f'HTTP Error: {response.status_code}'
            })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'Error',
            'message': str(e)
        })

@app.route('/remove-service', methods=['POST'])
def remove_service():
    """Remove a service from the configuration."""
    name = request.form.get('name')
    
    if name:
        config = load_config()
        config['services'] = [s for s in config['services'] if s['name'] != name]
        save_config(config)
        
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 