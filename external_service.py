from flask import Flask, jsonify
import random
from datetime import datetime

app = Flask(__name__)

@app.route('/api/data')
def get_data():
    """Simple API endpoint that returns random data."""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'value': random.randint(1, 100),
        'status': 'ok',
        'message': 'Hello from the external service!'
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'uptime': '123456',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 