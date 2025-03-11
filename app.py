import json
import os
import requests
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from bs4 import BeautifulSoup

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

def process_html_content(html_content):
    """Process HTML content to ensure proper rendering in iframes.
    
    This function handles parsing and preprocessing of HTML content
    to ensure scripts and styles are properly isolated.
    """
    try:
        # Try using BeautifulSoup to parse and clean the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process script tags to ensure they execute properly in iframe
        for script in soup.find_all('script'):
            # Add defer attribute to external scripts to ensure they load properly
            if script.get('src'):
                script['defer'] = 'defer'
            
            # Remove any document.write calls which can break iframe rendering
            if script.string:
                script.string = script.string.replace('document.write', '// document.write')
        
        return str(soup)
    except Exception as e:
        # If parsing fails, return original content
        print(f"Error processing HTML content: {e}")
        return html_content

def fetch_data_from_service(service):
    """Fetch data from an external service."""
    try:
        response = requests.get(service['url'], timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            
            # Get the base URL of the service for proper link resolution
            service_base_url = '/'.join(service['url'].split('/')[:3])  # Extract http(s)://domain.com
            service_path = '/'.join(service['url'].split('/')[3:])  # Extract the path
            
            # Determine the data format based on content type
            if 'application/json' in content_type:
                data = response.json()
            elif 'text/html' in content_type:
                data = response.text
                # Process HTML content
                data = process_html_content(data)
            else:
                data = response.text
                
            return {
                'name': service['name'],
                'url': service['url'],
                'status': 'Connected',
                'data': data,
                'base_url': service_base_url
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
    """Render the home page with all configured services."""
    config = load_config()
    service_data = []
    
    # Fetch data from each service
    for service in config.get('services', []):
        service_data.append(fetch_data_from_service(service))
    
    return render_template('index.html', services=service_data)

@app.route('/refresh-service-data')
def refresh_service_data():
    """Refresh data for a specific service."""
    service_name = request.args.get('name')
    if not service_name:
        return jsonify({'error': 'No service name provided'}), 400
    
    config = load_config()
    
    # Find the service by name
    service = next((s for s in config.get('services', []) if s['name'] == service_name), None)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    # Fetch fresh data
    service_data = fetch_data_from_service(service)
    
    return jsonify(service_data)

@app.route('/iframe/<service_name>')
def iframe_content(service_name):
    """Serve content for a specific service iframe."""
    config = load_config()
    
    # Find the service by name
    service = next((s for s in config.get('services', []) if s['name'] == service_name), None)
    if not service:
        return "Service not found", 404
    
    # Fetch service data
    service_data = fetch_data_from_service(service)
    
    if not service_data.get('data'):
        return f"Error: {service_data.get('status', 'No data available')}", 500
    
    # For HTML content, return directly to be rendered in iframe
    content_type = 'text/plain'
    if isinstance(service_data['data'], str) and (
        service_data['data'].startswith('<!DOCTYPE html>') or 
        service_data['data'].startswith('<html>') or 
        ('<' in service_data['data'] and '>' in service_data['data'])
    ):
        content_type = 'text/html'
        return Response(service_data['data'], mimetype=content_type)
    
    # For other types, wrap in a simple HTML template
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{service_name} Content</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 8px;
                overflow: auto;
                height: 100%;
                box-sizing: border-box;
            }}
            pre {{
                white-space: pre-wrap;
                margin: 0;
            }}
            img, video {{
                max-width: 100%;
                height: auto;
            }}
        </style>
    </head>
    <body>
        <pre>{json.dumps(service_data['data'], indent=2) if isinstance(service_data['data'], (dict, list)) else service_data['data']}</pre>
    </body>
    </html>
    """
    
    return Response(html_template, mimetype='text/html')

@app.route('/card-action', methods=['POST'])
def card_action():
    """Process actions from cards/iframes."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    service_id = data.get('serviceId')
    action = data.get('action')
    action_data = data.get('data', {})
    
    if not service_id or not action:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Map service_id to service name (assuming service_id is the sanitized service name)
    config = load_config()
    service = None
    
    for s in config.get('services', []):
        if s['name'].lower().replace(' ', '_') == service_id:
            service = s
            break
    
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    # Handle different actions
    result = {'success': True, 'message': f'Action {action} processed'}
    
    if action == 'log':
        print(f"Log from {service['name']}: {action_data.get('message', 'No message')}")
    
    # Add more action handlers as needed
    
    return jsonify(result)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Handle settings page, adding and managing services."""
    if request.method == 'POST':
        # Handle form submission to add a new service
        service_name = request.form.get('service_name')
        service_url = request.form.get('service_url')
        
        if service_name and service_url:
            config = load_config()
            
            # Check if service with the same name already exists
            service_exists = any(s['name'] == service_name for s in config.get('services', []))
            
            if not service_exists:
                # Add the new service
                if 'services' not in config:
                    config['services'] = []
                
                config['services'].append({
                    'name': service_name,
                    'url': service_url
                })
                
                save_config(config)
        
        return redirect(url_for('settings'))
    
    # GET request - show settings page
    config = load_config()
    return render_template('settings.html', services=config.get('services', []))

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test a connection to a service URL."""
    url = request.form.get('url')
    
    if not url:
        return jsonify({'status': 'Error', 'message': 'No URL provided'}), 400
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                data_preview = 'Valid JSON data received'
            elif 'text/html' in content_type:
                data_preview = 'HTML content received'
            else:
                data_preview = 'Data received'
                
            return jsonify({
                'status': 'Connected',
                'message': f'Connection successful: {response.status_code}',
                'preview': data_preview
            })
        else:
            return jsonify({
                'status': 'Error',
                'message': f'HTTP Error: {response.status_code}'
            })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'Error',
            'message': f'Connection failed: {str(e)}'
        })

@app.route('/remove-service', methods=['POST'])
def remove_service():
    """Remove a service from the configuration."""
    service_name = request.form.get('service_name')
    
    if not service_name:
        return jsonify({'status': 'Error', 'message': 'No service name provided'}), 400
    
    config = load_config()
    
    # Remove the service with the given name
    config['services'] = [s for s in config.get('services', []) if s['name'] != service_name]
    
    save_config(config)
    
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 